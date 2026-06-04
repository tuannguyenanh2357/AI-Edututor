import { Component, OnInit, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { getBackendUrl } from '../core/utils/api-base.util';
import { MarkdownRenderPipe } from '../core/pipes/markdown-render.pipe';

interface Toast {
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

interface ConfirmDialog {
  message: string;
  item: any;
}

@Component({
  selector: 'app-arena',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, MarkdownRenderPipe],
  templateUrl: './arena.html',
  styleUrls: ['./arena.css']
})
export class ArenaComponent implements OnInit {
  private platformId = inject(PLATFORM_ID);
  private http = inject(HttpClient);
  
  userStats = {
    username: 'Học sinh',
    streak: 0,
    gems: 0,
    xp: 0,
    rank: 'Tập Sự',
    grade_level: 12,
    avatar_url: ''
  };

  activeGrade = 12;
  shopItems: any[] = [];
  inventoryItems: any[] = [];
  leaderboard: any[] = [];
  
  dailyQuests: any[] = [];
  towerFloors: any[] = [];
  
  showTowerModal = false;
  showQuestModal = false;
  showInventoryModal = false;
  showPvpModal = false;
  
  currentQuest: any = null;
  selectedAnswer: string = '';
  bonusMessage: string | null = null;
  questResult: any = null;
  lastFailedQuestId: number | null = null;
  isSubmittingAnswer = false; // [NEW] Prevent double clicks

  // Toast system
  toasts: Toast[] = [];

  // Confirm dialog
  confirmDialog: ConfirmDialog | null = null;

  private get API_URL() {
    return getBackendUrl(this.platformId) + '/api/gamification';
  }

  get streakPet() {
    const s = this.userStats.streak;
    if (s >= 21) {
      return { icon: 'fa-fire-alt', class: 'stage-epic', name: 'Phượng Hoàng Lửa' };
    } else if (s >= 8) {
      return { icon: 'fa-dragon', class: 'stage-warrior', name: 'Rồng Chiến' };
    } else if (s >= 3) {
      return { icon: 'fa-dragon', class: 'stage-baby', name: 'Rồng Con' };
    } else {
      return { icon: 'fa-egg', class: 'stage-egg', name: 'Trứng Thần Long' };
    }
  }

  showToast(message: string, type: Toast['type'] = 'info', duration = 3500): void {
    const toast: Toast = { message, type };
    this.toasts.push(toast);
    setTimeout(() => {
      this.toasts = this.toasts.filter(t => t !== toast);
    }, duration);
  }

  getItemIcon(name: string): string {
    const n = name.toLowerCase();
    if (n.includes('băng nén') || n.includes('freeze')) return 'fa-snowflake';
    if (n.includes('nhân đôi xp') || n.includes('x2 xp')) return 'fa-bolt';
    if (n.includes('khung avatar')) return 'fa-award';
    if (n.includes('siêu cấp')) return 'fa-magic';
    if (n.includes('thông minh') || n.includes('hint')) return 'fa-brain';
    if (n.includes('tăng tốc xp') || n.includes('boost')) return 'fa-rocket';
    return 'fa-box';
  }

  ngOnInit(): void {
    this.loadUserData();
    this.loadShopItems();
    this.loadInventory();
  }

  loadUserData(): void {
    const url = getBackendUrl(this.platformId) + '/api/users/me';
    this.http.get<any>(url).subscribe({
      next: (data) => {
        this.userStats = {
          username: data.username || 'Học sinh',
          streak: data.current_streak || 0,
          gems: data.gems || 0,
          xp: data.total_xp || 0,
          rank: data.rank || 'Tập Sự',
          grade_level: data.grade_level || 12,
          avatar_url: data.avatar_url || ''
        };
        this.activeGrade = data.grade_level || 12;
        this.loadLeaderboard();
      },
      error: (err) => console.warn('Could not load user data:', err)
    });
  }

  setGrade(grade: number): void {
    this.activeGrade = grade;
    this.userStats.grade_level = grade;
    
    const url = getBackendUrl(this.platformId) + '/api/users/me';
    this.http.patch(url, { grade_level: grade }).subscribe({
      next: () => {
        this.loadLeaderboard();
        if (this.showTowerModal) {
          this.openDailyQuest();
        }
      },
      error: (err) => {
        console.warn('Grade sync failed:', err);
        this.loadLeaderboard();
      }
    });
  }

  loadShopItems(): void {
    this.http.get<any[]>(this.API_URL + '/store/').subscribe({
      next: (data) => this.shopItems = data,
      error: (err) => console.warn('Could not load shop:', err)
    });
  }

  loadInventory(): void {
    this.http.get<any[]>(this.API_URL + '/inventory/').subscribe({
      next: (data) => this.inventoryItems = data,
      error: (err) => console.warn('Could not load inventory:', err)
    });
  }

  loadLeaderboard(): void {
    const url = `${this.API_URL}/leaderboard/?grade=${this.activeGrade}`;
    this.http.get<any[]>(url).subscribe({
      next: (data) => this.leaderboard = data,
      error: (err) => console.warn('Could not load leaderboard:', err)
    });
  }

  openDailyQuest(): void {
    const url = `${this.API_URL}/daily-quest/?grade=${this.activeGrade}`;
    this.http.get<any[]>(url).subscribe({
      next: (quests) => {
        this.dailyQuests = quests;
        this.buildTowerFloors(quests);
        this.showTowerModal = true;
      },
      error: (err) => {
        const msg = err.error?.error || `Hiện chưa có thử thách tháp nào cho khối lớp ${this.activeGrade}.`;
        this.showToast(msg, 'warning');
      }
    });
  }

  buildTowerFloors(allQuests: any[]): void {
    this.towerFloors = [];
    for (let i = 1; i <= 10; i++) {
      const floorQuests = allQuests.filter(q => q.floor_level === i);
      const isCompleted = floorQuests.length > 0 && floorQuests.some(q => q.completed);
      
      let isUnlocked = (i === 1);
      if (i > 1) {
        const prevFloor = this.towerFloors[i - 2];
        isUnlocked = prevFloor && prevFloor.completed;
      }

      this.towerFloors.push({
        level: i,
        quests: floorQuests,
        completed: isCompleted,
        unlocked: isUnlocked,
        label: i === 10 ? 'ĐỈNH THÁP' : `Tầng ${i}`
      });
    }
  }

  startFloor(floor: any): void {
    if (!floor.unlocked) {
      this.showToast('Hãy hoàn thành tầng trước để mở khóa!', 'warning');
      return;
    }
    
    const availableQuests = floor.quests.filter((q: any) => !q.completed);
    
    if (availableQuests.length > 0) {
      let candidateQuests = availableQuests;
      if (availableQuests.length > 1 && this.lastFailedQuestId) {
        candidateQuests = availableQuests.filter((q: any) => q.id !== this.lastFailedQuestId);
      }

      const randIndex = Math.floor(Math.random() * candidateQuests.length);
      this.currentQuest = candidateQuests[randIndex];
      this.showQuestModal = true;
      this.selectedAnswer = '';
      this.bonusMessage = null;
    } else if (floor.completed) {
      this.showToast('Tầng này đã hoàn thành! Hãy chinh phục tầng tiếp theo.', 'success');
    } else {
      this.showToast('Hiện chưa có câu hỏi cho tầng này.', 'info');
    }
  }

  submitAnswer(): void {
    if (!this.selectedAnswer || !this.currentQuest || this.isSubmittingAnswer) return;

    this.isSubmittingAnswer = true;
    this.http.post<any>(this.API_URL + '/submit-quest/', {
      quest_id: this.currentQuest.id,
      answer: this.selectedAnswer
    }).subscribe({
      next: (res) => {
        this.isSubmittingAnswer = false;
        if (res.status === 'correct') {
          this.questResult = {
            success: true,
            xp: res.xp_earned,
            gems: res.gems_earned,
            floor: res.floor,
            msg: res.bonus_message || 'Bạn đã chinh phục tầng tháp thành công!'
          };
          
          this.userStats.xp = res.current_xp;
          this.userStats.gems = res.current_gems;
          this.userStats.streak = res.streak;
          this.userStats.rank = res.rank;

          this.lastFailedQuestId = null;
          this.refreshTower();
          this.loadInventory();
        } else {
          this.questResult = {
            success: false,
            msg: 'Rất tiếc, câu trả lời chưa chính xác. Đừng nản lòng, hãy thử lại nhé!'
          };
          this.lastFailedQuestId = this.currentQuest.id;
        }
      },
      error: (err) => {
        this.isSubmittingAnswer = false;
        this.showToast(err.error?.error || 'Có lỗi xảy ra.', 'error');
      }
    });
  }

  refreshTower(): void {
    const url = `${this.API_URL}/daily-quest/?grade=${this.activeGrade}`;
    this.http.get<any[]>(url).subscribe({
      next: (quests) => {
        this.dailyQuests = quests;
        this.buildTowerFloors(quests);
      }
    });
  }

  purchaseItem(item: any): void {
    if (this.userStats.gems < item.price_gems) {
      this.showToast('Bạn không đủ Gem để mua vật phẩm này.', 'error');
      return;
    }
    this.confirmDialog = {
      message: `Bạn có muốn đổi ${item.price_gems} Gem lấy "${item.name}" không?`,
      item
    };
  }

  onConfirmYes(): void {
    if (!this.confirmDialog) return;
    const item = this.confirmDialog.item;
    this.confirmDialog = null;

    this.http.post<any>(this.API_URL + '/purchase/', { item_id: item.id }).subscribe({
      next: (res) => {
        this.showToast(res.message || 'Mua thành công!', 'success');
        this.loadUserData();
        this.loadInventory();
      },
      error: (err) => this.showToast(err.error?.error || 'Có lỗi xảy ra.', 'error')
    });
  }

  openShop(): void {
    document.querySelector('.shop-preview')?.scrollIntoView({ behavior: 'smooth' });
  }

  closeQuest(): void {
    this.showQuestModal = false;
    this.questResult = null;
    this.selectedAnswer = '';
  }
}

