import { Component, OnInit, inject, PLATFORM_ID, ViewChild } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LearningPathService, LearningPath, LearningPathItem } from '../core/services/learning-path.service';
import { SubjectService, Subject, TeacherDocument } from '../core/services/subject.service';
import { ChatComponent } from '../chat/chat.component';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-lesson-view',
  standalone: true,
  imports: [CommonModule, RouterLink, ChatComponent],
  templateUrl: './lesson-view.html',
  styleUrls: ['./lesson-view.css']
})
export class LessonView implements OnInit {
  @ViewChild(ChatComponent) chatComponent!: ChatComponent;

  pathId!: number;
  itemId!: number;
  learningPath: LearningPath | null = null;
  currentItem: LearningPathItem | null = null;

  isLoading = true;
  isCompleting = false;

  // UI State
  isSidebarCollapsed = false;
  showPdf = false;
  activeStep = 1; // Phương pháp học hiện tại (1-3)

  subject: Subject | null = null;
  selectedDocument: TeacherDocument | null = null;
  safePdfUrl: SafeResourceUrl | null = null;

  private platformId = inject(PLATFORM_ID);
  private subjectService = inject(SubjectService);
  private sanitizer = inject(DomSanitizer);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private learningPathService: LearningPathService
  ) { }

  ngOnInit(): void {
    this.pathId = Number(this.route.snapshot.paramMap.get('pathId'));
    this.itemId = Number(this.route.snapshot.paramMap.get('itemId'));

    if (isPlatformBrowser(this.platformId)) {
      this.loadData();
    } else {
      this.isLoading = false;
    }
  }

  loadData() {
    this.isLoading = true;
    this.learningPathService.getLearningPathDetail(this.pathId).subscribe({
      next: (res) => {
        this.learningPath = res;
        this.currentItem = res.items.find(i => i.id === this.itemId) || null;

        if (this.learningPath?.subject) {
          this.loadSubjectDetails(this.learningPath.subject);
        } else {
          this.isLoading = false;
        }
      },
      error: (err) => {
        console.error('Failed to load lesson context', err);
        this.isLoading = false;
      }
    });
  }

  loadSubjectDetails(subjectId: number) {
    this.subjectService.getSubjectDetail(subjectId).subscribe({
      next: (res) => {
        this.subject = res;

        if (res.documents && res.documents.length > 0) {
          this.selectedDocument = res.documents[0];
          if (this.selectedDocument.pdf_file) {
            let url = this.selectedDocument.pdf_file;
            if (!url.startsWith('http')) {
              const backendUrl = 'http://localhost:8000';
              const cleanPath = url.startsWith('/') ? url : `/${url}`;
              const mediaPath = cleanPath.startsWith('/media') ? cleanPath : `/media${cleanPath}`;
              url = `${backendUrl}${mediaPath}`;
            }
            this.safePdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
          }
        }

        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading subject details', err);
        this.isLoading = false;
      }
    });
  }

  // ── UI Actions ──

  toggleSidebar() {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
  }

  togglePdf() {
    this.showPdf = !this.showPdf;
  }

  /**
   * Gửi gợi ý nhanh vào AI Chat thông qua ViewChild.
   * ChatComponent có property `newMessage` và method `sendMessage()`.
   */
  sendQuickPrompt(prompt: string) {
    if (!this.chatComponent) return;

    // Đặt nội dung vào input chat rồi gửi
    this.chatComponent.newMessage = prompt;
    this.chatComponent.sendMessage();

    // Cập nhật activeStep dựa trên hành vi
    if (prompt.includes('Bài tập') || prompt.includes('bài tập')) {
      this.activeStep = 2;
    } else {
      this.activeStep = Math.max(this.activeStep, 1);
    }
  }

  // ── Context for AI Tutor ──

  /**
   * Tín hiệu kích hoạt AI Tutor bắt đầu buổi học.
   * Không còn dùng các câu văn dài dòng, AI sẽ tự động tra cứu tiến độ.
   */
  get lessonContext(): string {
    if (!this.currentItem) return '';
    const name = this.currentItem.lesson_title || this.currentItem.quiz_title || 'bài học';
    const lessonId = this.currentItem.lesson_id ?? null;
    const chapterId = this.currentItem.chapter_id || null;
    // Bắt buộc AI gọi tool với các tham số này và tuân thủ định dạng. Các từ khóa được thiết kế khớp với agent.py
    return `[system_start_lesson] [YÊU CẦU BẮT BUỘC]: Hãy kiểm tra tiến độ học tập của tôi. BẠN PHẢI gọi công cụ \`check_student_progress\` [lesson_id:${lessonId ?? ''}] [chapter_id:${chapterId ?? ''}].
CHỈ liệt kê ĐÚNG những câu hỏi mà tôi đã làm sai liên quan đến bài ${name}, hãy giải thích và tuyệt đối KHÔNG liệt kê những câu không liên quan. Mọi câu trả lời PHẢI tuân theo cấu trúc sau:

BẠN PHẢI TRẢ LỜI THEO ĐÚNG CẤU TRÚC SAU:
Chào bạn, mình đã xem xét kỹ lưỡng kết quả học tập của bạn. Dựa trên dữ liệu hệ thống, bạn đang gặp một số khó khăn với các khái niệm về bài ${name}. Cụ thể, bạn đã làm sai các câu hỏi sau đây liên quan đến bài "${name}" trong bài Đánh giá đầu vào:

Những câu hỏi bạn đã làm sai (Chỉ liên quan đến ${name}):
CÂU SAI #1:
Chương: [Tên chương]
Câu hỏi: [Nội dung câu hỏi]
Bạn chọn: [Đáp án user chọn]
Đáp án đúng: [Đáp án đúng]
Giải thích: [Giải thích chi tiết lỗi sai]
(Lặp lại cho các câu sai tiếp theo...)

Đánh giá điểm yếu và Lộ trình học tập:
Điểm yếu chính:
- [Điểm yếu 1]
- [Điểm yếu 2]

Lộ trình học tập đề xuất:
Giai đoạn 1: [Tên giai đoạn]
- [Chi tiết]
Giai đoạn 2: [Tên giai đoạn]
- [Chi tiết]

Bây giờ, chúng ta hãy cùng làm một vài câu hỏi nhỏ để kiểm tra xem bạn đã nắm được phần nào nhé! 💡
[Liệt kê 3 câu hỏi trắc nghiệm liên quan đến phần yếu nhất]

Hãy trả lời các câu hỏi này, chúng ta sẽ cùng nhau kiểm tra đáp án! 😊`;
  }

  // ── Navigation ──

  completeLesson() {
    if (this.isCompleting) return;
    this.isCompleting = true;
    this.activeStep = 2; // Đánh dấu bước cuối
    this.learningPathService.completeItem(this.itemId).subscribe({
      next: () => {
        this.isCompleting = false;
        this.router.navigate(['/learning-path', this.pathId]);
      },
      error: () => {
        this.isCompleting = false;
        alert('Lỗi khi đánh dấu hoàn thành bài học');
      }
    });
  }

  goToChapterTest() {
    const chapterId = this.currentItem?.chapter_id;
    const subjectId = this.learningPath?.subject;

    if (chapterId && subjectId) {
      this.router.navigate(['/chapter-test', subjectId, chapterId]);
    } else if (subjectId) {
      this.router.navigate(['/select-chapter', subjectId]);
    }
  }
}
