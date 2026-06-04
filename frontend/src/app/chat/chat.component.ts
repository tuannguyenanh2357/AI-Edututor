import { Component, OnInit, OnChanges, SimpleChanges, inject, ViewChild, ElementRef, AfterViewChecked, ChangeDetectorRef, PLATFORM_ID, Input } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, SafeHtml, SafeUrl } from '@angular/platform-browser';
import { ChatService, ChatThread } from '../core/services/chat.service';
import { SubjectService, Subject, TeacherDocument } from '../core/services/subject.service';
import { AuthService } from '../core/services/auth.service';
import { marked } from 'marked';
import katex from 'katex';

// Extend window to access mermaid from CDN
declare const mermaid: any;

export interface ChatMessage {
  id?: number;
  subject?: number | null;
  role: 'user' | 'assistant';
  content: string;
  imageUrl?: string; // Multi-modal image support
  safeHtml?: SafeHtml;
  statusText?: string; // Streaming status indicator
  citations?: any[]; // [NEW] Danh sách trích dẫn RAG
  created_at?: string;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit, OnChanges, AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;
  @ViewChild('messageInput') private messageInput!: ElementRef;

  private platformId = inject(PLATFORM_ID);

  messages: ChatMessage[] = [];
  newMessage: string = '';
  subject: Subject | null = null;
  selectedDocument: TeacherDocument | null = null;
  showPdf: boolean = false; // [FIX] Lazy load PDF
  currentSafePdfUrl: SafeUrl | null = null; // [FIX] Store sanitized URL to prevent reloading on typing

  threads: ChatThread[] = [];
  currentThreadId: string | null = null;
  pathId: number | null = null; // [NEW] Lưu trữ ID lộ trình hiện tại

  isLoading: boolean = false;
  showDeleteModal: boolean = false; // [NEW] Flag for premium deletion modal
  attachedImage: string | null = null; // Stores Base64 string for preview & send
  private shouldScroll = false;
  private renderTimer: any; // Debounce timer for Markdown render

  isInitialLoading: boolean = true; // Flag for first subject fetch
  errorLoading: boolean = false; // Flag for fetch errors
  debugMessage: string = ''; // Chứa lỗi runtime để in thẳng lên màn hình
  private hasStartedAutoMessage: boolean = false; // [NEW] Tránh gửi auto message nhiều lần

  @Input() isEmbedded: boolean = false;
  @Input() subjectId: number | null = null;
  @Input() lessonContext: string | null = null;

  isSidebarVisible: boolean = false;
  isBookPanelOpen: boolean = false;
  isToolsMenuOpen: boolean = false;

  toggleSidebar(): void {
    this.isSidebarVisible = !this.isSidebarVisible;
    this.cdr.detectChanges();
  }

  toggleBookPanel(): void {
    this.isBookPanelOpen = !this.isBookPanelOpen;
    if (this.isBookPanelOpen) {
      this.isSidebarVisible = false;
    }
    this.cdr.detectChanges();
  }

  toggleToolsMenu(): void {
    this.isToolsMenuOpen = !this.isToolsMenuOpen;
    this.cdr.detectChanges();
  }

  closeToolsMenu(): void {
    this.isToolsMenuOpen = false;
  }

  startNewChat(): void {
    this.messages = [];
    this.currentThreadId = null;
    this.hasStartedAutoMessage = false; // Đặt lại cờ để có thể tự động nhắn tin lại
    
    // Xóa threadId khỏi URL
    if (isPlatformBrowser(this.platformId)) {
      const url = new URL(window.location.href);
      url.searchParams.delete('threadId');
      window.history.replaceState({}, '', url.toString());
      
      // Xóa trong sessionStorage
      if (this.isEmbedded && this.subjectId && this.lessonContext) {
        sessionStorage.removeItem(`lesson_thread_${this.subjectId}_${this.lessonContext}`);
      }
    }
    
    this.cdr.detectChanges();
    
    // Tự động kích hoạt lại AI Tutor ngay lập tức nếu đang ở Lesson View
    if (this.isEmbedded && this.lessonContext && this.subject) {
      this.hasStartedAutoMessage = true;
      setTimeout(() => {
        this.newMessage = this.lessonContext || '';
        this.sendMessage();
      }, 300);
    }
  }

