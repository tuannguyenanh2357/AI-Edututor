import { Component, OnInit, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterLink } from '@angular/router';
import { GamificationService, LeaderboardEntry } from '../core/services/gamification.service';
import { ToastrService } from 'ngx-toastr';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-explore',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './explore.component.html',
  styleUrl: './explore.component.css'
})
export class ExploreComponent implements OnInit {
  private platformId = inject(PLATFORM_ID);
  private gamificationService = inject(GamificationService);
  private toastr = inject(ToastrService);

  leaderboard: LeaderboardEntry[] = [];
  badges: any[] = [];
  
  selectedBadge: any = null;
  showBadgeModal: boolean = false;
  loading: boolean = false;

  floor(n: number): number {
    return Math.floor(n);
  }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.loadData();
    }
  }

  loadData(): void {
    this.loading = true;
    
    const allBadges$ = this.gamificationService.getAllBadges();
    const userBadges$ = this.gamificationService.getBadges();

    forkJoin([allBadges$, userBadges$]).subscribe({
      next: ([all, userEarned]) => {
        // Merge badges: map general badge info with user's earned status
        const earnedMap = new Map(userEarned.map((ub: any) => [ub.badge.id, ub.earned_at]));
        
        this.badges = all.map((b, i) => ({
          ...b,
          earned: earnedMap.has(b.id),
          earned_date: earnedMap.get(b.id)
        }));
        
        this.loading = false;
        console.log("Museum data synchronized successfully.");
      },
      error: (err: any) => {
        console.error("Error loading museum data:", err);
        this.loading = false;
      }
    });

    // Background check for very recent achievements to show notifications
    this.gamificationService.getRecentBadges().subscribe({
      next: (newBadges) => {
        newBadges.forEach(ub => {
          this.toastr.success(
            `Chúc mừng! Bạn đã mở khóa: ${ub.badge.name}`,
            'Thành tựu mới!',
            { positionClass: 'toast-bottom-right', progressBar: true }
          );
        });
      }
    });
  }

  get earnedBadgesCount(): number {
    return this.badges.filter(b => b.earned).length;
  }

  openBadgeDetails(badge: any): void {
    this.selectedBadge = badge;
    this.showBadgeModal = true;
  }

  closeModal(): void {
    this.showBadgeModal = false;
    this.selectedBadge = null;
  }
}
