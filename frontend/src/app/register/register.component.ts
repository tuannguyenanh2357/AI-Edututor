import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { AuthService } from '../core/services/auth.service';
import { Router, RouterLink } from '@angular/router'; // Import RouterLink để chuyển trang

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent implements OnInit {
  registerForm!: FormGroup;
  isLoading: boolean = false;
  errorMessage: string = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Thêm trường fullName và confirmPassword
    this.registerForm = this.fb.group({
      fullName: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', Validators.required]
    }, { validators: this.passwordMatchValidator }); // Gọi hàm check khớp mật khẩu
  }

  // Hàm kiểm tra mật khẩu và xác nhận mật khẩu có giống nhau không
  passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
    const password = control.get('password')?.value;
    const confirmPassword = control.get('confirmPassword')?.value;
    
    // Nếu có nhập mà không khớp thì báo lỗi
    if (password && confirmPassword && password !== confirmPassword) {
      control.get('confirmPassword')?.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    return null;
  }

  onSubmit(): void {
    if (this.registerForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';

      // Thường thì Backend không cần nhận trường confirmPassword, ta tách nó ra
      const { confirmPassword, ...dataToSend } = this.registerForm.value;

      this.authService.register(dataToSend).subscribe({
        next: (res) => {
          this.isLoading = false;
          alert('Đăng ký thành công! Vui lòng đăng nhập.');
          this.router.navigate(['/login']); // Đăng ký xong thì đẩy về trang Login
        },
        error: (err) => {
          this.isLoading = false;
          this.errorMessage = err.error?.message || 'Đăng ký thất bại. Email có thể đã tồn tại!';
        }
      });
    } else {
      this.registerForm.markAllAsTouched();
    }
  }
}