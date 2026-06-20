import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../services/auth.service';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { OtpPopupComponent } from '../../../shared/otp-popup/otp-popup.component';

@Component({
  selector: 'app-forgot-password',
  imports: [FormsModule, RouterLink, CommonModule, ToastModule, OtpPopupComponent],
  providers: [MessageService],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent implements OnDestroy {
  // 'email' = nhập email để nhận OTP, 'reset' = nhập OTP + mật khẩu mới
  step: 'email' | 'reset' = 'email';
  email = '';

  // OTP popup state
  showOtpPopup = false;
  isResendingOtp = false;
  otpError = '';
  otpSuccess = '';
  countdown = 0;
  private countdownTimer: any = null;

  // Reset form
  otp = '';
  newPassword = '';
  confirmPassword = '';
  isSubmittingEmail = false;
  isResetting = false;
  resetError = '';

  constructor(
    private router: Router,
    private authService: AuthService,
    private messageService: MessageService
  ) {}

  onSendOtp() {
    if (!this.email) {
      return;
    }
    this.isSubmittingEmail = true;
    this.resetError = '';
    this.authService.forgotPassword(this.email).subscribe({
      next: (response) => {
        this.isSubmittingEmail = false;
        if (response.EC === 0) {
          this.otp = '';
          this.showOtpPopup = true;
          this.startCountdown();
          this.messageService.add({
            severity: 'info',
            summary: 'Đã gửi mã',
            detail: response.otp_sent === false
              ? 'Không gửi được email. Kiểm tra lại hoặc xem mã ở log server khi test.'
              : `Mã đặt lại mật khẩu đã được gửi đến ${this.email}.`,
            life: 5000
          });
        } else {
          this.resetError = response.EM || 'Không gửi được mã. Vui lòng thử lại.';
        }
      },
      error: (error) => {
        this.isSubmittingEmail = false;
        this.resetError = error.error?.EM || error.message || 'Không gửi được mã. Vui lòng thử lại.';
      }
    });
  }

  // Khi user bấm "Xác nhận" trong popup OTP -> lưu OTP, chuyển sang bước đặt mật khẩu mới.
  // (Backend sẽ xác thực lại OTP khi gọi reset-password.)
  onVerifyOtp(otpValue: string) {
    this.otp = otpValue;
    this.showOtpPopup = false;
    this.stopCountdown();
    this.step = 'reset';
  }

  onResendOtp() {
    if (this.isResendingOtp) {
      return;
    }
    this.isResendingOtp = true;
    this.otpError = '';
    this.authService.forgotPassword(this.email).subscribe({
      next: (response) => {
        this.isResendingOtp = false;
        if (response.EC === 0) {
          this.startCountdown();
          this.messageService.add({
            severity: 'info',
            summary: 'Đã gửi lại mã',
            detail: `Mã đặt lại mới đã được gửi đến ${this.email}.`,
            life: 3000
          });
        } else {
          this.otpError = response.EM || 'Không gửi lại được mã.';
        }
      },
      error: (error) => {
        this.isResendingOtp = false;
        this.otpError = error.error?.EM || error.message || 'Không gửi lại được mã.';
      }
    });
  }

  onResetPassword() {
    this.resetError = '';
    if (this.newPassword.length < 6) {
      this.resetError = 'Mật khẩu mới phải có ít nhất 6 ký tự.';
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      this.resetError = 'Mật khẩu xác nhận không khớp.';
      return;
    }
    if (this.otp.length !== 6) {
      this.resetError = 'Vui lòng nhập đủ 6 chữ số mã đặt lại.';
      return;
    }

    this.isResetting = true;
    this.authService.resetPassword(this.email, this.otp, this.newPassword).subscribe({
      next: (response) => {
        this.isResetting = false;
        if (response.EC === 0) {
          this.messageService.add({
            severity: 'success',
            summary: 'Đặt lại mật khẩu thành công',
            detail: 'Bạn có thể đăng nhập bằng mật khẩu mới. Đang chuyển hướng...',
            life: 2500
          });
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 1500);
        } else {
          this.resetError = response.EM || 'Đặt lại mật khẩu thất bại. Vui lòng thử lại.';
        }
      },
      error: (error) => {
        this.isResetting = false;
        this.resetError = error.error?.EM || error.message || 'Đặt lại mật khẩu thất bại. Vui lòng thử lại.';
      }
    });
  }

  backToEmail() {
    this.step = 'email';
    this.otp = '';
    this.newPassword = '';
    this.confirmPassword = '';
    this.resetError = '';
  }

  startCountdown() {
    this.stopCountdown();
    this.countdown = 300; // 5 phút
    this.countdownTimer = setInterval(() => {
      if (this.countdown > 0) {
        this.countdown--;
      } else {
        this.stopCountdown();
      }
    }, 1000);
  }

  stopCountdown() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
  }

  ngOnDestroy() {
    this.stopCountdown();
  }
}
