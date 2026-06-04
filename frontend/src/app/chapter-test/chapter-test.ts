import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { getBackendUrl } from '../core/utils/api-base.util';
import { PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import katex from 'katex';

@Component({
  selector: 'app-chapter-test',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chapter-test.html',
  styleUrls: ['./chapter-test.css']
})
export class ChapterTest implements OnInit, OnDestroy {
  // Route params
  subjectId!: number;
  chapterId!: number;

  // UI state
  chapterTitle = '';
  testMode: string = 'chapter_test'; // 'chapter_test' | 'post_test'
  isLoading = true;
  isSubmitting = false;
  showResultModal = false;
  testCompleted = false;

  // Data
  quizId!: number;
  questions: any[] = [];
  answers: { [questionId: string]: number } = {};

  // Results
  score: number = 0;
  correctCount: number = 0;
  totalCount: number = 0;

  private platformId = inject(PLATFORM_ID);

  // Getters for Template
  get answeredCount(): number {
    return Object.keys(this.answers).length;
  }

  get progressPercent(): number {
    if (!this.questions || this.questions.length === 0) return 0;
    return (this.answeredCount / this.questions.length) * 100;
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.subjectId = Number(this.route.snapshot.paramMap.get('subjectId'));
    this.chapterId = Number(this.route.snapshot.paramMap.get('chapterId'));
    this.testMode = this.route.snapshot.queryParamMap.get('mode') || 'chapter_test';

    if (isPlatformBrowser(this.platformId)) {
      this.loadChapterTest();
    }
  }

  ngOnDestroy(): void {}

  loadChapterTest() {
    this.isLoading = true;
    const url = `${getBackendUrl(this.platformId)}/api/quiz/chapter-test/?chapter_id=${this.chapterId}&mode=${this.testMode}`;

    this.http.get<any>(url).subscribe({
      next: (res) => {
        const baseTitle = res.chapter_title || `Kiểm tra Chương`;
        this.chapterTitle = this.testMode === 'post_test'
          ? `${baseTitle} — Đánh giá đầu ra`
          : baseTitle;
        // Shuffle đáp án A/B/C/D mỗi lần tải để tránh học thuộc vị trí
        this.questions = (res.questions || []).map((q: any) => ({
          ...q,
          answers: this._shuffleArray([...q.answers])
        }));
        this.quizId = res.chapter_id;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Lỗi tải bài test:', err);
        this.isLoading = false;
        alert(`Không tải được bài test: ${err.error?.error || 'Lỗi kết nối'}`);
      }
    });
  }

  /** Xáo trộn mảng ngẫu nhiên (Fisher-Yates) */
  private _shuffleArray<T>(arr: T[]): T[] {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  selectOption(questionId: number, answerId: number) {
    if (this.testCompleted) return;
    this.answers[String(questionId)] = answerId;
  }

  isSelected(questionId: number, answerId: number): boolean {
    return this.answers[String(questionId)] === answerId;
  }

  canSubmit(): boolean {
    return this.questions.length > 0 && this.answeredCount === this.questions.length;
  }

  submitTest() {
    if (!this.canSubmit()) return;
    this.isSubmitting = true;

    // Phân biệt endpoint nộp bài dựa trên testMode
    const endpoint = this.testMode === 'post_test' ? 'post-test/submit' : 'chapter-test/submit';
    const url = `${getBackendUrl(this.platformId)}/api/quiz/${endpoint}/`;
    
    const body = {
      chapter_id: this.chapterId,
      answers: this.answers
    };

    this.http.post<any>(url, body).subscribe({
      next: (res) => {
        this.isSubmitting = false;
        // Nếu là post_test -> sang trang kết quả post-test, ngược lại dùng pre-test-result (polling)
        if (this.testMode === 'post_test') {
          this.router.navigate(['/post-test-result', res.submission_id]);
        } else {
          this.router.navigate(['/pre-test-result', res.submission_id]);
        }
      },
      error: (err) => {
        console.error('Lỗi nộp bài:', err);
        this.isSubmitting = false;
        alert('Không thể nộp bài, vui lòng thử lại.');
      }
    });
  }


  getScoreLabel(): string {
    if (this.score >= 80) return 'Xuất sắc! 🏆';
    if (this.score >= 60) return 'Khá tốt! 👍';
    if (this.score >= 40) return 'Cần cố gắng thêm 📖';
    return 'Cần ôn lại chương này 💪';
  }

  getScoreColor(): string {
    if (this.score >= 80) return '#22c55e';
    if (this.score >= 60) return '#f59e0b';
    if (this.score >= 40) return '#f97316';
    return '#ef4444';
  }

  isCorrect(q: any): boolean {
    const correctAnswer = q.answers.find((a: any) => a.is_correct);
    return this.answers[String(q.id)] === correctAnswer?.id;
  }

  getUserChoiceText(q: any): string {
    const choiceId = this.answers[String(q.id)];
    return q.answers.find((a: any) => a.id === choiceId)?.answer_text || 'Chưa chọn';
  }

  getCorrectChoiceText(q: any): string {
    return q.answers.find((a: any) => a.is_correct)?.answer_text || '';
  }

  tryAgain() {
    this.answers = {};
    this.showResultModal = false;
    this.testCompleted = false;
    this.score = 0;
  }

  goBack() {
    this.router.navigate(['/select-chapter', this.subjectId]);
  }

  goToDashboard() {
    this.router.navigate(['/dashboard']);
  }

  goToLearningPath() {
    // Dùng interceptor tự gắn token (auth_token), không set header thủ công
    const url = `${getBackendUrl(this.platformId)}/api/users/learning-path/?subject_id=${this.subjectId}`;

    this.http.get<any[]>(url).subscribe({
      next: (paths) => {
        if (paths && paths.length > 0) {
          this.router.navigate(['/learning-path', paths[0].id]);
        } else {
          // Fallback khi học sinh chưa có lộ trình học cho môn này
          const confirmMsg = 'Bạn chưa có Lộ trình học AI (AI Learning Path) cho môn học này.\n\nBạn có muốn làm bài Đánh giá đầu vào (Pre-test) để AI phân tích và tạo lộ trình không?';
          if (confirm(confirmMsg)) {
            this.router.navigate(['/pre-test', this.subjectId]);
          }
        }
      },
      error: () => this.router.navigate(['/dashboard'])
    });
  }

  goToChatWithAI() {
    let wrongQuestionsText = '';
    const wrongItems = this.questions.filter(q => !this.isCorrect(q));

    if (wrongItems.length > 0) {
      wrongQuestionsText = '\n--- CHI TIẾT CÁC CÂU HỎI LÀM SAI ---\n';
      wrongItems.forEach((q, index) => {
        wrongQuestionsText += `Câu ${index + 1} (Chương: ${this.chapterTitle}): ${q.question_text}\n`;
        wrongQuestionsText += `- Học sinh chọn: ${this.getUserChoiceText(q)}\n`;
        wrongQuestionsText += `- Đáp án ĐÚNG: ${this.getCorrectChoiceText(q)}\n\n`;
      });
    }

    const aiPrompt = `[CHẾ ĐỘ GIA SƯ CHỦ ĐỘNG - KẾT QUẢ KIỂM TRA CHƯƠNG]
Tôi vừa hoàn thành bài kiểm tra chương "${this.chapterTitle}".
Điểm của tôi là: ${this.score}/100.
${wrongQuestionsText}
## VAI TRÒ
Bạn là gia sư AI chủ động, dẫn dắt hoàn toàn buổi học.
Học sinh KHÔNG cần biết phải làm gì — bạn luôn chỉ rõ bước tiếp theo.

## TRẠNG THÁI (lưu trong conversation)
- phase: "planning" -> "teaching"
- current_topic: Dựa vào các lỗi sai của học sinh trong bài kiểm tra

## QUY TẮC BẮT BUỘC
1. Mỗi tin nhắn PHẢI kết thúc bằng câu hỏi hoặc nhiệm vụ cụ thể.
2. Bạn phải phân tích ĐÚNG CHỖ SAI của học sinh dựa trên TỪNG CÂU HỎI mà học sinh làm sai ở trên. Đừng dạy lại từ đầu nếu không cần thiết.
3. Giải thích tối đa 3-4 câu, sau đó hỏi ngay.
4. Không chờ học sinh chủ động — bạn luôn dẫn đường.
5. Nếu học sinh lạc đề → nhẹ nhàng kéo về bài học.
6. Sau 3 lần giải thích sai cùng 1 khái niệm → đổi hoàn toàn cách tiếp cận (ví dụ, hình ảnh, câu chuyện).
7. Thường xuyên GIAO BÀI TẬP (mini-quiz) để học sinh tự làm và kiểm tra lại kiến thức.

## LUỒNG CHÍNH
công bố kế hoạch sửa lỗi → phân tích lý do sai của từng câu hỏi cụ thể → dạy khái niệm sửa lỗi → hỏi kiểm tra → [đúng: tiếp] [sai: giải thích lại] → giao bài tập (mini-quiz) → kết thúc

Bắt đầu bằng việc CHÀO MỪNG, CÔNG BỐ lộ trình học rút gọn (tập trung vào những lỗi sai cụ thể trong bài kiểm tra vừa rồi), và BẮT ĐẦU DẠY phần đầu tiên ngay lập tức!`;

    sessionStorage.setItem('ai_tutor_context', aiPrompt);

    // Lấy pathId hiện tại nếu có để truyền vào chat, nếu không có thì truyền null
    const url = `${getBackendUrl(this.platformId)}/api/users/learning-path/?subject_id=${this.subjectId}`;
    this.http.get<any[]>(url).subscribe({
      next: (paths) => {
        const pathId = (paths && paths.length > 0) ? paths[0].id : null;
        this.router.navigate(['/chat', this.subjectId], {
          queryParams: {
            pathId: pathId,
            mode: 'guided'
          }
        });
      },
      error: () => {
        this.router.navigate(['/chat', this.subjectId], { queryParams: { mode: 'guided' } });
      }
    });
  }

  renderMath(text: string): SafeHtml {
    if (!text) return '';
    try {
      let processed = text;
      processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (_, f) => katex.renderToString(f, { displayMode: true, throwOnError: false }));
      processed = processed.replace(/\\\[([\s\S]+?)\\\]/g, (_, f) => katex.renderToString(f, { displayMode: true, throwOnError: false }));
      processed = processed.replace(/\$([^$\n]+)\$/g, (_, f) => katex.renderToString(f, { displayMode: false, throwOnError: false }));
      processed = processed.replace(/\\\(([\s\S]+?)\\\)/g, (_, f) => katex.renderToString(f, { displayMode: false, throwOnError: false }));
      return this.sanitizer.bypassSecurityTrustHtml(processed);
    } catch (e) {
      return text;
    }
  }
}
