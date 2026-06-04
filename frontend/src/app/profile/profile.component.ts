import { Component, OnInit, inject, PLATFORM_ID, ChangeDetectorRef } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { AuthService } from '../core/services/auth.service';
import { SubjectService, Subject } from '../core/services/subject.service';
import { LearningPathService, LearningPath } from '../core/services/learning-path.service';
import { PvpNotificationBellComponent } from '../core/components/pvp-notification-bell/pvp-notification-bell.component';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PvpNotificationBellComponent],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  // Dữ liệu thật từ API
  userFullName: string = '';
  userUsername: string = '';
  userEmail: string = '';
  userBio: string = '';
  userAvatarUrl: string = '';
  joinDate: string = '';
  userRole: string = 'USER';
  userRank: string = 'Tập Sự';
  gradeLevel: number = 12;

  // Stats thật từ API
  streak: number = 0;
  maxStreak: number = 0;
  totalXp: number = 0;
  gems: number = 0;

  // Modal chỉnh sửa hồ sơ
  showEditModal: boolean = false;
  editForm = {
    full_name: '',
    username: '',
    email: '',
    bio: '',
    avatar_url: '',
    date_of_birth: '',
    grade_level: 12
  };
  isSaving: boolean = false;
  saveMessage: string = '';
  saveError: string = '';

  recentActivity = [
    { type: 'lesson', title: 'Hằng đẳng thức đáng nhớ', subject: 'Toán học', date: '2 giờ trước', icon: 'fas fa-book' },
    { type: 'quiz', title: 'Trắc nghiệm Chương 1: Cơ học', subject: 'Vật lý', date: 'Hôm qua', icon: 'fas fa-clipboard-check' },
    { type: 'achievement', title: 'Đạt Streak 5 ngày liên tiếp!', subject: 'Hệ thống', date: 'Hôm qua', icon: 'fas fa-fire' },
    { type: 'lesson', title: 'Cấu tạo nguyên tử', subject: 'Hóa học', date: '2 ngày trước', icon: 'fas fa-flask' }
  ];

  activeSubjects: { id: number, name: string, grade: number, progress: number }[] = [];
  isLoadingSubjects = true;

  private authService = inject(AuthService);
  private subjectService = inject(SubjectService);
  private learningPathService = inject(LearningPathService);
  private router = inject(Router);
  private platformId = inject(PLATFORM_ID);
  private cdr = inject(ChangeDetectorRef);

  ngOnInit(): void {
    this.loadUserProfile();
    this.loadSubjects();
  }

  loadUserProfile(): void {
    this.authService.getCurrentUser().subscribe({
      next: (user) => {
        this.userFullName  = user.full_name || user.username || 'Người học';
        this.userUsername  = user.username || '';
        this.userEmail     = user.email || '';
        this.userBio       = user.bio || '';
        this.userAvatarUrl = user.avatar_url || '';
        this.userRole      = user.role || 'USER';
        this.userRank      = user.rank || 'Tập Sự';
        this.gradeLevel    = user.grade_level || 12;
        this.streak        = user.current_streak || 0;
        this.maxStreak     = user.max_streak || 0;
        this.totalXp       = user.total_xp || 0;
        this.gems          = user.gems || 0;

        // Lấy ngày tham gia thật từ database
        if (user.created_at) {
          const date = new Date(user.created_at);
          this.joinDate = `Tháng ${date.getMonth() + 1}, ${date.getFullYear()}`;
        } else {
          this.joinDate = 'Tháng 3, 2024';
        }

        if (isPlatformBrowser(this.platformId)) {
          localStorage.setItem('user_username', user.username || '');
          localStorage.setItem('user_name', user.full_name || user.username || '');
        }
      },
      error: () => {
        if (isPlatformBrowser(this.platformId)) {
          this.userFullName = localStorage.getItem('user_name') || 'Người học';
          this.userUsername = localStorage.getItem('user_username') || '';
        } else {
          this.userFullName = 'Người học';
          this.userUsername = '';
        }
      }
    });
  }

  getAvatarUrl(name?: string): string {
    const displayName = name || this.userFullName || this.userUsername || 'User';
    
    // Nếu có avatar_url và nó là một URL hợp lệ, không phải link tìm kiếm rác
    if (this.userAvatarUrl && 
        this.userAvatarUrl.startsWith('http') && 
        this.userAvatarUrl.length < 200 &&
        !this.userAvatarUrl.includes('bing.com') && 
        !this.userAvatarUrl.includes('google.com')) {
      return this.userAvatarUrl;
    }
    
    return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(displayName)}&backgroundColor=5c57d9&chars=1`;
  }

  handleImageError(event: any): void {
    const displayName = this.userFullName || this.userUsername || 'U';
    // Dự phòng sang DiceBear
    event.target.src = `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(displayName)}&backgroundColor=5c57d9&chars=1`;
  }

  loadSubjects(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.learningPathService.getLearningPaths().subscribe({
        next: (paths) => {
          const subjectMap = new Map<number, { name: string, grade: number, totalProgress: number, count: number }>();
          
          if (Array.isArray(paths)) {
            paths.forEach(p => {
              const sid = (p.subject && typeof p.subject === 'object') ? p.subject.id : p.subject;
              const sname = p.subject_name || (p.subject && p.subject.name) || 'Môn học';
              const sgrade = p.grade_level || (p.subject && p.subject.grade_level) || 10;
              const progress = p.progress_percentage || 0;
              
              if (!subjectMap.has(sid)) {
                subjectMap.set(sid, { name: sname, grade: sgrade, totalProgress: progress, count: 1 });
              } else {
                const data = subjectMap.get(sid)!;
                data.totalProgress += progress;
                data.count += 1;
              }
            });
          }
          
          this.activeSubjects = Array.from(subjectMap.entries()).map(([id, data]) => ({
            id: id,
            name: data.name,
            grade: data.grade,
            progress: Math.round(data.totalProgress / data.count)
          }));
          
          this.isLoadingSubjects = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error(err);
          this.isLoadingSubjects = false;
          this.cdr.detectChanges();
        }
      });
    } else {
      this.isLoadingSubjects = false;
    }
  }

  openEditModal(): void {
    this.editForm = {
      full_name:      this.userFullName,
      username:       this.userUsername,
      email:          this.userEmail,
      bio:            this.userBio,
      avatar_url:     this.userAvatarUrl,
      date_of_birth:  '',
      grade_level:    this.gradeLevel
    };
    this.saveMessage = '';
    this.saveError = '';
    this.showEditModal = true;
  }

  closeEditModal(): void {
    this.showEditModal = false;
    this.saveMessage = '';
    this.saveError = '';
  }

  saveProfile(): void {
    this.isSaving = true;
    this.saveMessage = '';
    this.saveError = '';

    this.authService.updateProfile(this.editForm).subscribe({
      next: (user) => {
        // Cập nhật lại giao diện với dữ liệu mới từ server
        this.userFullName  = user.full_name || user.username;
        this.userUsername  = user.username;
        this.userEmail     = user.email;
        this.userBio       = user.bio || '';
        this.userAvatarUrl = user.avatar_url || '';
        this.gradeLevel    = user.grade_level;

        if (isPlatformBrowser(this.platformId)) {
          localStorage.setItem('user_username', user.username);
          localStorage.setItem('user_name', user.full_name || user.username);
        }

        this.isSaving = false;
        this.saveMessage = 'Cập nhật hồ sơ thành công!';
        setTimeout(() => this.closeEditModal(), 1800);
      },
      error: (err) => {
        this.isSaving = false;
        const errData = err.error || {};
        if (errData.username) this.saveError = errData.username;
        else if (errData.email) this.saveError = errData.email;
        else this.saveError = 'Có lỗi xảy ra, vui lòng thử lại.';
      }
    });
  }

  shareProfile(): void {
    let username = this.userUsername;
    if (!username && isPlatformBrowser(this.platformId)) {
       username = localStorage.getItem('user_username') || '';
    }
    const shareUrl = `${window.location.origin}/profile/${username}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      alert(`Đã copy link hồ sơ!\n${shareUrl}`);
    }).catch(() => {
      prompt('Copy link hồ sơ của bạn:', shareUrl);
    });
  }

  logout(): void {
    const refreshToken = isPlatformBrowser(this.platformId) ? (localStorage.getItem('refresh_token') || '') : '';
    this.authService.logoutApi(refreshToken).subscribe({
      next: () => this.clearAndRedirect(),
      error: () => this.clearAndRedirect()
    });
  }

  private clearAndRedirect(): void {
    this.authService.logout();
    if (isPlatformBrowser(this.platformId)) {
      localStorage.clear();
    }
    this.router.navigate(['/login']);
  }

  onQuizSelect(subject?: any): void {
    if (subject?.id) {
      this.router.navigate(['/quiz-practice', subject.id, 0]);
    } else {
      this.router.navigate(['/quiz-practice']);
    }
  }

  getIcon(subjectName: string): string {
    const icons: Record<string, string> = {
      'Toán học': 'fas fa-calculator', 'Vật lý': 'fas fa-atom',
      'Hóa học': 'fas fa-flask', 'Sinh học': 'fas fa-dna',
      'Lịch sử': 'fas fa-landmark', 'Địa lý': 'fas fa-globe-asia',
    };
    return icons[subjectName] || 'fas fa-graduation-cap';
  }

  getIconBg(subjectName: string): string {
    const colors: Record<string, string> = {
      'Toán học': '#ef4444', 'Vật lý': '#3b82f6',
      'Hóa học': '#10b981', 'Sinh học': '#06b6d4',
      'Lịch sử': '#f59e0b', 'Địa lý': '#8b5cf6',
    };
    return colors[subjectName] || '#5C57D9';
  }
}
