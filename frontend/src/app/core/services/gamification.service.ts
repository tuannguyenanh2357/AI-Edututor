import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { getBackendUrl } from '../utils/api-base.util';

export interface DailyQuest {
  id: number;
  title: string;
  question_text: string;
  options: Record<string, string>;
  correct_answer: string;
  explanation: string;
  completed: boolean;
  subject_name?: string;
}

export interface LeaderboardEntry {
  id: number;
  username: string;
  total_xp: number;
  current_streak: number;
  gems: number;
  rank: string;
}

export interface Badge {
  name: string;
  description: string;
  icon_url: string;
}

@Injectable({
  providedIn: 'root'
})
export class GamificationService {
  private platformId = inject(PLATFORM_ID);
  private http = inject(HttpClient);

  private get apiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/gamification`;
  }

  getDailyQuests(): Observable<DailyQuest[]> {
    return this.http.get<DailyQuest[]>(`${this.apiUrl}/daily-quest/`);
  }

  submitQuest(questId: number, answer: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/submit-quest/`, { quest_id: questId, answer });
  }

  getLeaderboard(): Observable<LeaderboardEntry[]> {
    return this.http.get<LeaderboardEntry[]>(`${this.apiUrl}/leaderboard/`);
  }

  getBadges(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/badges/`);
  }

  getAllBadges(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/all-badges/`);
  }

  getRecentBadges(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/recent-badges/`);
  }
}
