import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../core/services/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.css'
})
export class ResetPasswordComponent implements OnInit {
  password: string = '';
  confirmPassword: string = '';
  uidb64: string = '';
  token: string = '';
  isLoading: boolean = false;
  message: string = '';
  error: string = '';

  constructor(
    private route: ActivatedRoute,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.uidb64 = params['uid'];
      this.token = params['token'];
      
      if (!this.uidb64 || !this.token) {
        this.error = 'Đường dẫn không hợp lệ hoặc thiếu thông tin xác thực.';
      }
    });
  }

  onSubmit() {
    if (this.password !== this.confirmPassword) {
      this.error = 'Mật khẩu xác nhận không khớp.';
      return;
    }

    this.isLoading = true;
    this.message = '';
    this.error = '';

    const data = {
      uidb64: this.uidb64,
      token: this.token,
      password: this.password
    };

    this.authService.resetPassword(data).subscribe({
      next: (res) => {
        this.message = 'Đặt lại mật khẩu thành công! Bạn sẽ được chuyển về trang đăng nhập trong giây lát.';
        this.isLoading = false;
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 3000);
      },
      error: (err) => {
        this.error = err.error?.error || 'Có lỗi xảy ra, vui lòng thử lại sau.';
        this.isLoading = false;
      }
    });
  }
}
