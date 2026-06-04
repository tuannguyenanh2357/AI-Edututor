import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { LearningPathService } from '../core/services/learning-path.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import katex from 'katex';

@Component({
  selector: 'app-post-test-result',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './post-test-result.html',
  styleUrls: ['./post-test-result.css']
})
export class PostTestResult implements OnInit, OnDestroy {
  submissionId!: number;
  resultStatus: 'evaluating' | 'completed' | 'failed' | 'error' = 'evaluating';
  
  // Data from API
  preScore: number = 0;
  postScore: number = 0;
  improvement: number = 0;
  aiFeedback: string = '';
  chapterTitle: string = '';
  subjectName: string = '';
  subjectId: number | null = null;
  learningPathId: number | null = null;
  
  questions: any[] = [];
  userAnswers: { [key: string]: number } = {};
  
  private pollInterval: any;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private learningPathService: LearningPathService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.submissionId = Number(this.route.snapshot.paramMap.get('submissionId'));
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  startPolling() {
    this.checkResult();
    this.pollInterval = setInterval(() => {
      this.checkResult();
    }, 3000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }

  checkResult() {
    this.learningPathService.getPostTestResult(this.submissionId).subscribe({
      next: (res) => {
        this.resultStatus = res.evaluator_status;
        
        if (this.resultStatus === 'completed') {
          this.preScore = res.pre_test_score;
          this.postScore = res.post_test_score;
          this.improvement = res.improvement;
          this.aiFeedback = res.ai_feedback;
          this.chapterTitle = res.chapter_title;
          this.subjectName = res.subject_name;
          this.subjectId = res.subject_id;
          this.learningPathId = res.learning_path_id;
          this.questions = res.questions;
          this.userAnswers = res.user_answers;
          
          this.stopPolling();
        } else if (this.resultStatus === 'failed') {
          this.stopPolling();
        }
      },
      error: () => {
        this.resultStatus = 'error';
        this.stopPolling();
      }
    });
  }

  getCorrectAnswerId(question: any): number | null {
    if (!question || !question.answers) return null;
    const correct = question.answers.find((a: any) => a.is_correct);
    return correct ? correct.id : null;
  }

  getChoiceText(question: any, answerId: any): string {
    if (!question || !question.answers || !answerId) return 'Chưa chọn';
    const ans = question.answers.find((a: any) => a.id === Number(answerId));
    return ans ? ans.answer_text : 'N/A';
  }

  goBack() {
    if (this.learningPathId) {
      this.router.navigate(['/learning-path', this.learningPathId]);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  retryLearningPath() {
    console.log('retryLearningPath called. pathId:', this.learningPathId);
    if (!this.learningPathId) {
      alert('Không tìm thấy mã lộ trình học tập. Vui lòng tải lại trang.');
      return;
    }

    // Tạm thời bỏ confirm để debug hoặc do môi trường browser chặn popup
    console.log('Proceeding with reset...');
    this.learningPathService.resetLearningPath(this.learningPathId).subscribe({
      next: (res) => {
        console.log('Reset successful:', res);
        // Xác định các câu làm sai
        const wrongQuestions = this.questions.filter(q => {
          const userAnsId = this.userAnswers[String(q.id)];
          const correctAnsId = this.getCorrectAnswerId(q);
          return String(userAnsId) !== String(correctAnsId);
        });

        console.log('Wrong questions count:', wrongQuestions.length);

        // Tạo nội dung cho AI Tutor tập trung vào lỗi sai
        let prompt = `Chào AI Gia sư, mình vừa làm bài Đánh giá đầu ra cho chương "${this.chapterTitle}" nhưng kết quả chưa tốt (${this.postScore}%). 
        Mình muốn học lại từ đầu. Hãy giúp mình giải thích và ôn tập kỹ hơn vào các nội dung mình đã làm sai sau đây:\n\n`;

        wrongQuestions.forEach((q, index) => {
          prompt += `Câu hỏi ${index + 1}: ${q.question_text}\n`;
          prompt += `- Mình đã chọn: ${this.getChoiceText(q, this.userAnswers[String(q.id)])}\n`;
          prompt += `- Đáp án đúng: ${this.getChoiceText(q, this.getCorrectAnswerId(q))}\n`;
          if (q.explanation) prompt += `- Giải thích: ${q.explanation}\n`;
          prompt += `\n`;
        });

        prompt += `Hãy đóng vai một gia sư tận tâm, phân tích tại sao mình sai và hướng dẫn mình học lại chương này nhé!`;

        console.log('Prompt generated. Length:', prompt.length);

        // Lưu vào sessionStorage để Chat component đọc
        sessionStorage.setItem('ai_tutor_remedial_context', prompt);
        if (this.subjectId) {
          sessionStorage.setItem('ai_tutor_remedial_subject_id', String(this.subjectId));
        }

        if (!this.subjectId) {
          console.error('Subject ID is missing!');
          this.router.navigate(['/dashboard']);
          return;
        }

        console.log('Navigating to chat with subjectId:', this.subjectId);
        // Điều hướng đến Chat của môn học đó
        this.router.navigate(['/chat', this.subjectId], { queryParams: { mode: 'remedial', pathId: this.learningPathId } });
      },
      error: (err) => {
        console.error('Reset failed:', err);
        alert('Không thể reset lộ trình. Vui lòng thử lại sau.');
      }
    });
  }

  goToDashboard() {
    this.router.navigate(['/dashboard']);
  }

  renderMath(text: string): SafeHtml {
    if (!text) return '';
    try {
      let processed = text;
      // Handle display mode: $$...$$ or \[...\]
      processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (_, f) => katex.renderToString(f, { displayMode: true, throwOnError: false }));
      processed = processed.replace(/\\\[([\s\S]+?)\\\]/g, (_, f) => katex.renderToString(f, { displayMode: true, throwOnError: false }));
      // Handle inline mode: $...$ or \(...\)
      processed = processed.replace(/\$([^$\n]+)\$/g, (_, f) => katex.renderToString(f, { displayMode: false, throwOnError: false }));
      processed = processed.replace(/\\\(([\s\S]+?)\\\)/g, (_, f) => katex.renderToString(f, { displayMode: false, throwOnError: false }));
      return this.sanitizer.bypassSecurityTrustHtml(processed);
    } catch (e) {
      console.error('KaTeX error:', e);
      return text;
    }
  }
}
