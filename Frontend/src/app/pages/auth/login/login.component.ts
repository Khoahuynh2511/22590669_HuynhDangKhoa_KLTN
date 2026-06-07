import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../services/auth.service';
import { AuthStateService } from '../../../services/auth-state.service';

@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterLink, CommonModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  loginMethod: 'email' | 'phone' = 'email';
  isLoading = false;
  otpSent = false;
  errorMessage: string | null = null;

  loginForm = {
    email: '',
    password: '',
    rememberMe: false
  };

  phoneForm = {
    phone: '',
    otp: ''
  };

  constructor(
    private router: Router,
    private authService: AuthService,
    private authStateService: AuthStateService
  ) {}

  onLogin() {
    this.isLoading = true;
    this.errorMessage = null;

    if (this.loginMethod === 'email') {
      if (this.loginForm.email && this.loginForm.password) {
        this.authService.loginWithEmail(this.loginForm.email, this.loginForm.password).subscribe({
          next: (response) => {
            console.log('Login success:', response);
            this.isLoading = false;
            if (response.EC === 0 && response.access_token) {
              localStorage.setItem('access_token', response.access_token);
              if (response.user) {
                localStorage.setItem('user', JSON.stringify(response.user));
                this.authStateService.login(response.access_token, response.user);
                
                // Redirect admin to /admin, regular users to /home
                if (response.user.role === 'admin') {
                  this.router.navigate(['/admin']);
            } else {
                  this.router.navigate(['/home']);
                }
              } else {
                this.router.navigate(['/home']);
              }
            } else {
              // Handle error response from backend
              this.errorMessage = response.EM || 'Vui lòng nhập đầy đủ email và mật khẩu.';
            }
          },
          error: (error) => {
            console.error('Login error:', error);
            this.isLoading = false;
            // Handle HTTP errors
            if (error.error && error.error.EM) {
              this.errorMessage = error.error.EM;
            } else {
              this.errorMessage = 'Vui lòng nhập đầy đủ email và mật khẩu.';
            }
          }
        });
      } else {
        this.isLoading = false;
        this.errorMessage = 'Vui lòng nhập đầy đủ email và mật khẩu.';
      }
    } else {
      if (this.phoneForm.phone && this.phoneForm.otp) {
        this.authService.loginWithPhone(this.phoneForm.phone, this.phoneForm.otp).subscribe({
          next: (response) => {
            console.log('Phone login success:', response);
            this.isLoading = false;
            // this.router.navigate(['/home']);
          },
          error: (error) => {
            console.error('Phone login error:', error);
            this.isLoading = false;
            if (error.error && error.error.EM) {
              this.errorMessage = error.error.EM;
            } else {
              this.errorMessage = 'Đã có lỗi xảy ra. Vui lòng thử lại sau.';
            }
          }
        });
      } else {
        this.isLoading = false;
        this.errorMessage = 'Vui lòng nhập đầy đủ số điện thoại và mã OTP.';
      }
    }
  }

  clearError() {
    this.errorMessage = null;
  }

  sendOTP() {
    if (!this.phoneForm.phone) {
      return;
    }

    this.isLoading = true;
    this.authService.sendOTP(this.phoneForm.phone).subscribe({
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
    this.phoneForm.otp = '';
    this.sendOTP();
  }

  onGoogleLogin() {
    this.isLoading = true;

    this.authService.getGoogleAuthUrl().subscribe({
      next: (response) => {
        this.isLoading = false;
        console.log('Google auth URL response:', response);
        
        if (response.EC === 0 && response.auth_url) {
          console.log('Google OAuth URL:', response.auth_url);
          
          if (!response.auth_url.includes('client_id')) {
            console.error('URL không chứa client_id:', response.auth_url);
            return;
          }
          
          window.location.href = response.auth_url;
        }
      },
      error: (error) => {
        console.error('Error getting Google auth URL:', error);
        this.isLoading = false;
        
        // Error handling - removed alert
      }
    });
  }
}