  selectThread(threadId: string): void {
    if (this.currentThreadId === threadId) return;
    this.currentThreadId = threadId;
    this.isLoading = false;
    this.messages = [];

    this.chatService.getChatHistory(threadId).subscribe({
      next: (history: ChatMessage[]) => {
        this.messages = history.map((m: any) => ({
          ...m,
          imageUrl: m.image_data,
          safeHtml: this.parseMarkdown(m.content, false)
        }));
        this.shouldScroll = true;
        this.cdr.detectChanges();
        setTimeout(() => this._renderMermaid(), 100);
      },
      error: (err) => console.error('Failed to load chat history', err)
    });
  }

  loadThreads(): void {
    this.chatService.getThreads().subscribe({
      next: (res) => {
        this.threads = res;
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Failed to load threads', err)
    });
  }


  // Getter trả về number cho routerLink '/quiz-practice' — tránh lỗi TS2345 trong template
  get selectedDocId(): number {
    return this.selectedDocument?.id ?? 0;
  }

  private chatService = inject(ChatService);
  private subjectService = inject(SubjectService);
  private authService = inject(AuthService);
  private route = inject(ActivatedRoute);
  private sanitizer = inject(DomSanitizer);
  private cdr = inject(ChangeDetectorRef);

  ngOnInit(): void {
    // [NEW] Lấy pathId từ query params (ví dụ: ?pathId=2)
    this.route.queryParamMap.subscribe(params => {
      const pId = params.get('pathId');
      if (pId) {
        this.pathId = Number(pId);
      }
      const tId = params.get('threadId');
      if (tId) {
        this.hasStartedAutoMessage = true;
        this.selectThread(tId);
      } else if (isPlatformBrowser(this.platformId) && this.subjectId && this.lessonContext) {
        // Fallback to sessionStorage if URL doesn't have it (e.g. navigation without preserving query params)
        const sessionThread = sessionStorage.getItem(`lesson_thread_${this.subjectId}_${this.lessonContext}`);
        if (sessionThread) {
          this.hasStartedAutoMessage = true;
          this.selectThread(sessionThread);

          // Restore URL
          const url = new URL(window.location.href);
          url.searchParams.set('threadId', sessionThread);
          window.history.replaceState({}, '', url.toString());
        }
      }
    });

    if (isPlatformBrowser(this.platformId)) {
      if (this.isEmbedded && this.subjectId) {
        this.loadSubject(Number(this.subjectId));
      } else {
        this.route.params.subscribe({
          next: (params) => {
            const id = params['id'];
            if (id) {
              this.loadSubject(Number(id));
            }
          },
          error: (e) => {
            this.isInitialLoading = false;
            this.errorLoading = true;
            this.debugMessage = 'Lỗi Route Observable: ' + e.toString();
            this.cdr.detectChanges();
          }
        });
      }
      this.loadThreads();
    } else {
      // Nếu là server, tắt loading ngay để không bị kẹt skeleton vô tận
      this.isInitialLoading = false;
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    // [FIX] Nếu subjectId được truyền vào sau khi component đã init (do async load ở cha)
    if (isPlatformBrowser(this.platformId) && this.isEmbedded) {
      if (changes['subjectId'] && changes['subjectId'].currentValue) {
        if (!this.subject || this.subject.id !== Number(this.subjectId)) {
          this.loadSubject(Number(this.subjectId));
        }
      }

      if (changes['lessonContext'] && changes['lessonContext'].currentValue && !this.hasStartedAutoMessage && this.subject) {
        // Chỉ gửi nếu không có threadId trong URL
        const hasThreadId = new URLSearchParams(window.location.search).has('threadId');
        const sessionThread = sessionStorage.getItem(`lesson_thread_${this.subjectId}_${changes['lessonContext'].currentValue}`);
        
        if (!hasThreadId && !sessionThread) {
          this.hasStartedAutoMessage = true;
          setTimeout(() => {
            this.newMessage = changes['lessonContext'].currentValue;
            this.sendMessage();
          }, 500);
        }
      }
    }
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private _renderMermaid(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    if (typeof mermaid !== 'undefined') {
      try {
        const blocks = document.querySelectorAll('.language-mermaid');
        const validNodes: Element[] = [];

        blocks.forEach(block => {
          const code = block.textContent?.trim() || '';

          // Chỉ render block là Mermaid hợp lệ, bỏ qua math/text/code bình thường
          const isMermaid = code.startsWith('graph') ||
            code.startsWith('flowchart') ||
            code.startsWith('sequenceDiagram') ||
            code.startsWith('classDiagram') ||
            code.startsWith('mindmap') ||
            code.startsWith('gantt');

          if (!isMermaid) return;

          const parentPre = block.parentElement;
          if (parentPre && parentPre.tagName === 'PRE') {
            const div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = code;
            parentPre.replaceWith(div);
            validNodes.push(div);
          }
        });

        if (validNodes.length > 0) {
          (mermaid.run({ nodes: validNodes }) as Promise<void>).catch((err: any) => {
            console.warn('Mermaid render failed:', err);
          });
        }

      } catch (err) {
        console.warn('Mermaid error:', err);
      }
    }
  }

  loadSubject(id: number): void {
    const backendUrl = 'http://localhost:8000'; // Hardcoded for local dev, can be moved to environment
    this.isInitialLoading = true;
    this.errorLoading = false;

    this.subjectService.getSubjectDetail(id).subscribe({
      next: (result: Subject) => {
        // [FIX SSR] Thực hiện cập nhật logic dữ liệu
        if (result.documents) {
          result.documents = result.documents.map(doc => {
            if (doc.pdf_file && !doc.pdf_file.startsWith('http')) {
              const path = doc.pdf_file.startsWith('/') ? doc.pdf_file : `/${doc.pdf_file}`;
              const mediaPath = path.startsWith('/media') ? path : `/media${path}`;
              doc.pdf_file = `${backendUrl}${mediaPath}`;
            }
            return doc;
          });
        }

        this.subject = result;
        this.isInitialLoading = false;

        // Trình duyệt cần detectChanges để cập nhật UI sau khi lấy từ Cache (đồng bộ)
        if (isPlatformBrowser(this.platformId)) {
          this.cdr.detectChanges();
        }

        if (result.documents && result.documents.length > 0) {
          this.selectDocument(result.documents[0]);
        } else {
          this._loadHistoryAndFocus();
        }

        // [NEW] Tự động bắt đầu bài giảng nếu ở chế độ nhúng (Lesson View)
        if (this.isEmbedded && this.lessonContext && !this.hasStartedAutoMessage) {
          this.hasStartedAutoMessage = true;
          // Đợi một chút để UI ổn định rồi mới gửi
          setTimeout(() => {
            this.newMessage = this.lessonContext || '';
            this.sendMessage();
          }, 500);
        }

        // [NEW] Tự động phân tích lỗi sai từ Quiz Practice (nếu có)
        if (!this.isEmbedded && !this.hasStartedAutoMessage) {
          const reviewContext = sessionStorage.getItem('ai_review_context');
          if (reviewContext) {
            this.hasStartedAutoMessage = true;
            // Xóa ngay để tránh gửi lại khi reload
            sessionStorage.removeItem('ai_review_context');
            sessionStorage.removeItem('ai_review_subject_id');
            sessionStorage.removeItem('ai_review_chapter');

            setTimeout(() => {
              this.newMessage = reviewContext;
              this.sendMessage();
            }, 800);
          }
        }

        // [NEW] Tự động khởi tạo AI Tutor Mode từ Pre-test (nếu có)
        if (!this.isEmbedded && !this.hasStartedAutoMessage) {
          const tutorContext = sessionStorage.getItem('ai_tutor_context');
          if (tutorContext) {
            this.hasStartedAutoMessage = true;
            // Xóa ngay để tránh gửi lại khi reload
            sessionStorage.removeItem('ai_tutor_context');

            setTimeout(() => {
              this.newMessage = tutorContext;
              this.sendMessage();
            }, 800);
          }
        }

        // [NEW] Tự động khởi tạo AI Tutor Remedial Mode (Sửa lỗi sau Post-test)
        if (!this.isEmbedded && !this.hasStartedAutoMessage) {
          const remedialContext = sessionStorage.getItem('ai_tutor_remedial_context');
          if (remedialContext) {
            this.hasStartedAutoMessage = true;
            sessionStorage.removeItem('ai_tutor_remedial_context');
            sessionStorage.removeItem('ai_tutor_remedial_subject_id');

            setTimeout(() => {
              this.newMessage = remedialContext;
              this.sendMessage();
            }, 800);
          }
        }
      },
      error: (err) => {
        console.error('Error loading subject', err);
        this.isInitialLoading = false;
        this.errorLoading = true;
        this.isLoading = false;
        this.debugMessage = 'Lỗi API Backend: ' + (err.message || JSON.stringify(err));
        if (isPlatformBrowser(this.platformId)) {
          this.cdr.detectChanges();
        }
      }
    });
  }

  selectDocument(doc: TeacherDocument): void {
    this.selectedDocument = doc;
    this.showPdf = false;

    // [FIX] Sanitize URL once here instead of using a getter to prevent iframe reload on every keystroke
    if (doc.pdf_file && doc.pdf_file.startsWith('http')) {
      this.currentSafePdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(doc.pdf_file);
    } else {
      this.currentSafePdfUrl = null;
    }

    this._loadHistoryAndFocus();
  }

  private _loadHistoryAndFocus(): void {
    // If not using a specific thread, just start new chat
    if (!this.currentThreadId) {
      this.messages = [];
    }
    this.isLoading = false;

    setTimeout(() => {
      this.messageInput?.nativeElement?.focus();
    }, 100);
  }

  /** Convert Markdown + LaTeX to sanitized HTML with optional KaTeX rendering */
  private parseMarkdown(text: string, skipKatex: boolean = false): SafeHtml {
    try {
      // ── Step 1: Extract math BEFORE marked.js can escape backslashes ──
      const mathMap: { placeholder: string; latex: string; display: boolean }[] = [];
      let counter = 0;

      // Display math $$...$$ — process multi-line expressions safely
      let processed = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, math) => {
        const ph = `EDUTEX${counter}D`;
        counter++;
        // If skipKatex is true, we still want to show the original math as text
        mathMap.push({ placeholder: ph, latex: math, display: true });
        return ph;
      });

      // Display math \[ ... \] (Block)
      processed = processed.replace(/\\\[([\s\S]+?)\\\]/g, (match, math) => {
        const ph = `EDUTEX${counter}D`;
        counter++;
        mathMap.push({ placeholder: ph, latex: math, display: true });
        return ph;
      });

      // Inline math $...$ — greedy match handles long expressions correctly
      processed = processed.replace(/\$([^$\n]+)\$/g, (match, math) => {
        // Remove smart filter to aggressively render all $...$ as Math
        const ph = `EDUTEX${counter}I`;
        counter++;
        mathMap.push({ placeholder: ph, latex: math, display: false });
        return ph;
      });

      // ── Step 2: Parse Markdown on the math-free text ──
      let html: string = marked.parse(processed, { breaks: true, gfm: true }) as string;

      // ── Step 3: Render each math expression with KaTeX (NPM Package) ──
      if (!skipKatex) {
        for (const { placeholder, latex, display } of mathMap) {
          try {
            const rendered = katex.renderToString(latex.trim(), {
              displayMode: display,
              throwOnError: false, // KaTeX will return an error span instead of throwing
              output: 'html',
              strict: false // Relax KaTeX rules to avoid failing on minor syntax errors
            });
            html = html.replace(placeholder, rendered);
          } catch (err) {
            console.warn('KaTeX fallback for:', latex, err);
            html = html.replace(placeholder, display ? `$$${latex}$$` : `$${latex}$`);
          }
        }
      } else {
        // Skip rendering or KaTeX not loaded — restore original raw LaTeX
        for (const { placeholder, latex, display } of mathMap) {
          html = html.replace(placeholder, display ? `$$${latex}$$` : `$${latex}$`);
        }
      }

      return this.sanitizer.bypassSecurityTrustHtml(html);
    } catch {
      return this.sanitizer.bypassSecurityTrustHtml(text.replace(/\n/g, '<br>'));
    }
  }

  sendMessage(): void {
    if ((!this.newMessage.trim() && !this.attachedImage) || !this.subject || this.isLoading) return;

    const userMsg: ChatMessage = {
      subject: this.subject.id,
      role: 'user',
      content: this.newMessage || 'Gửi một hình ảnh',
      imageUrl: this.attachedImage || undefined,
      safeHtml: this.sanitizer.bypassSecurityTrustHtml(this.newMessage)
    };

    this.messages.push(userMsg);
    const text = this.newMessage;
    const imgData = this.attachedImage;

    // Clear input
    this.newMessage = '';
    this.attachedImage = null;
    this.isLoading = true;
    this.shouldScroll = true;

    // Create a placeholder for the AI response
    const assistantMsg: ChatMessage = {
      subject: this.subject.id,
      role: 'assistant',
      content: '',
      safeHtml: this.sanitizer.bypassSecurityTrustHtml('')
    };
    this.messages.push(assistantMsg);

    // Build the context for the AI
    let contextTitle = this.subject.name;
    if (this.selectedDocument) contextTitle = this.selectedDocument.title;

    const lessonContext = `[Môn học: ${this.subject.name}] [Tài liệu: ${contextTitle}] ${text}`;

    // Build prior chat history (exclude the placeholder we just added)
    const historyForApi = this.messages.slice(0, -2).map(m => ({
      role: m.role === 'user' ? 'human' : 'ai',
      content: m.content
    }));

    this.chatService.getChatStream(
      lessonContext,
      this.authService.getUserId() || 1, // Lấy ID động từ AuthService, fallback về 1
      this.subject.name,
      historyForApi,
      imgData || undefined,
      this.currentThreadId
    ).subscribe({
      next: (event: any) => {
        if (event.type === 'token') {
          // Clear status indicator once real content arrives
          if (assistantMsg.statusText) assistantMsg.statusText = undefined;
          assistantMsg.content += event.content;

          clearTimeout(this.renderTimer);
          this.renderTimer = setTimeout(() => {
            assistantMsg.safeHtml = this.parseMarkdown(assistantMsg.content, true);
            this.shouldScroll = true;
            this.cdr.detectChanges();
          }, 30);
        } else if (event.type === 'tool_start') {
          // Show human-readable status chip instead of writing to content
          const toolLabels: Record<string, string> = {
            'search_agent_builder': '🔍 Đang tra cứu sách giáo khoa...',
            'read_textbook_page': '📖 Đang đọc trang sách...',
            'generate_quick_quiz': '✏️ Đang soạn bài tập...',
            'check_student_progress': '📊 Đang kiểm tra tiến độ...',
          };
          const raw = event.content?.replace('Đang xử lý: ', '').replace('...', '').trim();
          assistantMsg.statusText = toolLabels[raw] || `⚙️ ${event.content}`;
          this.shouldScroll = true;
          this.cdr.detectChanges();
        } else if (event.type === 'error') {
          assistantMsg.content = `❌ Lỗi: ${event.content}`;
          assistantMsg.safeHtml = this.parseMarkdown(assistantMsg.content, false);
          this.isLoading = false;
          this.cdr.detectChanges();
        } else if (event.type === 'done') {
          this.isLoading = false;
          clearTimeout(this.renderTimer);

          // [FEAT] Rendering math fully now that the response is complete
          assistantMsg.safeHtml = this.parseMarkdown(assistantMsg.content, false);
          this.shouldScroll = true;
          this.cdr.detectChanges();

          // Wait for DOM to update with final HTML before querying for Mermaid
          setTimeout(() => {
            this._renderMermaid();
          }, 50);

          // [FIX #1] Persist to Django
          if (this.subject) {
            this.chatService.saveChatPair(
              this.subject.id,
              text, // The original user message text
              assistantMsg.content, // The full AI response content
              this.currentThreadId,
              assistantMsg.citations || [], // [NEW] Lưu trích dẫn
              imgData // Pass the image data
            ).subscribe({
              next: (res) => {
                this.currentThreadId = res.thread_id;
                this.loadThreads();

                // Add threadId to URL without reloading
                if (isPlatformBrowser(this.platformId)) {
                  const url = new URL(window.location.href);
                  url.searchParams.set('threadId', res.thread_id);
                  window.history.replaceState({}, '', url.toString());

                  if (this.isEmbedded && this.lessonContext) {
                    sessionStorage.setItem(`lesson_thread_${this.subject?.id}_${this.lessonContext}`, res.thread_id);
                  }
                }
              },
              error: (err) => console.error('Failed to persist chat history', err)
            });
          }
        } else if (event.type === 'citations') {
          // [FEAT] Nhận trích dẫn từ AI Service
          assistantMsg.citations = event.content;

          // PDF Pre-loading: Nếu có trích dẫn, hãy đảm bảo Panel PDF sẵn sàng
          if (assistantMsg.citations && assistantMsg.citations.length > 0) {
            this._preloadPdf(assistantMsg.citations[0]);
          }
          this.cdr.detectChanges();
        }
      },
      error: (err: any) => {
        this.isLoading = false;
        assistantMsg.content = '❌ Không thể kết nối với AI Service. Vui lòng thử lại.';
        assistantMsg.safeHtml = this.parseMarkdown(assistantMsg.content, false);
        console.error('Chat stream error:', err);
        this.cdr.detectChanges();
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  clearChat(): void {
    if (this.messages.length === 0) return;
    this.showDeleteModal = true;
  }

  confirmDelete(): void {
    if (!this.currentThreadId) return;

    this.chatService.deleteThread(this.currentThreadId).subscribe({
      next: () => {
        this.messages = [];
        this.currentThreadId = null;
        this.loadThreads();
        this.showDeleteModal = false;
        
        // Gọi hàm startNewChat để reset lại toàn bộ state và tự động gửi lại tin nhắn
        this.startNewChat();
      },
      error: (err) => {
        console.error('Failed to clear chat history', err);
        // Fallback local clear if backend fails
        this.messages = [];
        this.currentThreadId = null;
        this.showDeleteModal = false;
        this.startNewChat();
      }
    });
  }

  cancelDelete(): void {
    this.showDeleteModal = false;
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        this.attachedImage = reader.result as string;
        this.cdr.detectChanges();
      };
      reader.readAsDataURL(file);
    }
  }

  onPaste(event: ClipboardEvent): void {
    const items = event.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onload = () => {
            this.attachedImage = reader.result as string;
            this.cdr.detectChanges();
          };
          reader.readAsDataURL(file);
        }
      }
    }
  }

