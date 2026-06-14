import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

export interface ActivityPackageItem {
  activity_id: string;
  name: string;
  description?: string;
  destination: string;
  time_slot: 'morning' | 'afternoon' | 'evening';
  category?: string;
  duration_hours?: number;
  price: number;
  difficulty?: 'easy' | 'moderate' | 'hard';
  location?: string;
  image_url?: string;
  gallery_urls?: string[];
  included_services?: string[];
  max_participants?: number;
  min_participants?: number;
  is_active: boolean;
  is_ai_generated: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ActivityListResponse {
  EC: number;
  EM: string;
  data: {
    activities: ActivityPackageItem[];
    total: number;
  };
}

export interface ActivityDetailResponse {
  EC: number;
  EM: string;
  data: ActivityPackageItem;
}

@Injectable({
  providedIn: 'root'
})
export class AdminActivityService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/activity-packages`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  getActivities(params?: {
    limit?: number;
    offset?: number;
    destination?: string;
    category?: string;
    searchTerm?: string;
  }): Observable<ActivityListResponse> {
    let httpParams = new HttpParams();
    if (params) {
      if (params.limit !== undefined) httpParams = httpParams.set('limit', params.limit.toString());
      if (params.offset !== undefined) httpParams = httpParams.set('offset', params.offset.toString());
      if (params.destination) httpParams = httpParams.set('destination', params.destination);
      if (params.category) httpParams = httpParams.set('category', params.category);
      if (params.searchTerm) httpParams = httpParams.set('searchTerm', params.searchTerm);
    }
    return this.http.get<ActivityListResponse>(`${this.apiBaseUrl}/admin`, {
      headers: this.getHeaders(),
      params: httpParams
    });
  }

  getActivityById(activityId: string): Observable<ActivityDetailResponse> {
    return this.http.get<ActivityDetailResponse>(`${this.apiBaseUrl}/${activityId}`, { headers: this.getHeaders() });
  }

  createActivity(data: Partial<ActivityPackageItem>): Observable<ActivityDetailResponse> {
    return this.http.post<ActivityDetailResponse>(`${this.apiBaseUrl}/`, data, { headers: this.getHeaders() });
  }

  updateActivity(activityId: string, data: Partial<ActivityPackageItem>): Observable<ActivityDetailResponse> {
    return this.http.put<ActivityDetailResponse>(`${this.apiBaseUrl}/${activityId}`, data, { headers: this.getHeaders() });
  }

  deleteActivity(activityId: string): Observable<{ EC: number; EM: string; data: null }> {
    return this.http.delete<{ EC: number; EM: string; data: null }>(`${this.apiBaseUrl}/${activityId}`, { headers: this.getHeaders() });
  }
}
