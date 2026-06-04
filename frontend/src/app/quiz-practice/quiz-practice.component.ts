import {
  Component, OnInit, OnDestroy, inject, PLATFORM_ID, ChangeDetectorRef
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { SubjectService, Subject, TeacherDocument } from '../core/services/subject.service';
import { QuizService, PracticeQuestion } from '../core/services/quiz.service';

// ─ Kiểu trạng thái Quiz ─
type QuizState = 'subject_select' | 'topic_select' | 'generating' | 'quiz_active' | 'result';

// ─ Câu hỏi đã được mở rộng với trạng thái học sinh ─
interface AnsweredQuestion extends PracticeQuestion {
  selected_index: number | null;  // null = chưa trả lời
  is_correct: boolean | null;
  show_explanation: boolean;
}

// ─ Giao diện dữ liệu Curriculum ─
interface Chapter {
  id: number;
  title: string;
  order_num: number;
}

interface Lesson {
  id: number;
  title: string;
  order_num: number;
}

import { MarkdownRenderPipe } from '../core/pipes/markdown-render.pipe';

@Component({
  selector: 'app-quiz-practice',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, MarkdownRenderPipe],
  templateUrl: './quiz-practice.component.html',
  styleUrls: ['./quiz-practice.component.css']
})
export class QuizPracticeComponent implements OnInit, OnDestroy {

  // ─ Services ─
  private platformId = inject(PLATFORM_ID);
  private route = inject(ActivatedRoute);
  private subjectService = inject(SubjectService);
  private quizService = inject(QuizService);
  private cdr = inject(ChangeDetectorRef);

  private subs = new Subscription();

  // ─ Dữ liệu ─
  subjects: Subject[] = [];
  subject: Subject | null = null;
  subjectId: number = 0;
  isSubjectListLoading: boolean = false;

  // ─ Curriculum Data ─
  chapters: Chapter[] = [];
  lessons: Lesson[] = [];
  selectedChapter: Chapter | null = null;
  selectedLesson: Lesson | null = null;

  // ─ Quản lý Quiz ─
  quizState: QuizState = 'topic_select';
  numQuestions: number = 5;
  questions: AnsweredQuestion[] = [];
  currentIndex: number = 0;
  readonly PASSING_SCORE = 70;

  // ─ UI helpers ─
  errorMessage: string = '';
  isDataLoading: boolean = true;
  isCurriculumLoading: boolean = false;
  readonly optionLabels = ['A', 'B', 'C', 'D'];

  // ─ Computed getters ─
  get currentQuestion(): AnsweredQuestion | null {
    return this.questions[this.currentIndex] ?? null;
  }

  get scorePercent(): number {
    if (this.questions.length === 0) return 0;
    const correct = this.questions.filter(q => q.is_correct === true).length;
    return Math.round((correct / this.questions.length) * 100);
  }

  get isPassed(): boolean {
    return this.scorePercent >= this.PASSING_SCORE;
  }

  get correctCount(): number {
    return this.questions.filter(q => q.is_correct === true).length;
  }

  get hasChapters(): boolean {
    return (this.chapters?.length ?? 0) > 0;
  }

  get selectionDisplay(): string {
    if (this.selectedLesson) return this.selectedLesson.title;
    if (this.selectedChapter) return this.selectedChapter.title;
    return this.subject?.name ?? '';
  }

  get chapterTitle(): string {
    return this.selectedChapter?.title ?? this.subject?.name ?? '';
  }

  getOptionNgClass(q: AnsweredQuestion, i: number): Record<string, boolean> {
    const notAnswered = q.selected_index === null;
    return {
      'correct': !notAnswered && i === q.correct_index,
      'wrong':   !notAnswered && i === q.selected_index && !q.is_correct,
      'dimmed':  !notAnswered && i !== q.correct_index && i !== q.selected_index,
    };
  }

