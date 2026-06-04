import { Component, OnInit, OnDestroy, inject, PLATFORM_ID, NgZone, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { BattleService, Battle } from '../../services/battle.service';
import { BattlePollService } from '../../services/battle-poll.service';
import { getBackendUrl } from '../../../core/utils/api-base.util';
import { PvpNotificationBellComponent } from '../../../core/components/pvp-notification-bell/pvp-notification-bell.component';
import { Subscription } from 'rxjs';

const CHALLENGE_TIMEOUT_SEC = 20;

@Component({
  selector: 'app-pvp-lobby',
  standalone: true,
  imports: [CommonModule, PvpNotificationBellComponent],
  templateUrl: './pvp-lobby.html',
  styleUrl: './pvp-lobby.css'
})
export class PvpLobbyComponent implements OnInit, OnDestroy {
  private router        = inject(Router);
  private http          = inject(HttpClient);
  private battleService = inject(BattleService);
  private platformId    = inject(PLATFORM_ID);
  private pollService   = inject(BattlePollService);
  private ngZone        = inject(NgZone);
  private cdr           = inject(ChangeDetectorRef);

  players:        any[]    = [];
  pendingBattles: Battle[] = [];
  myGrade         = 12;
  myUserId        = 0;   // Current user's ID — used to hide self-challenge button
  isLoading       = false;
  challengeMsg:   string | null = null;
  countdownSec    = 0; // Live countdown shown to challenger

  // Ready Check State
  waitingForBattleId: number | null = null;
  private countdownRef: any = null;
  private refreshSub?: Subscription;
  private pollSub?: Subscription;

  ngOnInit(): void {
    this.loadCurrentUser();
    this.loadPendingBattles();
    
    // Listen for refresh signal (e.g. from global ready check)
    this.refreshSub = this.pollService.refreshSignal$.subscribe(() => {
      this.loadPendingBattles();
    });
  }

  ngOnDestroy(): void {
    this.stopCountdown();
    this.refreshSub?.unsubscribe();
    this.pollSub?.unsubscribe();
  }

  private stopCountdown(): void {
    if (this.countdownRef) {
      clearInterval(this.countdownRef);
      this.countdownRef = null;
    }
  }

  /**
   * Smooth countdown using Date.now() deadline reference.
   * Checks every 100ms, only triggers Angular CD when value changes.
   */
  private startCountdownWithDeadline(deadline: number): void {
    this.stopCountdown();
    this.ngZone.runOutsideAngular(() => {
      this.countdownRef = setInterval(() => {
        const remaining = Math.ceil((deadline - Date.now()) / 1000);
        const newVal = Math.max(0, remaining);
        
        if (newVal !== this.countdownSec) {
          this.ngZone.run(() => {
            this.countdownSec = newVal;
            this.cdr.detectChanges();
            if (this.countdownSec <= 0) {
              this.stopCountdown();
              if (this.isLoading) {
                this.isLoading = false;
                this.waitingForBattleId = null;
                this.challengeMsg = 'Đối thủ không phản hồi. Vui lòng thử lại sau.';
                this.cdr.detectChanges();
              }
            }
          });
        }
      }, 100);
    });
  }

  loadCurrentUser(): void {
    const url = getBackendUrl(this.platformId) + '/api/users/me';
    this.http.get<any>(url).subscribe({
      next: (user) => {
        this.myGrade  = user.grade_level || 12;
        this.myUserId = user.id || 0;
        this.loadLeaderboard();
      }
    });
  }

  loadLeaderboard(): void {
    const url = getBackendUrl(this.platformId) + `/api/gamification/leaderboard/?grade=${this.myGrade}`;
    this.http.get<any[]>(url).subscribe({
      next: (data) => this.players = data,
      error: () => {}
    });
  }

  loadPendingBattles(): void {
    this.battleService.getPending().subscribe({
      next: (data) => this.pendingBattles = data,
      error: () => {}
    });
  }

  isSelf(player: any): boolean {
    return player.id === this.myUserId;
  }

  challenge(player: any): void {
    // Block self-challenge at frontend before even hitting API
    if (this.isLoading || this.isSelf(player)) return;

    this.isLoading    = true;
    this.challengeMsg = null;
    this.cdr.detectChanges();

    this.battleService.challenge(player.id, this.myGrade).subscribe({
      next: (battle) => {
        this.waitingForBattleId = battle.id;
        this.challengeMsg = `Đã gửi! Đang chờ ${player.username} chấp nhận...`;
        
        // Use created_at as anchor to sync with opponent
        const startTime = battle.created_at ? new Date(battle.created_at).getTime() : Date.now();
        const syncDeadline = startTime + (CHALLENGE_TIMEOUT_SEC * 1000);
        this.startCountdownWithDeadline(syncDeadline);

        this.pollSub = this.pollService.pollUntilDone(battle.id).subscribe({
          next: (status) => {
            if (status.status === 'in_progress') {
              this.stopCountdown();
              this.pollSub?.unsubscribe();
              this.ngZone.run(() => {
                this.router.navigate(['/pvp/battle', battle.id]);
              });
            } else if (status.status === 'cancelled' || status.status === 'expired') {
              this.stopCountdown();
              this.isLoading = false;
              this.challengeMsg = 'Đối thủ đã từ chối hoặc hết hạn.';
              this.waitingForBattleId = null;
              this.cdr.detectChanges();
            }
          }
        });
      },
      error: (err) => {
        this.isLoading    = false;
        const serverError = err.error?.error || err.error?.detail || (typeof err.error === 'string' ? err.error : null);
        this.challengeMsg = serverError || 'Không thể gửi lời thách đấu. Vui lòng thử lại.';
        this.cdr.detectChanges();
        console.error('Challenge Error:', err);
      }
    });
  }

  acceptChallenge(battle: Battle): void {
    this.battleService.accept(battle.id).subscribe({
      next: () => {
        this.ngZone.run(() => {
          this.router.navigate(['/pvp/battle', battle.id]);
        });
      },
      error: (err) => console.error('Accept error:', err.error?.error)
    });
  }
  
  cancelChallenge(): void {
    if (!this.waitingForBattleId) return;
    
    this.battleService.decline(this.waitingForBattleId).subscribe({
      next: () => {
        this.stopCountdown();
        this.isLoading = false;
        this.waitingForBattleId = null;
        this.challengeMsg = 'Bạn đã hủy lời thách đấu.';
        this.pollSub?.unsubscribe();
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Cancel error:', err);
      }
    });
  }

  viewHistory(): void {
    this.router.navigate(['/pvp/history']);
  }

  goBack(): void {
    this.router.navigate(['/arena']);
  }
}
