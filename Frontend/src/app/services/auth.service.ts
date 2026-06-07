import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { ConfigService } from './config.service';

interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  EC: number;
  EM: string;
  access_token?: string;
  user?: {
    email: string;
    full_name: string;
    user_id: string;
    role?: 'admin' | 'user';
  };
}

interface VerifyTokenRequest {
  token?: string;
}

interface VerifyTokenResponse {
  EC: number;
  EM: string;
  data?: {
    email: string;
    exp: number;
    full_name: string;
    user_id?: string;
    role?: 'admin' | 'user';
  };
}

interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
  phone_number: string;
}

interface RegisterResponse {
  EC: number;
  EM: string;
  user?: {
    email: string;
    full_name: string;
    user_id: string;
  };
}

interface GoogleLoginRequest {
  id_token: string;
}

interface GoogleAuthURLResponse {
  EC: number;
  EM: string;
  auth_url?: string;
}

interface GoogleCallbackResponse {
  EC: number;
  EM: string;
  access_token?: string;
  user?: {
    email: string;
    full_name: string;
    user_id: string;
    role?: 'admin' | 'user';
  };
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) { }

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  loginWithEmail(email: string, password: string): Observable<LoginResponse> {
    const requestData: LoginRequest = {
      email: email,
      password: password
    };

    return this.http.post<LoginResponse>(`${this.apiBaseUrl}/auth/login`, requestData);
  }

  loginWithPhone(phone: string, otp: string): Observable<any> {
    console.log('Phone login:', { phone, otp });
    return of({ success: true, user: { phone } });
  }

  sendOTP(phone: string): Observable<any> {
    console.log('Sending OTP to:', phone);
    return of({ success: true, message: 'OTP sent successfully' });
  }

  getGoogleAuthUrl(): Observable<GoogleAuthURLResponse> {
    return this.http.get<GoogleAuthURLResponse>(`${this.apiBaseUrl}/auth/google/auth-url`);
  }

  handleGoogleCallback(code: string, state?: string, format: string = 'json'): Observable<GoogleCallbackResponse> {
    const params: any = { code, format };
    if (state) {
      params.state = state;
    }
    
    return this.http.get<GoogleCallbackResponse>(`${this.apiBaseUrl}/auth/google/callback`, { params });
  }

  loginWithGoogle(idToken: string): Observable<LoginResponse> {
    const requestData: GoogleLoginRequest = {
      id_token: idToken
    };

    return this.http.post<LoginResponse>(`${this.apiBaseUrl}/auth/google/login`, requestData);
  }

  registerWithEmail(data: { fullName: string; email: string; phone: string; password: string }): Observable<RegisterResponse> {
    const requestData: RegisterRequest = {
      email: data.email,
      full_name: data.fullName,
      password: data.password,
      phone_number: data.phone
    };

    return this.http.post<RegisterResponse>(`${this.apiBaseUrl}/auth/register`, requestData);
  }

  registerWithPhone(phone: string, otp: string, data: any): Observable<any> {
    console.log('Phone registration:', { phone, otp, data });
    return of({ success: true, user: { phone, ...data } });
  }

  registerWithGoogle(): Observable<any> {
    console.log('Google registration initiated');
    return of({ success: true, user: { provider: 'google' } });
  }

  verifyToken(token?: string): Observable<VerifyTokenResponse> {
    const tokenToVerify = token || this.getToken();
    
    let headers = new HttpHeaders();
    if (tokenToVerify) {
      headers = headers.set('Authorization', `Bearer ${tokenToVerify}`);
    }

    const requestData: VerifyTokenRequest = tokenToVerify ? { token: tokenToVerify } : {};

    return this.http.post<VerifyTokenResponse>(
      `${this.apiBaseUrl}/auth/verify-token`,
      requestData,
      { headers }
    );
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getUser(): any {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
