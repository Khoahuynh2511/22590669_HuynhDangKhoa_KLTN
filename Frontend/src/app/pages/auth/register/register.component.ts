import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../services/auth.service';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';

@Component({
  selector: 'app-register',
  imports: [FormsModule, RouterLink, CommonModule, ToastModule],
  providers: [MessageService],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss'
})
export class RegisterComponent {
  registerMethod: 'email' | 'phone' = 'email';
  isLoading = false;
  otpSent = false;

  registerForm = {
    fullName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    agreeTerms: false
  };

  passwordValidation = {
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false
  };

  showPasswordRequirements = false;
  passwordError = '';

  phoneRegisterForm = {
    fullName: '',
    phone: '',
    otp: '',
    agreeTerms: false
  };

  constructor(
    private router: Router,
    private authService: AuthService,
    private messageService: MessageService
  ) { }

  onPasswordChange() {
    const p = this.registerForm.password;
    this.passwordValidation.length = p.length >= 8;
    this.passwordValidation.uppercase = /[A-Z]/.test(p);
    this.passwordValidation.lowercase = /[a-z]/.test(p);
    this.passwordValidation.number = /[0-9]/.test(p);
    this.passwordValidation.special = /[@$!%*?&]/.test(p);
    this.showPasswordRequirements = true;
    this.passwordError = '';
  }

  isPasswordValid(): boolean {
    return Object.values(this.passwordValidation).every(v => v);
  }

  onRegister() {
    if (this.registerMethod === 'email') {
      if (!this.isPasswordValid()) {
        this.passwordError = 'Mật khẩu không đáp ứng yêu cầu bảo mật';
        return;
      }

      if (this.registerForm.password !== this.registerForm.confirmPassword) {
        this.passwordError = 'Mật khẩu xác nhận không khớp';
        return;
      }

      if (this.registerForm.fullName && this.registerForm.email && this.registerForm.phone && this.registerForm.password && this.registerForm.agreeTerms) {
        this.isLoading = true;
        this.authService.registerWithEmail({
          fullName: this.registerForm.fullName,
          email: this.registerForm.email,
          phone: this.registerForm.phone,
          password: this.registerForm.password
        }).subscribe({
          next: (response) => {
            console.log('Register success:', response);
            this.isLoading = false;
            if (response.EC === 0) {
              this.messageService.add({
                severity: 'success',
                summary: 'Đăng ký thành công',
                detail: 'Tài khoản của bạn đã được tạo thành công! Đang chuyển hướng đến trang Đăng nhập...',
                life: 2000
              });
              setTimeout(() => {
                this.router.navigate(['/login']);
              }, 2000);
            } else {
              let errMsg = response.EM;
              if (errMsg === 'Email already exists') {
                errMsg = 'Email này đã được đăng ký trong hệ thống. Vui lòng sử dụng email khác.';
              }
              this.messageService.add({
                severity: 'error',
                summary: 'Đăng ký thất bại',
                detail: errMsg || 'Đăng ký không thành công. Vui lòng thử lại.',
                life: 4000
              });
            }
          },
          error: (error) => {
            console.error('Register error:', error);
            this.isLoading = false;
            const errMsg = error.error?.EM || error.message || 'Đã có lỗi xảy ra trong quá trình đăng ký. Vui lòng thử lại sau.';
            this.messageService.add({
              severity: 'error',
              summary: 'Lỗi hệ thống',
              detail: errMsg,
              life: 4000
            });
          }
        });
      }
    } else {
      if (this.phoneRegisterForm.fullName && this.phoneRegisterForm.phone && this.phoneRegisterForm.otp && this.phoneRegisterForm.agreeTerms) {
        this.isLoading = true;
        this.authService.registerWithPhone(
          this.phoneRegisterForm.phone,
          this.phoneRegisterForm.otp,
          { fullName: this.phoneRegisterForm.fullName }
        ).subscribe({
          next: (response) => {
            console.log('Phone register success:', response);
            this.isLoading = false;
            if (response.success || response.EC === 0) {
              this.messageService.add({
                severity: 'success',
                summary: 'Đăng ký thành công',
                detail: 'Tài khoản của bạn đã được tạo thành công! Đang chuyển hướng đến trang Đăng nhập...',
                life: 2000
              });
              setTimeout(() => {
                this.router.navigate(['/login']);
              }, 2000);
            } else {
              this.messageService.add({
                severity: 'error',
                summary: 'Đăng ký thất bại',
                detail: response.EM || 'Đăng ký không thành công. Vui lòng thử lại.',
                life: 4000
              });
            }
          },
          error: (error) => {
            console.error('Phone register error:', error);
            this.isLoading = false;
            const errMsg = error.error?.EM || error.message || 'Đăng ký bằng số điện thoại thất bại. Vui lòng thử lại.';
            this.messageService.add({
              severity: 'error',
              summary: 'Lỗi',
              detail: errMsg,
              life: 4000
            });
          }
        });
      }
    }
  }

  sendOTP() {
    if (!this.phoneRegisterForm.phone) {
      return;
    }

    this.isLoading = true;
    this.authService.sendOTP(this.phoneRegisterForm.phone).subscribe({
      next: (response) => {
        console.log('OTP sent:', response);
        this.otpSent = true;
        this.isLoading = false;
        this.messageService.add({
          severity: 'info',
          summary: 'Đã gửi mã OTP',
          detail: 'Mã OTP đã được gửi đến số điện thoại của bạn.',
          life: 3000
        });
      },
      error: (error) => {
        console.error('OTP send error:', error);
        this.isLoading = false;
        this.messageService.add({
          severity: 'error',
          summary: 'Không gửi được OTP',
          detail: error.message || 'Gửi mã OTP thất bại. Vui lòng thử lại.',
          life: 3000
        });
      }
    });
  }

  resendOTP() {
    this.otpSent = false;
    this.phoneRegisterForm.otp = '';
    this.sendOTP();
  }


}
