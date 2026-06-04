import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { LearningPathService } from '../core/services/learning-path.service';

@Component({
  selector: 'app-post-test',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './post-test.html',
  styleUrls: ['./post-test.css']
})
export class PostTest implements OnInit {
  itemId!: number;
  isCompleting = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private learningPathService: LearningPathService
  ) {}

  ngOnInit(): void {
    this.itemId = Number(this.route.snapshot.paramMap.get('itemId'));
  }

  completeQuiz() {
    this.isCompleting = true;
    this.learningPathService.completeItem(this.itemId).subscribe({
      next: (res) => {
        this.isCompleting = false;
        window.history.back();
      },
      error: () => {
        this.isCompleting = false;
        alert('Lỗi khi đánh dấu hoàn thành bài kiểm tra');
      }
    });
  }
}