  ngOnInit(): void {
    this.subjectId = Number(this.route.snapshot.paramMap.get('subjectId') ?? 0);

    // Chế độ chọn môn: khi không có subjectId hoặc subjectId=0
    if (!this.subjectId) {
      this.quizState = 'subject_select';
      this.isDataLoading = false;
      this._loadSubjectList();
      return;
    }

    // Tải thông tin môn học
    const subSubject = this.subjectService.getSubjectDetail(this.subjectId).subscribe({
      next: (s) => {
        this.subject = s;
        if (isPlatformBrowser(this.platformId)) this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[QuizPractice] Failed to load subject:', err);
        this.errorMessage = `Không tải được thông tin môn học.`;
      }
    });

    // Tải danh sách chương
    const subChapters = this.quizService.getChapters(this.subjectId).subscribe({
      next: (data) => {
        this.chapters = data;
        this.isDataLoading = false;
        if (isPlatformBrowser(this.platformId)) this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[QuizPractice] Failed to load chapters:', err);
        this.isDataLoading = false;
        if (isPlatformBrowser(this.platformId)) this.cdr.detectChanges();
      }
    });

    this.subs.add(subSubject);
    this.subs.add(subChapters);
  }

  private _loadSubjectList(): void {
    this.isSubjectListLoading = true;
    const sub = this.subjectService.getSubjects().subscribe({
      next: (data) => {
        this.subjects = data;
        this.isSubjectListLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[QuizPractice] Failed to load subjects:', err);
        this.isSubjectListLoading = false;
        this.cdr.detectChanges();
      }
    });
    this.subs.add(sub);
  }

