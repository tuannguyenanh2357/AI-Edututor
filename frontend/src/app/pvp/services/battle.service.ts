import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { getBackendUrl } from '../../core/utils/api-base.util';

export interface BattlePlayer {
  id: number;
  username: string;
  rank: string;
  total_xp: number;
  grade_level: number;
}

export interface BattleResult {
  player: BattlePlayer;
  score: number;
  correct_count: number;
  total_time: number;
}

export interface Battle {
  id: number;
  challenger: BattlePlayer;
  opponent: BattlePlayer;
  grade_level: number;
  question_ids?: number[];
  questions?: any[];
  status: 'pending' | 'in_progress' | 'completed' | 'expired' | 'cancelled';
  winner?: BattlePlayer | null;
  results?: BattleResult[];
  created_at: string;
  expires_at: string;
}

export interface BattleStatus {
  status: string;
  winner: string | null;
  is_draw: boolean;
  result_count: number;
  your_score?: number;
  opponent_score?: number;
  your_correct?: number;
  opponent_correct?: number;
}

@Injectable({ providedIn: 'root' })
export class BattleService {
  private http       = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  private get baseUrl(): string {
    return getBackendUrl(this.platformId) + '/api/battle';
  }

  /** Send a challenge to another player */
  challenge(opponentId: number, gradeLevel: number): Observable<Battle> {
    return this.http.post<Battle>(`${this.baseUrl}/challenge/`, {
      opponent_id: opponentId,
      grade_level: gradeLevel,
    });
  }

  /** Get pending battles (challenges waiting for ME) */
  getPending(): Observable<Battle[]> {
    return this.http.get<Battle[]>(`${this.baseUrl}/pending/`);
  }

  /** Get my battle history */
  getHistory(): Observable<Battle[]> {
    return this.http.get<Battle[]>(`${this.baseUrl}/history/`);
  }

  /** Get full battle detail including questions */
  getBattle(battleId: number): Observable<Battle> {
    return this.http.get<Battle>(`${this.baseUrl}/${battleId}/`);
  }

  /** Accept a pending challenge */
  accept(battleId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/${battleId}/accept/`, {});
  }

  /** Decline a pending challenge */
  decline(battleId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/${battleId}/decline/`, {});
  }

  /** Submit answer log after completing all questions */
  submitAnswers(battleId: number, answerLog: Record<string, { answer: string; time_ms: number }>): Observable<any> {
    return this.http.post(`${this.baseUrl}/${battleId}/submit/`, { answer_log: answerLog });
  }

  /** Poll battle status (called every 3s while waiting for opponent) */
  getStatus(battleId: number): Observable<BattleStatus> {
    return this.http.get<BattleStatus>(`${this.baseUrl}/${battleId}/status/`);
  }
}
