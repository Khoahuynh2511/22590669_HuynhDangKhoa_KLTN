import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';
import { UserProfileResponse, UpdateProfileRequest, UpdateProfileResponse } from '../shared/models/user-profile.model';

@Injectable({
  providedIn: 'root'
})
export class ProfileService {
  private apiBaseUrl: string;

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
    private authService: AuthService
  ) {
    this.apiBaseUrl = this.configService.getApiUrl();
  }

  /**
   * Get current user's profile from server
   */
  getMyProfile(): Observable<UserProfileResponse> {
    const token = this.authService.getToken();
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    return this.http.get<UserProfileResponse>(`${this.apiBaseUrl}/users/me`, { headers })
      .pipe(
        catchError(error => {
          console.error('Error fetching profile:', error);
          // Handle 401/403 by logging out
          if (error.status === 401 || error.status === 403) {
            this.authService.logout();
          }
          return throwError(() => error);
        })
      );
  }

  /**
   * Update current user's profile
   */
  updateMyProfile(data: UpdateProfileRequest): Observable<UpdateProfileResponse> {
    const token = this.authService.getToken();
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });

    return this.http.patch<UpdateProfileResponse>(`${this.apiBaseUrl}/users/me`, data, { headers })
      .pipe(
        tap(response => {
          // Update localStorage user if successful
          if (response.EC === 0 && response.data) {
            const currentUser = this.authService.getUser();
            if (currentUser) {
              const updatedUser = {
                ...currentUser,
                full_name: response.data.full_name,
                email: response.data.email,
                user_id: response.data.user_id,
                profile_picture: response.data.profile_picture
              };
              localStorage.setItem('user', JSON.stringify(updatedUser));
            }
          }
        }),
        catchError(error => {
          console.error('Error updating profile:', error);
          if (error.status === 401 || error.status === 403) {
            this.authService.logout();
          }
          return throwError(() => error);
        })
      );
  }

  /**
   * Upload profile picture to Cloudinary via backend
   */
  /**
   * Change user password
   */
  changePassword(data: { current_password: string; new_password: string }): Observable<{ EC: number; EM: string }> {
    const token = this.authService.getToken();
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });

    return this.http.post<{ EC: number; EM: string }>(`${this.apiBaseUrl}/users/me/password`, data, { headers })
      .pipe(
        catchError(error => {
          console.error('Error changing password:', error);
          if (error.status === 401 || error.status === 403) {
            this.authService.logout();
          }
          return throwError(() => error);
        })
      );
  }

  uploadProfilePicture(file: File): Observable<UpdateProfileResponse> {
    const token = this.authService.getToken();
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<UpdateProfileResponse>(`${this.apiBaseUrl}/users/me/avatar`, formData, { headers })
      .pipe(
        tap(response => {
          if (response.EC === 0 && response.data) {
            const currentUser = this.authService.getUser();
            if (currentUser) {
              const updatedUser = {
                ...currentUser,
                full_name: response.data.full_name,
                email: response.data.email,
                user_id: response.data.user_id,
                profile_picture: response.data.profile_picture
              };
              localStorage.setItem('user', JSON.stringify(updatedUser));
            }
          }
        }),
        catchError(error => {
          console.error('Error uploading profile picture:', error);
          if (error.status === 401 || error.status === 403) {
            this.authService.logout();
          }
          return throwError(() => error);
        })
      );
  }
}
