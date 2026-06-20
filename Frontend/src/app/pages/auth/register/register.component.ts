import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../services/auth.service';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { OtpPopupComponent } from '../../../shared/otp-popup/otp-popup.component';

@Component({
  selector: 'app-register',
  imports: [FormsModule, RouterLink, CommonModule, ToastModule, OtpPopupComponent],
  providers: [MessageService],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss'
})
export class RegisterComponent implements OnDestroy {
  registerMethod: 'email' | 'phone' = 'email';
  isLoading = false;
  otpSent = false;

  // === Email verification OTP flow ===
  showRegisterOTP = false;
  registeredEmail = '';
  isVerifyingRegisterOTP = false;
  isResendingRegisterOTP = false;
  registerOtpError = '';
  registerOtpSuccess = '';
  registerCountdown = 0;
  private registerCountdownTimer: any = null;

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
              if (response.awaiting_verification) {
                // Luồng mới: mở popup OTP xác thực email
                this.registeredEmail = this.registerForm.email;
                this.showRegisterOTP = true;
                this.registerOtpError = '';
                this.registerOtpSuccess = '';
                this.startRegisterCountdown();
                this.messageService.add({
                  severity: 'info',
                  summary: 'Xác thực email',
                  detail: response.otp_sent === false
                    ? 'Không gửi được email. Vui lòng bấm "Gửi lại OTP" hoặc kiểm tra lại (mã cũng được in ở log server khi test).'
                    : `Mã xác thực đã được gửi đến ${this.registeredEmail}. Vui lòng nhập để kích hoạt tài khoản.`,
                  life: 5000
                });
              } else {
                // Fallback: backend không yêu cầu verify → chuyển login
                this.messageService.add({
                  severity: 'success',
                  summary: 'Đăng ký thành công',
                  detail: 'Tài khoản của bạn đã được tạo thành công! Đang chuyển hướng đến trang Đăng nhập...',
                  life: 2000
                });
                setTimeout(() => {
                  this.router.navigate(['/login']);
                }, 2000);
              }
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

  // ===== Email verification OTP handlers =====

  onVerifyRegisterOTP(otp: string) {
    if (!this.registeredEmail) {
      return;
    }
    this.isVerifyingRegisterOTP = true;
    this.registerOtpError = '';
    this.registerOtpSuccess = '';
    this.authService.verifyEmail(this.registeredEmail, otp).subscribe({
      next: (response) => {
        this.isVerifyingRegisterOTP = false;
        if (response.EC === 0) {
          this.stopRegisterCountdown();
          this.registerOtpSuccess = response.EM || 'Xác thực thành công!';
          this.messageService.add({
            severity: 'success',
            summary: 'Xác thực thành công',
            detail: 'Tài khoản đã được kích hoạt. Đang chuyển đến trang đăng nhập...',
            life: 2500
          });
          setTimeout(() => {
            this.showRegisterOTP = false;
            this.router.navigate(['/login']);
          }, 1500);
        } else {
          this.registerOtpError = response.EM || 'Mã xác thực không đúng hoặc đã hết hạn.';
        }
      },
      error: (error) => {
        this.isVerifyingRegisterOTP = false;
        this.registerOtpError = error.error?.EM || error.message || 'Xác thực thất bại. Vui lòng thử lại.';
      }
    });
  }

  onResendRegisterOTP() {
    if (!this.registeredEmail || this.isResendingRegisterOTP) {
      return;
    }
    this.isResendingRegisterOTP = true;
    this.registerOtpError = '';
    this.authService.resendVerification(this.registeredEmail).subscribe({
      next: (response) => {
        this.isResendingRegisterOTP = false;
        if (response.EC === 0) {
          this.startRegisterCountdown();
          this.messageService.add({
            severity: 'info',
            summary: 'Đã gửi lại mã',
            detail: `Mã xác thực mới đã được gửi đến ${this.registeredEmail}.`,
            life: 3000
          });
        } else {
          this.registerOtpError = response.EM || 'Không gửi lại được mã. Vui lòng thử lại.';
        }
      },
      error: (error) => {
        this.isResendingRegisterOTP = false;
        this.registerOtpError = error.error?.EM || error.message || 'Không gửi lại được mã. Vui lòng thử lại.';
      }
    });
  }

  startRegisterCountdown() {
    this.stopRegisterCountdown();
    this.registerCountdown = 300; // 5 phút (OTP_EXPIRE_MINUTES)
    this.registerCountdownTimer = setInterval(() => {
      if (this.registerCountdown > 0) {
        this.registerCountdown--;
      } else {
        this.stopRegisterCountdown();
      }
    }, 1000);
  }

  stopRegisterCountdown() {
    if (this.registerCountdownTimer) {
      clearInterval(this.registerCountdownTimer);
      this.registerCountdownTimer = null;
    }
  }

  ngOnDestroy() {
    this.stopRegisterCountdown();
  }


}
