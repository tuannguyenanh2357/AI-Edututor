import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { LearningPathService } from '../core/services/learning-path.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import katex from 'katex';

@Component({
  selector: 'app-pre-test-result',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pre-test-result.html',
  styleUrls: ['./pre-test-result.css']
})
export class PreTestResult implements OnInit, OnDestroy {
  submissionId!: number;
  score: number = 0;
  resultStatus: 'evaluating' | 'completed' | 'error' = 'evaluating';
  learningPathId: number | null = null;
  subjectId: number | null = null;
  subjectName: string = '';
  chapterTitle: string = '';
  aiFeedback: string = '';
  wrongChapters: string[] = [];
  nextChapterId: number | null = null;
  chapterId: number | null = null;
  questions: any[] = [];
  userAnswers: { [key: string]: number } = {};
  bloomAnalysis: any = null;
  get isMastered(): boolean {
    return this.score >= 80;
  }

  get totalQuestions(): number {
    return this.questions.length;
  }

  get correctCount(): number {
    return this.questions.filter(q => this.userAnswers[q.id] === this.getCorrectAnswerId(q)).length;
  }

  get wrongCount(): number {
    return this.totalQuestions - this.correctCount;
  }

  private pollInterval: any;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private learningPathService: LearningPathService,
    private sanitizer: DomSanitizer
  ) { }

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
    // Gọi chapter-test result API (luồng chính)
    this.learningPathService.getChapterTestResult(this.submissionId).subscribe({
      next: (res) => {
        this.score = res.score;
        this.resultStatus = res.evaluator_status;
        this.learningPathId = res.learning_path_id;
        this.aiFeedback = res.ai_feedback || '';
        this.subjectId = res.subject_id || null;
        this.chapterId = res.chapter_id || null;
        this.nextChapterId = res.next_chapter_id || null;
        this.subjectName = res.subject_name || '';
        this.chapterTitle = res.chapter_title || '';
        this.wrongChapters = res.wrong_chapters || [];
        this.questions = res.questions || [];
        this.userAnswers = res.user_answers || {};

        if (this.resultStatus === 'completed' && this.learningPathId) {
          this.bloomAnalysis = res.bloom_analysis;
          this.stopPolling();
        }
      },
      error: () => {
        this.resultStatus = 'error';
        this.stopPolling();
      }
    });
  }

  // Hướng B: đi thẳng vào Roadmap Timeline (/learning-path/:id)
  startLearning() {
    if (this.isMastered && this.nextChapterId) {
      // Nếu đã master -> Chuyển sang test chương tiếp theo
      this.router.navigate(['/chapter-test', this.subjectId, this.nextChapterId]);
    } else if (this.learningPathId) {
      this.router.navigate(['/learning-path', this.learningPathId]);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  goToDashboard() {
    this.router.navigate(['/dashboard']);
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

  getCorrectAnswerId(question: any): number | null {
    if (!question || !question.answers) return null;
    const correct = question.answers.find((a: any) => a.is_correct);
    return correct ? correct.id : null;
  }
}