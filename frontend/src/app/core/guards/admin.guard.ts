import { inject, PLATFORM_ID } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { isPlatformServer } from '@angular/common';

export const adminGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);

  // Cho phép server render để tránh redirect sai trong quá trình Hydration
  if (isPlatformServer(platformId)) {
    return true;
  }

  if (authService.isAdmin()) {
    return true;
  }
  
  // Nếu là client và không phải admin, điều hướng về dashboard thường
  router.navigate(['/dashboard']);
  return false;
};
