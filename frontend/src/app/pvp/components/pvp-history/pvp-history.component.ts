import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { BattleService, Battle } from '../../services/battle.service';

@Component({
  selector: 'app-pvp-history',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pvp-history.html',
  styleUrl: './pvp-history.css'
})
export class PvpHistoryComponent implements OnInit {
  private router        = inject(Router);
  private battleService = inject(BattleService);

  history: Battle[] = [];
  isLoading = true;

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.battleService.getHistory().subscribe({
      next: (data) => {
        this.history = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  getOutcome(battle: Battle): string {
    if (battle.status !== 'completed' && battle.status !== 'expired') return 'Đang diễn ra';
    if (!battle.winner) return 'Hòa';
    // Check if the current user is the winner
    // We need the current user ID, but we can also infer from username if we had it
    // For now, let's just show who won.
    return `Chiến thắng: ${battle.winner.username}`;
  }

  isDraft(battle: Battle): boolean {
    return battle.status === 'pending' || battle.status === 'in_progress';
  }

  viewResult(battleId: number): void {
    this.router.navigate(['/pvp/result', battleId]);
  }

  goBack(): void {
    this.router.navigate(['/pvp']);
  }
}
