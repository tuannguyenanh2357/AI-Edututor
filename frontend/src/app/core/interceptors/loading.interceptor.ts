import { inject } from '@angular/core';
import { HttpInterceptorFn } from '@angular/common/http';
import { finalize } from 'rxjs/operators';
import { LoadingService } from '../services/loading.service';

/**
 * loadingInterceptor — Functional HTTP Interceptor (Angular 18+ style).
 * Tự động kích hoạt LoadingService khi có bất kỳ HTTP request nào,
 * và tắt sau khi response hoàn thành (kể cả khi có lỗi).
 */
export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService = inject(LoadingService);

  // Bỏ qua các request SSE streaming của AI Service để tránh loading bar bị kẹt
  const skipLoading = req.url.includes('/api/v1/chat') || req.url.includes('/api/v1/stream');

  if (!skipLoading) {
    loadingService.show();
  }

  return next(req).pipe(
    finalize(() => {
      if (!skipLoading) {
        loadingService.hide();
      }
    })
  );
};
