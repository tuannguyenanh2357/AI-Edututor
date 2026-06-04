import {
  Component, OnInit, OnDestroy, inject, NgZone,
  HostListener, ElementRef, ViewChild, AfterViewInit, ChangeDetectorRef, PLATFORM_ID
} from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { BattleService, Battle } from '../../../pvp/services/battle.service';
import { BattlePollService } from '../../../pvp/services/battle-poll.service';

const READY_CHECK_DURATION = 20; // seconds — match backend PENDING_EXPIRY_SECONDS

@Component({
  selector: 'app-pvp-notification-bell',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pvp-notification-bell.component.html',
  styleUrl: './pvp-notification-bell.component.css',
})
export class PvpNotificationBellComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('bellBtn') bellBtnRef!: ElementRef<HTMLButtonElement>;

  private pollService   = inject(BattlePollService);
  private battleService = inject(BattleService);
  private router        = inject(Router);
  private ngZone        = inject(NgZone);
  private cdr           = inject(ChangeDetectorRef);
  private platformId    = inject(PLATFORM_ID);

  invite: Battle | null = null;
  isOpen       = false;
  isProcessing = false;
  timeLeft     = READY_CHECK_DURATION;
  progressWidth = 100;

  // Position of dropdown (fixed, computed from bell button rect)
  dropdownTop  = 0;
  dropdownRight = 0;

  private inviteSub?: Subscription;
  private pollSub?: Subscription;
  private timerRef: any = null;
  private timerDeadline = 0;

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      // Guarantee polling is active while the bell is present (only in browser)
      this.pollSub = this.pollService.pollForInvites().subscribe();
    }

    this.inviteSub = this.pollService.invite$.subscribe((battle: Battle | null) => {
      const hadInvite = !!this.invite;
      this.invite = battle;

      if (battle && !hadInvite) {
        // New invite: auto-open dropdown + start timer
        this.isProcessing = false;
        this.isOpen = true;
        this.startTimer();
        // Defer position calc so DOM has rendered the bell button
        setTimeout(() => this.updateDropdownPosition(), 0);
      } else if (!battle) {
        this.isOpen = false;
        this.stopTimer();
      }
    });
  }

  ngAfterViewInit(): void {}

  ngOnDestroy(): void {
    this.stopTimer();
    this.inviteSub?.unsubscribe();
    this.pollSub?.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest('app-pvp-notification-bell')) {
      this.isOpen = false;
    }
  }

  @HostListener('window:scroll')
  @HostListener('window:resize')
  onViewChange() {
    if (this.isOpen) this.updateDropdownPosition();
  }

  updateDropdownPosition(): void {
    if (!this.bellBtnRef) return;
    const rect = this.bellBtnRef.nativeElement.getBoundingClientRect();
    this.dropdownTop   = rect.bottom + 10;
    this.dropdownRight = window.innerWidth - rect.right;
  }

  togglePanel(e: MouseEvent): void {
    e.stopPropagation();
    this.isOpen = !this.isOpen;
    if (this.isOpen) this.updateDropdownPosition();
  }

  private startTimer(): void {
    this.stopTimer();
    if (!this.invite) return;

    // Use created_at as anchor to sync with challenger
    const startTime = this.invite.created_at ? new Date(this.invite.created_at).getTime() : Date.now();
    this.timerDeadline = startTime + (READY_CHECK_DURATION * 1000);
    this.progressWidth  = 100;

    this.ngZone.runOutsideAngular(() => {
      this.timerRef = setInterval(() => {
        const remaining   = Math.ceil((this.timerDeadline - Date.now()) / 1000);
        const newTimeLeft = Math.max(0, remaining);
        const newProgress = (newTimeLeft / READY_CHECK_DURATION) * 100;

        if (newTimeLeft !== this.timeLeft || Math.abs(newProgress - this.progressWidth) > 1) {
          this.ngZone.run(() => {
            this.timeLeft      = newTimeLeft;
            this.progressWidth = newProgress;
            this.cdr.detectChanges(); // Vital for smooth bar and text
            if (this.timeLeft <= 0 && !this.isProcessing) {
              this.autoDecline();
            }
          });
        }
      }, 100);
    });
  }

  private stopTimer(): void {
    if (this.timerRef) {
      clearInterval(this.timerRef);
      this.timerRef = null;
    }
  }

  private autoDecline(): void {
    if (!this.invite || this.isProcessing) return;
    this.isProcessing = true;
    this.stopTimer();
    this.battleService.decline(this.invite.id).subscribe({
      next:  () => { this.pollService.clearInvite(); this.pollService.notifyAction(); },
      error: () => { this.pollService.clearInvite(); this.pollService.notifyAction(); }
    });
  }

  accept(): void {
    if (!this.invite || this.isProcessing) return;
    this.isProcessing = true;
    this.cdr.detectChanges();
    this.stopTimer();
    const battleId = this.invite.id;

    this.battleService.accept(battleId).subscribe({
      next: () => {
        this.pollService.clearInvite();
        this.pollService.notifyAction();
        this.isOpen = false;
        this.ngZone.run(() => {
          this.router.navigate(['/pvp/battle', battleId]);
        });
      },
      error: () => {
        this.isProcessing = false;
        this.cdr.detectChanges();
        this.startTimer();
      }
    });
  }

  decline(): void {
    if (!this.invite || this.isProcessing) return;
    this.isProcessing = true;
    this.stopTimer();

    this.battleService.decline(this.invite.id).subscribe({
      next:  () => { this.pollService.clearInvite(); this.pollService.notifyAction(); this.isOpen = false; },
      error: () => { this.pollService.clearInvite(); this.pollService.notifyAction(); this.isOpen = false; }
    });
  }

  getAvatarUrl(username: string): string {
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(username)}&background=6366f1&color=fff&size=64`;
  }
}
