import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformServer } from '@angular/common';

/**
 * Trả về base URL của Backend API.
 * - Nếu chạy trên Server (SSR trong Docker): dùng tên service Docker "backend"
 * - Nếu chạy trên Trình duyệt: dùng localhost
 */
export function getBackendUrl(platformId: Object): string {
  if (isPlatformServer(platformId)) {
    // Trong Docker, frontend container kết nối backend qua tên service
    return 'http://backend:8000';
  }
  return 'http://localhost:8000';
}

/**
 * Trả về base URL của AI Service.
 * - Nếu chạy trên Server (SSR): dùng tên service Docker "ai_service"
 * - Nếu chạy trên Trình duyệt: dùng localhost
 */
export function getAiServiceUrl(platformId: Object): string {
  if (isPlatformServer(platformId)) {
    return 'http://ai_service:8001';
  }
  return 'http://localhost:8001';
}
