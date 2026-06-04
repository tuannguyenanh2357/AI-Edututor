import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  features = [
    {
      icon: 'brain',
      title: 'Gia sư AI 24/7',
      description: 'Giải đáp mọi bài toán tức thì bằng công nghệ AI tiên tiến, luôn sẵn sàng hỗ trợ bạn.'
    },
    {
      icon: 'quiz',
      title: 'Sinh Quiz Tự Động',
      description: 'Tự động tạo bài tập trắc nghiệm từ Sách Giáo Khoa, kiểm tra kiến thức hiệu quả.'
    },
    {
      icon: 'chart',
      title: 'Chấm điểm & Nhận xét',
      description: 'Đánh giá chi tiết điểm mạnh và điểm yếu, giúp bạn cải thiện đúng chỗ cần thiết.'
    },
    {
      icon: 'path',
      title: 'Lộ trình cá nhân hóa',
      description: 'Đề xuất bài học phù hợp theo năng lực thực tế của từng học sinh.'
    }
  ];

  isMenuOpen = false;

  toggleMenu(): void {
    this.isMenuOpen = !this.isMenuOpen;
  }
}
