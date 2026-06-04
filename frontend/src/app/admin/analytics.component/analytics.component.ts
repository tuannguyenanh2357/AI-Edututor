import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { getBackendUrl } from '../../core/utils/api-base.util';

interface SubjectStat {
  name: string;
  short: string;
  color: string;
  sessions: number;
  chatCount: number;
  quizCount: number;
  trend: number;
  students: number;
}

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.css']
})
export class AnalyticsComponent implements OnInit {

  subjectStats: SubjectStat[] = [];
  isLoading = true;

  gradeDistribution = [
    { label: 'Lớp 10', count: 0 },
    { label: 'Lớp 11', count: 0 },
    { label: 'Lớp 12', count: 0 },
  ];

  private get apiBase(): string {
    return `${getBackendUrl(this.platformId)}/api/admin`;
  }

  constructor(
    private http: HttpClient,
    @Inject(PLATFORM_ID) private platformId: Object
  ) { }

  get totalStudents(): number {
    return this.gradeDistribution.reduce((s, g) => s + g.count, 0);
  }

  get topSubject(): SubjectStat | null {
    if (!this.subjectStats.length) return null;
    return this.subjectStats.reduce((prev, curr) => curr.students > prev.students ? curr : prev);
  }

  getPercent(students: number): string {
    if (this.totalStudents === 0) return '0';
    return ((students / Math.max(this.totalStudents, 1)) * 100).toFixed(0);
  }

  getBarHeight(students: number): number {
    const max = Math.max(...this.subjectStats.map(s => s.students), 1);
    return (students / max) * 100;
  }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.loadData();
    }
  }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders();
  }

  loadData(): void {
    this.isLoading = true;
    const headers = this.getHeaders();

    this.http.get<any>(`${this.apiBase}/analytics/`, { headers }).subscribe({
      next: (data) => {
        this.subjectStats = data.subjects || [];
        if (data.gradeDistribution) this.gradeDistribution = data.gradeDistribution;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Lỗi analytics:', err);
        this.isLoading = false;
        if (err.status === 401) this.handleUnauthorized();
      }
    });

    this.http.get<any>(`${this.apiBase}/stats/`, { headers }).subscribe({
      next: (data) => {
        if (data.gradeDistribution) this.gradeDistribution = data.gradeDistribution;
      },
      error: () => {}
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