import { Component, OnInit, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterLink } from '@angular/router';
import { SubjectService, Subject } from '../core/services/subject.service';
import { AuthService } from '../core/services/auth.service';
import { Router } from '@angular/router';
import { PvpNotificationBellComponent } from '../core/components/pvp-notification-bell/pvp-notification-bell.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, PvpNotificationBellComponent],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css'],
})
export class Dashboard implements OnInit {
  subjects: Subject[] = [];
  filteredSubjects: Subject[] = [];
  userName: string = 'Người học';
  selectedGrade: number | null = 10;

  streak: number = 0;
  totalPoints: number = 0;

  stats = { easy: 0, medium: 0, hard: 0, total: 0 };

  userAvatarUrl: string = '';
  userUsername: string = '';

  private subjectService = inject(SubjectService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private platformId = inject(PLATFORM_ID);

  ngOnInit(): void {
    this.loadUserProfile();
    this.loadSubjects();
  }

  loadUserProfile(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.authService.getCurrentUser().subscribe({
        next: (user) => {
          this.userName = user.full_name || user.username || 'Người học';
          this.userAvatarUrl = user.avatar_url || '';
          this.userUsername = user.username || '';
          this.streak = user.current_streak || 0;
        },
        error: () => {
          this.userName = localStorage.getItem('user_name') || 'Người học';
        }
      });
    }
  }

  getAvatarUrl(): string {
    const displayName = this.userName || 'User';
    if (this.userAvatarUrl && this.userAvatarUrl.startsWith('http') && this.userAvatarUrl.length < 200) {
      return this.userAvatarUrl;
    }
    return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(displayName)}&backgroundColor=5c57d9&chars=1`;
  }

  handleImageError(event: any): void {
    const displayName = this.userName || 'U';
    event.target.src = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(displayName)}&backgroundColor=5c57d9&chars=1`;
  }

  loadSubjects(): void {
    this.subjectService.getSubjects().subscribe({
      next: (data) => {
        // Lọc các môn học trùng lặp (giữ lại môn học đầu tiên xuất hiện theo tên và khối)
        const uniqueSubjects: any[] = [];
        const seen = new Set<string>();
        for (const sub of data) {
           const key = `${sub.name}_${sub.grade_level}`;
           if (!seen.has(key)) {
               seen.add(key);
               uniqueSubjects.push(sub);
           }
        }
        
        this.subjects = uniqueSubjects;
        // Bỏ qua thuật toán tìm lớp mặc định, thay vào đó hiển thị toàn bộ (null)
        this.filterByGrade(this.selectedGrade);
      },
      error: (err) => {
        console.error('Lỗi tải môn học:', err);
      }
    });
  }

  selectGrade(grade: number | null): void {
    // Toggle: nếu bấm lại lớp đang chọn thì bỏ lọc (hiển thị tất cả)
    if (grade !== null && this.selectedGrade === grade) {
      this.selectedGrade = null;
    } else {
      this.selectedGrade = grade;
    }
    this.filterByGrade(this.selectedGrade);
  }

  filterByGrade(grade: number | null): void {
    if (grade === null) {
      this.filteredSubjects = [...this.subjects];
    } else {
      this.filteredSubjects = this.subjects.filter(s => s.grade_level === grade);
    }
  }

  onSubjectSelect(subject: any): void {
    if (subject && subject.id) {
      this.router.navigate(['/chat', subject.id]);
    }
  }

  onQuizSelect(subject?: any): void {
    if (subject && subject.id) {
      // Gọi từ card môn cụ thể → vào thẳng môn đó
      this.router.navigate(['/quiz-practice', subject.id, 0]);
    } else {
      // Gọi từ menu/navbar → vào trang chọn môn
      this.router.navigate(['/quiz-practice']);
    }
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  getIcon(subjectName: string): string {
    const icons: Record<string, string> = {
      'Toán học': 'fas fa-calculator',
      'Vật lý':   'fas fa-atom',
      'Hóa học':  'fas fa-flask',
      'Sinh học': 'fas fa-dna',
      'Lịch sử':  'fas fa-landmark',
      'Địa lý':   'fas fa-globe-asia',
      'Giáo dục công dân': 'fas fa-balance-scale',
      'Tin học':  'fas fa-laptop-code',
    };
    return icons[subjectName] || 'fas fa-graduation-cap';
  }

  getIconBg(subjectName: string): string {
    const colors: Record<string, string> = {
      'Toán học': 'linear-gradient(135deg, #ef4444, #f87171)',
      'Vật lý':   'linear-gradient(135deg, #3b82f6, #60a5fa)',
      'Hóa học':  'linear-gradient(135deg, #10b981, #34d399)',
      'Sinh học': 'linear-gradient(135deg, #06b6d4, #22d3ee)',
      'Lịch sử':  'linear-gradient(135deg, #f59e0b, #fbbf24)',
      'Địa lý':   'linear-gradient(135deg, #8b5cf6, #a78bfa)',
      'Giáo dục công dân': 'linear-gradient(135deg, #ec4899, #f472b6)',
      'Tin học':  'linear-gradient(135deg, #6366f1, #818cf8)',
    };
    return colors[subjectName] || 'linear-gradient(135deg, #5C57D9, #7c3aed)';
  }

  getOverallProgress(): number {
    if (!this.stats || this.stats.total === 0) return 0;
    const done = (this.stats.easy || 0) + (this.stats.medium || 0) + (this.stats.hard || 0);
    return Math.round((done / this.stats.total) * 100);
  }
}
