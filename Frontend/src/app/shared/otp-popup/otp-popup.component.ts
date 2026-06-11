import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-otp-popup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './otp-popup.component.html',
  styleUrl: './otp-popup.component.scss'
})
export class OtpPopupComponent {
  @Input() visible = false;
  @Input() otpCode = '';
  @Input() email = '';
  @Input() title = 'Xác thực OTP';
  @Input() isVerifying = false;
  @Input() isResending = false;
  @Input() errorMessage = '';
  @Input() successMessage = '';
  @Input() countdown = 0;
  @Input() resendDisabled = false;

  @Output() verify = new EventEmitter<string>();
  @Output() resend = new EventEmitter<void>();

  otpInput = '';

  onInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    let value = target.value.replace(/\D/g, '');
    if (value.length > 6) {
      value = value.substring(0, 6);
    }
    this.otpInput = value;
    target.value = value;
  }

  onEnter(): void {
    if (this.otpInput.length === 6 && !this.isVerifying) {
      this.onVerify();
    }
  }

  onVerify(): void {
    if (this.otpInput.length !== 6 || this.isVerifying) {
      return;
    }
    this.verify.emit(this.otpInput);
  }

  onResend(): void {
    if (this.isResending || this.resendDisabled) {
      return;
    }
    this.otpInput = '';
    this.resend.emit();
  }

  formatCountdown(): string {
    const minutes = Math.floor(this.countdown / 60);
    const seconds = this.countdown % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  copyOtpCode(): void {
    if (!this.otpCode) {
      return;
    }
    navigator.clipboard.writeText(this.otpCode).catch(() => {
      // Clipboard not available
    });
  }
}
