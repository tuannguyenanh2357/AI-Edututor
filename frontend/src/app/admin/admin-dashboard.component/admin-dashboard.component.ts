import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { getBackendUrl } from '../../core/utils/api-base.util';

interface SubjectStat {
  name: string;
  color: string;
  percentage: number;
}

interface RecentRegistration {
  name: string;
  email: string;
  avatarColor: string;
  timeAgo: string;
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css']
})
export class AdminDashboardComponent implements OnInit {

  today = new Date();

  stats = {
    totalUsers: 0,
    newUsersThisWeek: 0,
    onlineUsers: 0,
    questionsToday: 0,
    questionsTrend: 0,
    questionsTrendUp: true,
    quizzesToday: 0,
    quizzesTrend: 0,
    quizzesTrendUp: true,
  };

  subjectStats: SubjectStat[] = [];
  recentRegistrations: RecentRegistration[] = [];
  isLoading = true;
  showNotifPopup = false;

  toggleNotifPopup(event: Event): void {
    event.stopPropagation();
    this.showNotifPopup = !this.showNotifPopup;
  }

  closeNotifPopup(): void {
    this.showNotifPopup = false;
  }

  private get apiBase(): string {
    return `${getBackendUrl(this.platformId)}/api/admin`;
  }

  constructor(
    private http: HttpClient,
    @Inject(PLATFORM_ID) private platformId: Object
  ) { }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.loadDashboardData();
    }
  }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders(); // Để interceptor tự thêm Bearer token
  }

  loadDashboardData(): void {
    const headers = this.getHeaders();

    this.http.get<any>(`${this.apiBase}/stats/`, { headers }).subscribe({
      next: (data) => {
        this.stats = {
          totalUsers: data.totalUsers,
          newUsersThisWeek: data.newUsersThisWeek,
          onlineUsers: 0,
          questionsToday: data.questionsToday,
          questionsTrend: data.questionsTrend,
          questionsTrendUp: data.questionsTrendUp,
          quizzesToday: data.quizzesToday,
          quizzesTrend: data.quizzesTrend,
          quizzesTrendUp: data.quizzesTrendUp,
        };
      },
      error: (err) => {
        console.error('Lỗi stats:', err);
        if (err.status === 401) this.handleUnauthorized();
      }
    });

    this.http.get<any>(`${this.apiBase}/subjects/`, { headers }).subscribe({
      next: (data) => {
        this.subjectStats = data.subjects;
      },
      error: (err) => {
        console.error('Lỗi subjects:', err);
        if (err.status === 401) this.handleUnauthorized();
      }
    });

    this.http.get<any>(`${this.apiBase}/registrations/`, { headers }).subscribe({
      next: (data) => {
        this.recentRegistrations = data.registrations;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Lỗi registrations:', err);
        this.isLoading = false;
        if (err.status === 401) this.handleUnauthorized();
      }
    });
  }

  private handleUnauthorized(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_role');
      window.location.href = '/login';
    }
  }
}