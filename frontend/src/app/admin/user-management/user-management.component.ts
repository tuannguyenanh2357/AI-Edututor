import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { getBackendUrl } from '../../core/utils/api-base.util';

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  avatarColor: string;
  grade?: number;
  currentSubject?: string;
  currentChapter?: string;
  totalSessions?: number;
  isLocked?: boolean;
  createdAt?: string;
  lastLogin?: string;
  progress?: number;
}

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './user-management.component.html',
  styleUrls: ['./user-management.component.css']
})
export class UserManagementComponent implements OnInit {

  users: User[] = [];
  filteredUsers: User[] = [];
  searchQuery = '';
  filterGrade = '';
  filterSubject = '';
  filterStatus = '';
  isLoading = true;

  showDetail = false;
  selectedUser: User | null = null;

  // Stats
  totalCount = 0;
  newThisWeek = 0;
  activeToday = 0;
  activePct = 0;
  lockedCount = 0;

  // Pagination
  currentPage = 1;
  pageSize = 10;
  Math = Math;

  private get apiBase(): string {
    return `${getBackendUrl(this.platformId)}/api/admin`;
  }
  private readonly colors = ['#1565c0','#00897b','#f57c00','#7b1fa2','#c62828','#0288d1'];

  constructor(
    private http: HttpClient,
    @Inject(PLATFORM_ID) private platformId: Object
  ) { }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.loadData();
    }
  }

  private getHeaders(): HttpHeaders {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token) {
        return new HttpHeaders({
          'Authorization': `Bearer ${token}`
        });
      }
    }
    return new HttpHeaders();
  }

  loadData(): void {
    this.isLoading = true;
    const headers = this.getHeaders();

    this.http.get<any>(`${this.apiBase}/stats/`, { headers }).subscribe({
      next: (data) => {
        this.totalCount = data.totalUsers || 0;
        this.newThisWeek = data.newUsersThisWeek || 0;
        this.activeToday = data.activeToday || 0;
        this.lockedCount = data.lockedAccounts || 0;
        this.activePct = this.totalCount > 0 ? Math.round((this.activeToday / this.totalCount) * 100) : 0;
      },
      error: (err) => { if (err.status === 401) this.handleUnauthorized(); }
    });

    this.http.get<any>(`${this.apiBase}/users/`, { headers }).subscribe({
      next: (data) => {
        const colorList = this.colors;
        this.users = (data.users || []).map((u: any, i: number) => ({
          ...u,
          avatarColor: colorList[i % colorList.length]
        }));
        this.applyFilter();
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 401) this.handleUnauthorized();
      }
    });
  }

  applyFilter(): void {
    let result = [...this.users];
    const q = this.searchQuery.toLowerCase().trim();
    if (q) result = result.filter(u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    if (this.filterGrade) result = result.filter(u => String(u.grade) === this.filterGrade);
    if (this.filterSubject) result = result.filter(u => u.currentSubject?.includes(this.filterSubject));
    if (this.filterStatus === 'active') result = result.filter(u => !u.isLocked);
    if (this.filterStatus === 'locked') result = result.filter(u => u.isLocked);
    this.filteredUsers = result;
    this.currentPage = 1;
  }

  get pagedUsers(): User[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.filteredUsers.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.ceil(this.filteredUsers.length / this.pageSize);
  }

  get pageNumbers(): number[] {
    return Array.from({ length: this.totalPages }, (_, i) => i + 1);
  }

  goPage(p: number): void { this.currentPage = p; }
  prevPage(): void { if (this.currentPage > 1) this.currentPage--; }
  nextPage(): void { if (this.currentPage < this.totalPages) this.currentPage++; }

  openDetail(user: User): void {
    this.selectedUser = user;
    this.showDetail = true;
  }

  closeDetail(): void {
    this.showDetail = false;
    this.selectedUser = null;
  }

  toggleLock(): void {
    if (!this.selectedUser) return;
    const headers = this.getHeaders();
    this.http.post<any>(`${this.apiBase}/users/${this.selectedUser.id}/toggle-status/`, {}, { headers }).subscribe({
      next: () => {
        const user = this.users.find(u => u.id === this.selectedUser!.id);
        if (user) {
          user.isLocked = !user.isLocked;
          this.lockedCount = this.users.filter(u => u.isLocked).length;
        }
        if (this.selectedUser) this.selectedUser.isLocked = !this.selectedUser.isLocked;
      },
      error: (err) => console.error('Lỗi toggle lock:', err)
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