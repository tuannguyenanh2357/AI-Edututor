import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { BattleService, BattleStatus } from '../../services/battle.service';

@Component({
  selector: 'app-pvp-result',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pvp-result.html',
  styleUrl: './pvp-result.css'
})
export class PvpResultComponent implements OnInit {
  private route         = inject(ActivatedRoute);
  private router        = inject(Router);
  private battleService = inject(BattleService);

  result:    BattleStatus | null = null;
  isLoading  = true;
  battleId!: number;

  ngOnInit(): void {
    this.battleId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadResult();
  }

  loadResult(): void {
    this.battleService.getStatus(this.battleId).subscribe({
      next: (data) => {
        this.result    = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.router.navigate(['/pvp']);
      }
    });
  }

  get outcomeLabel(): string {
    if (!this.result) return '';
    if (this.result.is_draw) return 'HÒA';
    // We determine win/lose by comparing scores
    const myScore  = this.result.your_score    ?? 0;
    const oppScore = this.result.opponent_score ?? 0;
    return myScore >= oppScore ? 'CHIẾN THẮNG 🏆' : 'THẤT BẠI 💀';
  }

  get isWin(): boolean {
    if (!this.result || this.result.is_draw) return false;
    return (this.result.your_score ?? 0) >= (this.result.opponent_score ?? 0);
  }

  goLobby():   void { this.router.navigate(['/pvp']); }
  goArena():   void { this.router.navigate(['/arena']); }
  rematch():   void { this.router.navigate(['/pvp']); }
}