  onSelectSubject(sub: Subject): void {
    this.subject = sub;
    this.subjectId = sub.id;
    this.isDataLoading = true;
    this.quizState = 'topic_select';
    this.cdr.detectChanges();

    const subChapters = this.quizService.getChapters(sub.id).subscribe({
      next: (data) => {
        this.chapters = data;
        this.isDataLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[QuizPractice] Failed to load chapters:', err);
        this.isDataLoading = false;
        this.cdr.detectChanges();
      }
    });
    this.subs.add(subChapters);
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  /** Trả về Font Awesome class đầy đủ cho icon môn học */
  getSubjectIconClass(sub: Subject): string {
    const icon = sub.icon_url || 'fa-graduation-cap';
    // Nếu đã có prefix 'fas'/'fa' thì giữ nguyên, không thì thêm 'fas'
    if (icon.startsWith('fas ') || icon.startsWith('fab ') || icon.startsWith('far ')) {
      return icon;
    }
    return `fas ${icon}`;
  }

  /** Trả về màu tương ứng cho từng môn */
  getSubjectColor(subjectName: string): string {
    const colorMap: Record<string, string> = {
      'Toán học':           '#ef4444',
      'Vật lý':             '#3b82f6',
      'Hóa học':            '#10b981',
      'Sinh học':           '#06b6d4',
      'Lịch sử':            '#f59e0b',
      'Địa lý':             '#8b5cf6',
      'Giáo dục công dân':  '#ec4899',
      'Tin học':            '#6366f1',
    };
    return colorMap[subjectName] || '#6c63ff';
  }

  /** Chọn chương và tải danh sách bài học */
  onSelectChapter(chapter: Chapter): void {
    this.selectedChapter = chapter;
    this.selectedLesson = null;
    this.lessons = [];
    this.isCurriculumLoading = true;
    this.cdr.detectChanges();

    const sub = this.quizService.getLessons(chapter.id).subscribe({
      next: (data) => {
        this.lessons = data;
        this.isCurriculumLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[QuizPractice] Failed to load lessons:', err);
        this.isCurriculumLoading = false;
        this.cdr.detectChanges();
      }
    });
    this.subs.add(sub);
  }

  /** Chọn bài học */
  onSelectLesson(lesson: Lesson): void {
    this.selectedLesson = lesson;
    this.cdr.detectChanges();
  }

  /** Quay lại bước chọn chương */
  backToChapters(): void {
    this.selectedChapter = null;
    this.selectedLesson = null;
    this.lessons = [];
    this.cdr.detectChanges();
  }

  /** Gọi AI Service sinh bài tập */
  generateQuiz(): void {
    if (!this.subject || (this.hasChapters && !this.selectedChapter && !this.selectedLesson)) return;

    this.errorMessage = '';
    this.quizState = 'generating';
    this.cdr.detectChanges();

    const sub = this.quizService.generateAIQuiz(
      this.subject.name,
      this.subject.grade_level ?? 10,
      this.selectionDisplay,
      this.numQuestions,
      this.selectedLesson?.id
    ).subscribe({
      next: (questions: PracticeQuestion[]) => {
        if (!questions || questions.length === 0) {
          this.errorMessage = 'AI không sinh được câu hỏi. Hãy thử lại!';
          this.quizState = 'topic_select';
          this.cdr.detectChanges();
          return;
        }
        this.questions = questions.map(q => ({
          ...q,
          selected_index: null,
          is_correct: null,
          show_explanation: false
        }));
        this.currentIndex = 0;
        this.quizState = 'quiz_active';
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[QuizPractice] Generate quiz error:', err);
        this.errorMessage = 'Kết nối AI gặp sự cố. Hãy kiểm tra lại và thử lại.';
        this.quizState = 'topic_select';
        this.cdr.detectChanges();
      }
    });

    this.subs.add(sub);
  }

  selectAnswer(optionIndex: number): void {
    const q = this.currentQuestion;
    if (!q || q.selected_index !== null) return;
    q.selected_index = optionIndex;
    q.is_correct = optionIndex === q.correct_index;
    q.show_explanation = true;
  }

  nextQuestion(): void {
    if (this.currentIndex < this.questions.length - 1) {
      this.currentIndex++;
    } else {
      this.quizState = 'result';
    }
  }

  retryNewTopic(): void {
    this.questions = [];
    this.currentIndex = 0;
    this.errorMessage = '';
    this.quizState = 'topic_select';
  }

  // ─ AI Review: Phân tích lỗi sai tự động ─

  private router = inject(Router);

  /**
   * Tổng hợp các câu sai thành prompt chi tiết để AI phân tích và dạy lại
   */
  getWrongAnalysis(): string {
    const wrongQuestions = this.questions.filter(q => q.is_correct === false);
    if (wrongQuestions.length === 0) return '';

    const topicName = this.selectionDisplay;
    let analysis = `[CHẾ ĐỘ: PHÂN TÍCH LỖI SAI - TỰ ĐỘNG DẠY LẠI]\n\n`;
    analysis += `Tôi vừa luyện tập "${topicName}" và sai ${wrongQuestions.length}/${this.questions.length} câu (Điểm: ${this.scorePercent}%).\n\n`;
    analysis += `Dưới đây là các câu tôi trả lời SAI. Hãy phân tích từng câu:\n\n`;

    wrongQuestions.forEach((q, i) => {
      const userAnswer = q.selected_index !== null ? q.options[q.selected_index] : 'Chưa chọn';
      const correctAnswer = q.options[q.correct_index];
      analysis += `--- Câu ${i + 1} ---\n`;
      analysis += `📌 Đề bài: ${q.question}\n`;
      analysis += `❌ Tôi chọn: ${userAnswer}\n`;
      analysis += `✅ Đáp án đúng: ${correctAnswer}\n`;
      if (q.explanation) {
        analysis += `💡 Giải thích: ${q.explanation}\n`;
      }
      analysis += `\n`;
    });

    analysis += `\nYêu cầu:\n`;
    analysis += `1. Phân tích chi tiết TẠI SAO tôi sai từng câu (lỗi tư duy gì?)\n`;
    analysis += `2. Giảng lại kiến thức trọng tâm liên quan đến các câu sai\n`;
    analysis += `3. Cho tôi 2-3 bài tập tương tự để luyện lại\n`;
    analysis += `4. Tóm tắt những điểm cần ghi nhớ để không sai lại`;

    return analysis;
  }

  /**
   * Chuyển đến AI Chat với context phân tích lỗi sai tự động.
   * AI sẽ nhận prompt và bắt đầu dạy lại ngay — học sinh không cần hỏi.
   */
  goToAIReview(): void {
    const analysis = this.getWrongAnalysis();
    if (!analysis) {
      // Đúng hết → không cần ôn
      return;
    }

    // Lưu prompt vào sessionStorage để ChatComponent tự gửi
    sessionStorage.setItem('ai_review_context', analysis);
    sessionStorage.setItem('ai_review_subject_id', String(this.subjectId));

    // Navigate đến AI Chat
    this.router.navigate(['/chat', this.subjectId]);
  }
}