  removeAttachedImage(): void {
    this.attachedImage = null;
  }

  private scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch (err) { }
  }

  /**
   * [NEW] Xem nguồn tài liệu cụ thể
   */
  viewSource(citation: any): void {
    if (!this.subject) return;

    // 1. Tìm tài liệu khớp với tiêu đề trích dẫn
    const doc = this.subject.documents?.find(d =>
      citation.title.toLowerCase().includes(d.title.toLowerCase()) ||
      d.title.toLowerCase().includes(citation.title.toLowerCase())
    );

    if (doc) {
      this.selectDocument(doc);
      // 2. Mở panel & Tự động hiện PDF
      this.isBookPanelOpen = true;
      this.isSidebarVisible = false;
      this.showPdf = true;

      // 3. Nhảy đến trang (PDF Viewer thường hỗ trợ #page=N)
      const page = citation.page || 1;
      const offset = this.subject.page_offset || 0;
      const actualPdfPage = page + offset;

      if (doc.pdf_file) {
        const baseUrl = doc.pdf_file.split('#')[0];
        this.currentSafePdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(`${baseUrl}#page=${actualPdfPage}`);
      }
    }
    this.cdr.detectChanges();
  }

  /**
   * [NEW] Tải trước PDF để tăng tốc
   */
  private _preloadPdf(citation: any): void {
    if (!this.subject || this.selectedDocument) return;

    const doc = this.subject.documents?.find(d =>
      citation.title.toLowerCase().includes(d.title.toLowerCase())
    );

    if (doc && !this.currentSafePdfUrl) {
      this.currentSafePdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(doc.pdf_file || '');
    }
  }
}
