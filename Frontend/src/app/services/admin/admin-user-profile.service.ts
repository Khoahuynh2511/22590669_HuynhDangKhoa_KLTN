import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../config.service';

export interface UserProfile {
  user_id: string;
  email: string;
  full_name: string;
  phone_number: string;
  profile_picture?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfileResponse {
  EC: number;
  EM: string;
  data: UserProfile;
}

export interface UpdateProfileRequest {
  full_name?: string;
  phone_number?: string;
  profile_picture?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  EC: number;
  EM: string;
}

@Injectable({
  providedIn: 'root'
})
export class UserProfileService {
  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/users/me`;
  }

  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  /**
   * GET /api/v1/users/me
   * Get current user's profile
   */
  getMyProfile(): Observable<UserProfileResponse> {
    return this.http.get<UserProfileResponse>(
      this.apiBaseUrl,
      { headers: this.getHeaders() }
    );
  }

  /**
   * PATCH /api/v1/users/me
   * Update current user's profile
   */
  updateMyProfile(request: UpdateProfileRequest): Observable<UserProfileResponse> {
    return this.http.patch<UserProfileResponse>(
      this.apiBaseUrl,
      request,
      { headers: this.getHeaders() }
    );
  }

  /**
   * POST /api/v1/users/me/avatar
   * Upload profile picture
   */
  uploadAvatar(file: File): Observable<UserProfileResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('access_token');
    const headers = new HttpHeaders({
      'Authorization': token ? `Bearer ${token}` : ''
    });

    return this.http.post<UserProfileResponse>(
      `${this.apiBaseUrl}/avatar`,
      formData,
      { headers }
    );
  }

  /**
   * POST /api/v1/users/me/password
   * Change password
   */
  changePassword(request: ChangePasswordRequest): Observable<ChangePasswordResponse> {
    return this.http.post<ChangePasswordResponse>(
      `${this.apiBaseUrl}/password`,
      request,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Logout - clear local storage
   */
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
  }
}
