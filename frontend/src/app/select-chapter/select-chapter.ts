import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SubjectService, Subject, Chapter } from '../core/services/subject.service';

@Component({
  selector: 'app-select-chapter',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './select-chapter.html',
  styleUrls: ['./select-chapter.css']
})
export class SelectChapter implements OnInit {
  subject: Subject | null = null;
  chapters: Chapter[] = [];
  isLoading = true;
  subjectId!: number;
  selectedChapterId: number | null = null;

  // Icon map theo thứ tự chương
  chapterIcons = ['📐', '🔬', '⚗️', '🧬', '🗺️', '📊', '🎯', '💡', '🔭', '📚'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private subjectService: SubjectService
  ) {}

  ngOnInit(): void {
    this.subjectId = Number(this.route.snapshot.paramMap.get('subjectId'));
    this.loadData();
  }

  loadData() {
    this.isLoading = true;
    this.subjectService.getSubjectDetail(this.subjectId).subscribe({
      next: (sub) => {
        this.subject = sub;
        this.subjectService.getChapters(this.subjectId).subscribe({
          next: (chapters) => {
            this.chapters = chapters.sort((a, b) => a.order_num - b.order_num);
            this.isLoading = false;
          },
          error: () => this.isLoading = false
        });
      },
      error: () => this.isLoading = false
    });
  }

  getChapterIcon(index: number): string {
    return this.chapterIcons[index % this.chapterIcons.length];
  }

  onSelectChapter(chapter: Chapter) {
    this.selectedChapterId = chapter.id;
    setTimeout(() => {
      if (chapter.has_learning_path && chapter.learning_path_id) {
        // Đã test -> Chuyển thẳng đến lộ trình
        this.router.navigate(['/learning-path', chapter.learning_path_id]);
      } else {
        // Chưa test -> Chuyển đến trang làm bài test
        this.router.navigate(['/chapter-test', this.subjectId, chapter.id]);
      }
    }, 300);
  }

  onStartPostTest(chapter: Chapter, event: Event) {
    event.stopPropagation(); // Ngăn click bọn lan lên card
    this.router.navigate(['/chapter-test', this.subjectId, chapter.id], {
      queryParams: { mode: 'post_test' }
    });
  }

  goBack() {
    this.router.navigate(['/select-subject']);
  }
}
