import { Component, Input, OnInit, OnDestroy, inject, Output, EventEmitter, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BattleService, Battle } from '../../services/battle.service';
import { BattlePollService } from '../../services/battle-poll.service';
import { Router } from '@angular/router';

const READY_CHECK_DURATION = 15; // seconds

@Component({
  selector: 'app-pvp-ready-check',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pvp-ready-check.html',
  styleUrl: './pvp-ready-check.css'
})
export class PvpReadyCheckComponent implements OnInit, OnDestroy {
  @Input() battle!: Battle;
  @Output() onAction = new EventEmitter<void>();

  private battleService = inject(BattleService);
  private pollService   = inject(BattlePollService);
  private router        = inject(Router);
  private ngZone        = inject(NgZone);

  timeLeft = READY_CHECK_DURATION;
  isProcessing = false;

  private timerRef: any = null;
  private timerDeadline = 0;

  get progressWidth(): number {
    return (this.timeLeft / READY_CHECK_DURATION) * 100;
  }

  ngOnInit() {
    this.startTimer();
  }

  ngOnDestroy() {
    this.stopTimer();
  }

  /**
   * Smooth timer using Date.now() deadline + 100ms polling.
   * Runs outside Angular zone, only re-enters when displayed value changes.
   */
  startTimer() {
    this.stopTimer();
    this.timeLeft = READY_CHECK_DURATION;
    this.timerDeadline = Date.now() + READY_CHECK_DURATION * 1000;

    this.ngZone.runOutsideAngular(() => {
      this.timerRef = setInterval(() => {
        const remaining  = Math.ceil((this.timerDeadline - Date.now()) / 1000);
        const newTimeLeft = Math.max(0, remaining);

        if (newTimeLeft !== this.timeLeft) {
          this.ngZone.run(() => {
            this.timeLeft = newTimeLeft;
            if (this.timeLeft <= 0) {
              this.stopTimer();
              this.decline();
            }
          });
        }
      }, 100);
    });
  }

  stopTimer() {
    if (this.timerRef) {
      clearInterval(this.timerRef);
      this.timerRef = null;
    }
  }

  accept() {
    if (this.isProcessing) return;
    this.isProcessing = true;
    this.stopTimer();

    this.battleService.accept(this.battle.id).subscribe({
      next: () => {
        this.pollService.clearInvite();
        this.pollService.notifyAction(); // Notify others to refresh
        this.router.navigate(['/pvp/battle', this.battle.id]);
        this.onAction.emit();
      },
      error: () => {
        this.decline();
      }
    });
  }

  decline() {
    if (this.isProcessing) return;
    this.isProcessing = true;
    this.stopTimer();

    this.battleService.decline(this.battle.id).subscribe({
      next: () => {
        this.pollService.clearInvite();
        this.pollService.notifyAction(); // Notify others to refresh
        this.onAction.emit();
      },
      error: () => {
        this.pollService.clearInvite();
        this.pollService.notifyAction(); // Notify others to refresh
        this.onAction.emit();
      }
    });
  }
}
