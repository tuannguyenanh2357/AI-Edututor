import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { LearningPathService, PreTestQuestion } from '../core/services/learning-path.service';
import katex from 'katex';

@Component({
  selector: 'app-pre-test',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pre-test.html',
  styleUrls: ['./pre-test.css']
})
export class PreTest implements OnInit, OnDestroy {
  subjectId!: number;
  quizId!: number;
  questions: PreTestQuestion[] = [];
  
  isLoading = true;
  isSubmitting = false;

  // Modal & Polling state
  showResultModal = false;
  gradingStatus: 'grading' | 'completed' | 'error' = 'grading';
  submissionResult: any = null;
  private pollInterval: any;

  // Lưu đáp án user: { question_id: answer_id }
  answers: { [questionId: string]: number } = {};

  get answeredCount(): number {
    return Object.keys(this.answers).length;
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private learningPathService: LearningPathService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.subjectId = Number(this.route.snapshot.paramMap.get('subjectId'));
    this.loadPreTest();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  loadPreTest() {
    this.isLoading = true;
    this.learningPathService.getPreTest(this.subjectId).subscribe({
      next: (res) => {
        this.quizId = res.id;
        this.questions = res.questions;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Lỗi tải Pre-Test', err);
        this.isLoading = false;
        alert('Có lỗi khi tạo bài test. Vui lòng thử lại sau.');
      }
    });
  }

  selectOption(questionId: number, answerId: number) {
    this.answers[String(questionId)] = answerId;
  }

  isSelected(questionId: number, answerId: number): boolean {
    return this.answers[String(questionId)] === answerId;
  }

  canSubmit(): boolean {
    return Object.keys(this.answers).length === this.questions.length;
  }

  submitTest() {
    if (!this.canSubmit()) return;
    
    this.isSubmitting = true;
    this.showResultModal = true;
    this.gradingStatus = 'grading';

    const submissionData = {
      quiz_id: this.quizId,
      answers: this.answers
    };

    this.learningPathService.submitPreTest(submissionData).subscribe({
      next: (res) => {
        this.isSubmitting = false;
        this.startPolling(res.submission_id);
      },
      error: (err) => {
        console.error('Lỗi nộp bài', err);
        this.isSubmitting = false;
        this.gradingStatus = 'error';
      }
    });
  }

  startPolling(submissionId: number) {
    this.checkResult(submissionId);
    this.pollInterval = setInterval(() => {
      this.checkResult(submissionId);
    }, 3000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }

  checkResult(submissionId: number) {
    this.learningPathService.getPreTestResult(submissionId).subscribe({
      next: (res) => {
        if (res.evaluator_status === 'completed') {
          this.stopPolling();
          this.submissionResult = res;
          this.gradingStatus = 'completed';
        }
      },
      error: () => {
        this.gradingStatus = 'error';
        this.stopPolling();
      }
    });
  }

  /** Chuyển sang trang Lộ trình học tập chi tiết */
  startLearning() {
    if (this.submissionResult && this.submissionResult.learning_path_id) {
      this.router.navigate(['/learning-path', this.submissionResult.learning_path_id]);
    } else {
      // Fallback: Tìm lộ trình gần nhất cho môn này
      this.isLoading = true;
      this.learningPathService.getLearningPaths(this.subjectId).subscribe({
        next: (paths) => {
          if (paths && paths.length > 0) {
            this.router.navigate(['/learning-path', paths[0].id]);
          } else {
            this.router.navigate(['/dashboard']);
          }
        },
        error: () => this.router.navigate(['/dashboard'])
      });
    }
  }

  closeModal() {
    if (this.gradingStatus === 'completed') {
      // Dẫn thẳng vào lộ trình học thay vì dashboard
      this.startLearning();
    } else {
      this.showResultModal = false;
    }
  }

  /** Kiểm tra xem câu trả lời của user cho 1 câu hỏi là đúng hay sai */
  isCorrect(q: any): boolean {
    const userChoiceId = this.submissionResult?.user_answers[String(q.id)];
    const correctAnswer = q.answers.find((a: any) => a.is_correct);
    return userChoiceId === correctAnswer?.id;
  }

  getUserChoiceText(q: any): string {
    const userChoiceId = this.submissionResult?.user_answers[String(q.id)];
    return q.answers.find((a: any) => a.id === userChoiceId)?.answer_text || 'Chưa chọn';
  }

  getCorrectChoiceText(q: any): string {
    return q.answers.find((a: any) => a.is_correct)?.answer_text || '';
  }

  /** Render LaTeX string to SafeHtml using KaTeX */
  renderMath(text: string): SafeHtml {
    if (!text) return '';
    try {
      // Logic: Tìm tất cả cặp $...$ hoặc \(...\) hoặc \[...\]
      // Ở đây ta dùng regex đơn giản để bóc tách và render
      let processed = text;

      // 1. Render Block Math: $$...$$ hoặc \[...\]
      processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (match, formula) => {
        return katex.renderToString(formula, { displayMode: true, throwOnError: false });
      });
      processed = processed.replace(/\\\[([\s\S]+?)\\\]/g, (match, formula) => {
        return katex.renderToString(formula, { displayMode: true, throwOnError: false });
      });

      // 2. Render Inline Math: $...$ hoặc \(...\)
      processed = processed.replace(/\$([^$\n]+)\$/g, (match, formula) => {
        return katex.renderToString(formula, { displayMode: false, throwOnError: false });
      });
      processed = processed.replace(/\\\(([\s\S]+?)\\\)/g, (match, formula) => {
        return katex.renderToString(formula, { displayMode: false, throwOnError: false });
      });

      return this.sanitizer.bypassSecurityTrustHtml(processed);
    } catch (e) {
      console.warn('KaTeX error:', e);
      return text;
    }
  }
}
