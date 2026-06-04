import { Component, inject } from '@angular/core';
import { CommonModule, AsyncPipe } from '@angular/common';
import { LoadingService } from '../../services/loading.service';

/**
 * LoadingComponent — Thanh loading mỏng cố định ở trên cùng màn hình.
 * Tự động hiện/ẩn dựa trên LoadingService.loading$ observable.
 */
@Component({
  selector: 'app-loading',
  standalone: true,
  imports: [CommonModule, AsyncPipe],
  template: `
    @if (loadingService.loading$ | async) {
      <div class="loading-bar-container" aria-label="Đang tải dữ liệu" role="progressbar">
        <div class="loading-bar"></div>
      </div>
    }
  `,
  styles: [`
    .loading-bar-container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      z-index: 9999;
      overflow: hidden;
    }

    .loading-bar {
      height: 100%;
      width: 40%;
      background: linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa, #6366f1);
      background-size: 200% 100%;
      border-radius: 0 3px 3px 0;
      box-shadow: 0 0 10px rgba(139, 92, 246, 0.8), 0 0 20px rgba(99, 102, 241, 0.4);
      animation: slide 1.6s ease-in-out infinite, shimmer 1.6s linear infinite;
    }

    @keyframes slide {
      0%   { transform: translateX(-100%); width: 40%; }
      50%  { width: 60%; }
      100% { transform: translateX(280%); width: 40%; }
    }

    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `]
})
export class LoadingComponent {
  readonly loadingService = inject(LoadingService);
}
