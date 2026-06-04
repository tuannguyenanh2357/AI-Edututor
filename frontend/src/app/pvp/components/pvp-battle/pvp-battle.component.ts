import { Component, OnInit, OnDestroy, inject, NgZone, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription, timer } from 'rxjs';
import { BattleService, Battle } from '../../services/battle.service';
import { BattlePollService } from '../../services/battle-poll.service';
import { MarkdownRenderPipe } from '../../../core/pipes/markdown-render.pipe';

const TIME_LIMIT = 15; // seconds per question

@Component({
  selector: 'app-pvp-battle',
  standalone: true,
  imports: [CommonModule, MarkdownRenderPipe],
  templateUrl: './pvp-battle.html',
  styleUrl: './pvp-battle.css'
})
export class PvpBattleComponent implements OnInit, OnDestroy {
  private route         = inject(ActivatedRoute);
  private router        = inject(Router);
  private battleService = inject(BattleService);
  private pollService   = inject(BattlePollService);
  private ngZone        = inject(NgZone);
  private cdr           = inject(ChangeDetectorRef);

  battle:          Battle | null = null;
  questions:       any[]  = [];
  currentIndex     = 0;
  currentQuestion: any    = null;
  optionKeys:      string[] = [];
  progress         = 0;
  selectedAnswer:  string = '';
  timeLeft         = TIME_LIMIT;
  isSubmitting     = false;
  isTransitioning  = false;
  correctKey: string | null = null;
  phase: 'loading' | 'playing' | 'waiting' | 'done' = 'loading';

  answerLog: Record<string, { answer: string; time_ms: number }> = {};
  questionStartTime = 0;

  // Timer internals
  private timerSub?: Subscription;
  private deadline = 0;

  private pollSub?: Subscription;
  private battleId!: number;

  ngOnInit(): void {
    this.battleId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadBattle();
  }

  loadBattle(): void {
    this.battleService.getBattle(this.battleId).subscribe({
      next: (battle) => {
        this.battle    = battle;
        this.questions = battle.questions || [];
        if (this.questions.length > 0) {
          this.phase = 'playing';
          this.startQuestion();
        } else {
          this.router.navigate(['/pvp']);
        }
      },
      error: () => this.router.navigate(['/pvp'])
    });
  }

  startQuestion(): void {
    if (this.currentIndex >= this.questions.length) {
      this.submitAll();
      return;
    }
    
    try {
      this.selectedAnswer  = '';
      this.correctKey      = null;
      this.isTransitioning = false;
      this.timeLeft        = TIME_LIMIT;
      this.currentQuestion = this.questions[this.currentIndex];
      this.optionKeys      = this.currentQuestion && this.currentQuestion.options ? Object.keys(this.currentQuestion.options) : [];
      this.progress        = (this.currentIndex / this.questions.length) * 100;
      this.questionStartTime = Date.now();
      this.cdr.markForCheck();
      this.cdr.detectChanges();
      this.startTimer();
    } catch (e) {
      console.error('Error starting question:', e);
      // Auto skip question if it crashes
      this.nextQuestion();
    }
  }

  /**
   * Smooth, reliable timer using RxJS. Updates every 1 second.
   */
  private startTimer(): void {
    this.stopTimer();
    this.timeLeft = TIME_LIMIT;
    this.deadline = Date.now() + (TIME_LIMIT * 1000);
    
    this.ngZone.runOutsideAngular(() => {
      // Poll faster (every 100ms) for high precision, but only trigger Angular CD when the second changes
      this.timerSub = timer(0, 100).subscribe(() => {
        const now = Date.now();
        const remaining = Math.max(0, Math.ceil((this.deadline - now) / 1000));
        
        if (remaining !== this.timeLeft && !this.isTransitioning) {
          this.ngZone.run(() => {
            this.timeLeft = remaining;
            this.cdr.markForCheck();
            this.cdr.detectChanges();
            
            if (this.timeLeft <= 0) {
              this.handleTimeout();
            }
          });
        }
      });
    });
  }

  private stopTimer(): void {
    if (this.timerSub) {
      this.timerSub.unsubscribe();
      this.timerSub = undefined;
    }
  }

  private handleTimeout(): void {
    if (this.isTransitioning) return;
    this.isTransitioning = true;
    this.stopTimer();
    this.recordAnswer('');
    this.cdr.detectChanges();
    
    timer(500).subscribe(() => {
      this.ngZone.run(() => {
        this.nextQuestion();
        this.cdr.detectChanges();
      });
    });
  }

  selectAnswer(option: string): void {
    this.ngZone.run(() => {
      if (this.selectedAnswer || this.isTransitioning) return;

      this.stopTimer();
      this.isTransitioning = true;
      this.selectedAnswer  = option;
      this.correctKey      = this.currentQuestion?.correct_answer || null;

      const timeMs = Date.now() - this.questionStartTime;
      this.recordAnswer(option, timeMs);
      this.cdr.detectChanges();

      // Use a standard setTimeout for the most primitive, reliable delay
      setTimeout(() => {
        this.ngZone.run(() => {
          try {
            this.nextQuestion();
          } catch (err) {
            console.error('Error in nextQuestion transition:', err);
            this.isTransitioning = false;
            this.currentIndex++;
            this.startQuestion();
          }
          this.cdr.detectChanges();
        });
      }, 600);
    });
  }

  private recordAnswer(answer: string, timeMs?: number): void {
    const quest = this.questions[this.currentIndex];
    if (!quest) return;
    this.answerLog[String(quest.id)] = {
      answer:  answer,
      time_ms: timeMs ?? (TIME_LIMIT * 1000),
    };
  }

  private nextQuestion(): void {
    this.currentIndex++;
    this.cdr.markForCheck();
    this.cdr.detectChanges();
    this.startQuestion();
  }

  private submitAll(): void {
    this.isSubmitting = true;
    this.phase = 'waiting';

    this.battleService.submitAnswers(this.battleId, this.answerLog).subscribe({
      next: (res) => {
        if (res.status === 'completed') {
          this.router.navigate(['/pvp/result', this.battleId]);
        } else {
          this.startPolling();
        }
      },
      error: (err) => {
        this.isSubmitting = false;
        this.phase = 'playing';
        console.error('Submit error:', err.error?.error);
      }
    });
  }

  private startPolling(): void {
    this.pollSub = this.pollService.pollUntilDone(this.battleId).subscribe({
      next: (status) => {
        if (status.status === 'completed' || status.status === 'expired') {
          this.router.navigate(['/pvp/result', this.battleId]);
        }
      },
      error: () => {}
    });
  }

  ngOnDestroy(): void {
    this.stopTimer();
    this.pollSub?.unsubscribe();
  }
}
