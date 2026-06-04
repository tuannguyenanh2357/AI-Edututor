import { Injectable, inject } from '@angular/core';
import { Observable, timer, switchMap, takeWhile, share, BehaviorSubject, map, of } from 'rxjs';
import { BattleService, BattleStatus, Battle } from './battle.service';
import { Router } from '@angular/router';

const POLL_INTERVAL_MS = 2000; // Poll every 2 seconds for faster invite detection

@Injectable({ providedIn: 'root' })
export class BattlePollService {
  private battleService = inject(BattleService);
  private router = inject(Router);

  // Global state for a "Match Ready" overlay
  private inviteSubject = new BehaviorSubject<Battle | null>(null);
  public invite$ = this.inviteSubject.asObservable();

  // Signal for components to refresh their state (e.g. pending list in lobby)
  private refreshSubject = new BehaviorSubject<void>(undefined);
  public refreshSignal$ = this.refreshSubject.asObservable();

  notifyAction() {
    this.refreshSubject.next();
  }

  /**
   * Poll for ANY pending invitations for the current user.
   * Useful in the Lobby or globally.
   */
  pollForInvites(): Observable<Battle[]> {
    return timer(0, POLL_INTERVAL_MS).pipe(
      switchMap(() => {
        // Pause background polling if actively playing a battle to avoid UI stuttering
        if (this.router.url.includes('/pvp/battle/')) {
          return of([]);
        }
        return this.battleService.getPending();
      }),
      map(battles => {
        const currentInvite = this.inviteSubject.value;
        if (battles.length > 0) {
          // Only update if it's a new battle (different ID)
          if (!currentInvite || currentInvite.id !== battles[0].id) {
            this.inviteSubject.next(battles[0]);
          }
        } else if (battles.length === 0 && currentInvite) {
          this.inviteSubject.next(null);
        }
        return battles;
      }),
      share()
    );
  }

  /** Clear the current invitation locally (e.g. after Accept/Decline) */
  clearInvite() {
    this.inviteSubject.next(null);
  }

  /**
   * Poll battle status every 3 seconds until it's completed/expired.
   * Auto-stops when status is no longer 'pending' or 'in_progress'.
   *
   * Usage:
   *   this.pollService.pollUntilDone(battleId).subscribe(status => { ... })
   */
  pollUntilDone(battleId: number): Observable<BattleStatus> {
    return timer(0, POLL_INTERVAL_MS).pipe(
      switchMap(() => this.battleService.getStatus(battleId)),
      takeWhile(
        (status) => status.status === 'pending' || status.status === 'in_progress',
        true // emit the last value (completed/expired) before stopping
      ),
      share() // Share one interval among multiple subscribers
    );
  }
}
