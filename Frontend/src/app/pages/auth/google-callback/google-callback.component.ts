import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../services/auth.service';
import { AuthStateService } from '../../../services/auth-state.service';

@Component({
  selector: 'app-google-callback',
  imports: [CommonModule],
  template: `
    <div class="callback-container">
      <div class="loading-spinner">
        <p>Đang xử lý đăng nhập Google...</p>
      </div>
    </div>
  `,
  styles: [`
    .callback-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }
    .loading-spinner {
      text-align: center;
    }
  `]
})
export class GoogleCallbackComponent implements OnInit {
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private authStateService: AuthStateService
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      const token = params['token'];
      const code = params['code'];
      const state = params['state'];
      const error = params['error'];

      if (error) {
        this.router.navigate(['/login']);
        return;
      }

      if (token) {
        this.handleToken(token);
      } else if (code) {
        this.handleCodeWithApi(code, state);
      } else {
        const hash = window.location.hash.substring(1);
        const hashParams = new URLSearchParams(hash);
        const hashToken = hashParams.get('token');
        const hashCode = hashParams.get('code');
        const hashState = hashParams.get('state');

        if (hashToken) {
          this.handleToken(hashToken);
        } else if (hashCode) {
          this.handleCodeWithApi(hashCode, hashState || undefined);
        } else {
          this.router.navigate(['/login']);
        }
      }
    });
  }

  private handleToken(token: string): void {
    localStorage.setItem('access_token', token);
    
    this.authService.verifyToken(token).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          const user = {
            email: response.data.email,
            full_name: response.data.full_name,
            user_id: response.data.user_id || response.data.email,
            role: response.data.role || 'user'
          };
          localStorage.setItem('user', JSON.stringify(user));
          this.authStateService.login(token, user);
          
          // Redirect admin to /admin, regular users to /home
          if (user.role === 'admin') {
            this.router.navigate(['/admin']);
          } else {
          this.router.navigate(['/home']);
          }
        } else {
          this.router.navigate(['/login']);
        }
      },
      error: () => {
        this.router.navigate(['/login']);
      }
    });
  }

  private handleCode(code: string): void {
    this.authService.loginWithGoogle(code).subscribe({
      next: (response) => {
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
          this.router.navigate(['/login']);
        }
      },
      error: (error) => {
        console.error('Google login error:', error);
        this.router.navigate(['/login']);
      }
    });
  }

  private handleCodeWithApi(code: string, state?: string): void {
    this.authService.handleGoogleCallback(code, state, 'json').subscribe({
      next: (response) => {
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
          this.router.navigate(['/login']);
        }
      },
      error: (error) => {
        console.error('Google callback error:', error);
        this.router.navigate(['/login']);
      }
    });
  }
}

