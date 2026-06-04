import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { LearningPathService, LearningPath, LearningPathItem } from '../core/services/learning-path.service';

@Component({
  selector: 'app-learning-path',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './learning-path.html',
  styleUrls: ['./learning-path.css']
})
export class LearningPathView implements OnInit {
  pathId!: number;
  learningPath: LearningPath | null = null;
  isLoading = true;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private learningPathService: LearningPathService
  ) { }

  ngOnInit(): void {
    this.pathId = Number(this.route.snapshot.paramMap.get('pathId'));
    this.loadData();
  }

  loadData() {
    this.isLoading = true;
    this.learningPathService.getLearningPathDetail(this.pathId).subscribe({
      next: (res) => {
        this.learningPath = res;

        // Derive common chapter title if missing but all items share one
        if (this.learningPath && !this.learningPath.chapter_title && this.learningPath.items.length > 0) {
          const firstChapter = this.learningPath.items[0].chapter_name;
          const allSame = this.learningPath.items.every(item => item.chapter_name === firstChapter);
          if (allSame && firstChapter) {
            this.learningPath.chapter_title = firstChapter;
          }
        }

        this.isLoading = false;
      },
      error: (err) => {
        console.error(err);
        this.isLoading = false;
      }
    });
  }

  openItem(item: LearningPathItem) {
    if (!item.is_unlocked && item.status !== 'COMPLETED') {
      // Báo là phải hoàn thành bài trước
      alert('Vui lòng hoàn thành bài học trước đó để mở khóa!');
      return;
    }

    if (item.item_type === 'LESSON') {
      this.router.navigate(['/learning-path', this.pathId, 'lesson', item.id]);
    } else {
      this.router.navigate(['/learning-path', this.pathId, 'quiz', item.id]);
    }
  }

  getStrategyLabel(s: string) {
    switch (s) {
      case 'foundation': return 'Nền tảng (Ôn tập toàn diện)';
      case 'standard': return 'Tiêu chuẩn (Khắc phục điểm yếu)';
      case 'advanced': return 'Nâng cao (Phát triển kỹ năng)';
      default: return 'Khác';
    }
  }

  getMilestoneColor(item: LearningPathItem): string {
    // Nếu AI không chẩn đoán hoặc chương này chưa được test
    if (!item.mastery_level) return 'mastery-default';

    switch (item.mastery_level.toUpperCase()) {
      case 'RED': return 'mastery-red';
      case 'YELLOW': return 'mastery-yellow';
      case 'GREEN': return 'mastery-green';
      default: return 'mastery-default';
    }
  }

  startItem(item: LearningPathItem) {
    this.openItem(item);
  }

  goToChapterTest() {
    // Dùng cho luyện tập thêm (không phải vượt ải chính thức)
    if (this.learningPath?.subject && this.learningPath.chapter) {
      this.router.navigate(['/chapter-test', this.learningPath.subject, this.learningPath.chapter]);
    } else if (this.learningPath?.subject) {
      this.router.navigate(['/select-chapter', this.learningPath.subject]);
    }
  }

  // Nút "Vượt ải" — bài kiểm tra đầu ra chính thức (mode=post_test)
  goToPostTest() {
    if (this.learningPath?.subject && this.learningPath.chapter) {
      this.router.navigate(
        ['/chapter-test', this.learningPath.subject, this.learningPath.chapter],
        { queryParams: { mode: 'post_test' } }
      );
    } else if (this.learningPath?.subject) {
      this.router.navigate(['/select-chapter', this.learningPath.subject]);
    }
  }

  // Fallback cho template cũ bị cache
  goToQuizPractice() {
    this.goToChapterTest();
  }
}
