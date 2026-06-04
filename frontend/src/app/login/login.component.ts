import { Component, OnInit, AfterViewInit, OnDestroy, PLATFORM_ID, Inject, NgZone } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../core/services/auth.service';
import { Router } from '@angular/router';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit, AfterViewInit, OnDestroy {
  loginForm!: FormGroup;
  isPasswordVisible: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';

  private renderRetryTimer: any = null;
  private maxRetries = 10;
  private retryCount = 0;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private ngZone: NgZone,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  ngAfterViewInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    // Chạy ngoài Angular zone để tránh xung đột change detection với Google SDK
    this.ngZone.runOutsideAngular(() => {
      // Delay nhỏ để đảm bảo DOM và hydration hoàn tất
      this.renderRetryTimer = setTimeout(() => this.tryRenderGoogleButton(), 300);
    });
  }

  ngOnDestroy(): void {
    if (this.renderRetryTimer) {
      clearTimeout(this.renderRetryTimer);
    }
  }

  private tryRenderGoogleButton(): void {
    const win = window as any;

    if (win.google?.accounts?.id) {
      try {
        win.google.accounts.id.initialize({
          client_id: '563742313603-h39despeq6pa6ir4adhnq2iet46a5erf.apps.googleusercontent.com',
          callback: (response: any) => {
            // Chạy lại trong Angular zone để trigger change detection
            this.ngZone.run(() => {
              this.loginWithGoogleToken(response.credential);
            });
          }
        });

        const btn = document.getElementById('google-btn');
        if (btn) {
          // Xóa nội dung cũ (nếu Angular hydration đã render thừa)
          btn.innerHTML = '';
          win.google.accounts.id.renderButton(btn, {
            theme: 'outline',
            size: 'large',
            width: 280
          });
        }
      } catch (err) {
        console.warn('Google renderButton error:', err);
      }
    } else if (this.retryCount < this.maxRetries) {
      // SDK chưa load xong, thử lại
      this.retryCount++;
      this.renderRetryTimer = setTimeout(() => this.tryRenderGoogleButton(), 500);
    } else {
      console.warn('Google SDK không tải được sau nhiều lần thử.');
    }
  }

  togglePasswordVisibility(): void {
    this.isPasswordVisible = !this.isPasswordVisible;
  }

  onSubmit(): void {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';

      this.authService.login(this.loginForm.value).subscribe({
        next: (response) => {
          this.isLoading = false;
          if (response.access_token && response.user && response.user.role) {
            this.authService.saveUserData(response.access_token, response.user.role, response.user.id);
          }
          if (this.authService.isAdmin()) {
            this.router.navigate(['/admin/dashboard']);
          } else {
            this.router.navigate(['/dashboard']);
          }
        },
        error: (error) => {
          console.error('Lỗi từ Server:', error);
          this.isLoading = false;
          this.errorMessage =
            error.error?.error || 'Tài khoản hoặc mật khẩu không chính xác. Vui lòng thử lại!';
        }
      });
    } else {
      this.loginForm.markAllAsTouched();
    }
  }

  loginWithGoogleToken(idToken: string): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.authService.loginWithGoogle(idToken).subscribe({
      next: (response) => {
        this.isLoading = false;
        if (response.access_token && response.user && response.user.role) {
          this.authService.saveUserData(response.access_token, response.user.role, response.user.id);
        }
        if (this.authService.isAdmin()) {
          this.router.navigate(['/admin/dashboard']);
        } else {
          this.router.navigate(['/dashboard']);
        }
      },
      error: (error) => {
        console.error('Lỗi từ Server:', error);
        this.isLoading = false;
        this.errorMessage =
          error.error?.error || 'Đăng nhập Google thất bại. Vui lòng thử lại!';
      }
    });
  }
}