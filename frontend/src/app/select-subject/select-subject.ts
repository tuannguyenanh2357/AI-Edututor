import { Component, OnInit, PLATFORM_ID, inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { SubjectService } from '../core/services/subject.service';
import { LearningPathService } from '../core/services/learning-path.service';

@Component({
  selector: 'app-select-subject',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './select-subject.html',
  styleUrls: ['./select-subject.css']
})
export class SelectSubject implements OnInit {
  subjects: any[] = [];
  learningPaths: any[] = [];
  isLoading = true;

  constructor(
    private subjectService: SubjectService,
    private learningPathService: LearningPathService,
    private router: Router
  ) {}

  private platformId = inject(PLATFORM_ID);

  ngOnInit(): void {
    this.loadData();
  }

  loadData() {
    this.isLoading = true;
    // Tải danh sách môn học và lộ trình đang có của user
    this.subjectService.getSubjects().subscribe({
      next: (subs) => {
        // Lọc các môn học trùng lặp (giữ lại môn học đầu tiên xuất hiện theo tên và khối)
        const uniqueSubjects: any[] = [];
        const seen = new Set<string>();
        for (const sub of subs) {
           const key = `${sub.name}_${sub.grade_level}`;
           if (!seen.has(key)) {
               seen.add(key);
               uniqueSubjects.push(sub);
           }
        }
        this.subjects = uniqueSubjects;
        
        if (isPlatformBrowser(this.platformId)) {
          this.learningPathService.getLearningPaths().subscribe({
            next: (paths) => {
              this.learningPaths = paths;
              this.isLoading = false;
            },
            error: () => this.isLoading = false
          });
        } else {
          this.isLoading = false;
        }
      },
      error: () => this.isLoading = false
    });
  }

  hasLearningPath(subjectId: number) {
    return this.learningPaths.some(p => p.subject.id === subjectId);
  }

  getLearningPathId(subjectId: number) {
    const path = this.learningPaths.find(p => p.subject.id === subjectId);
    return path ? path.id : null;
  }

  onSelectSubject(subjectId: number) {
    if (this.hasLearningPath(subjectId)) {
      // Đã có lộ trình -> điều hướng đến learning path
      const pathId = this.getLearningPathId(subjectId);
      this.router.navigate(['/learning-path', pathId]);
    } else {
      // Chưa có lộ trình -> chọn Chương để làm test đầu vào
      this.router.navigate(['/select-chapter', subjectId]);
    }
  }
}
