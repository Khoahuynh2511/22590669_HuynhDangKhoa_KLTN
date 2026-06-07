import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-register',
  imports: [FormsModule, RouterLink, CommonModule],
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
    private authService: AuthService
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
              this.router.navigate(['/login']);
            }
          },
          error: (error) => {
            console.error('Register error:', error);
            this.isLoading = false;
            // Error handling - removed alert
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
            // this.router.navigate(['/login']);
          },
          error: (error) => {
            console.error('Phone register error:', error);
            this.isLoading = false;
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
      },
      error: (error) => {
        console.error('OTP send error:', error);
        this.isLoading = false;
      }
    });
  }

  resendOTP() {
    this.otpSent = false;
    this.phoneRegisterForm.otp = '';
    this.sendOTP();
  }

  onGoogleRegister() {
    this.isLoading = true;
    this.authService.registerWithGoogle().subscribe({
      next: (response) => {
        console.log('Google register success:', response);
        this.isLoading = false;
        // this.router.navigate(['/home']);
      },
      error: (error) => {
        console.error('Google register error:', error);
        this.isLoading = false;
      }
    });
  }
}
