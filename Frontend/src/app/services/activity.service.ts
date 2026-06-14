import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface ActivityPackage {
  activity_id: string;
  name: string;
  description: string;
  destination: string;
  time_slot: 'morning' | 'afternoon' | 'evening';
  category?: string;
  duration_hours?: number;
  price: number;
  difficulty?: string;
  location?: string;
  image_url?: string;
  gallery_urls?: string[];
  included_services?: string[];
  max_participants?: number;
  min_participants?: number;
  is_active: boolean;
  is_ai_generated: boolean;
}

export interface ActivityListResponse {
  EC: number;
  EM: string;
  data: ActivityPackage[];
}

export interface DestinationListResponse {
  EC: number;
  EM: string;
  data: string[];
}

export interface CustomCheckoutResponse {
  EC: number;
  EM: string;
  data: {
    success: boolean;
    plan_id: string;
    booking_id: string;
    payment_id?: string;
    payment_url?: string;
    total_price: number;
    error?: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ActivityService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) {}

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  getDestinations(): Observable<DestinationListResponse> {
    return this.http.get<DestinationListResponse>(
      `${this.apiBaseUrl}/activity-packages/destinations`,
      { headers: this.getHeaders() }
    );
  }

  getActivities(params?: {
    destination?: string;
    time_slot?: string;
    category?: string;
    limit?: number;
  }): Observable<ActivityListResponse> {
    let httpParams = new HttpParams();
    if (params?.destination) {
      httpParams = httpParams.set('destination', params.destination);
    }
    if (params?.time_slot) {
      httpParams = httpParams.set('time_slot', params.time_slot);
    }
    if (params?.category) {
      httpParams = httpParams.set('category', params.category);
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }

    return this.http.get<ActivityListResponse>(
      `${this.apiBaseUrl}/activity-packages/`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  checkoutCustomItinerary(payload: {
    destination: string;
    duration_days: number;
    group_size: number;
    travel_date: string;
    itinerary: Record<string, {
      morning: ActivityPackage | null | ActivityPackage[];
      afternoon: ActivityPackage | null | ActivityPackage[];
      evening: ActivityPackage | null | ActivityPackage[];
    }>;
    return_url?: string;
  }): Observable<CustomCheckoutResponse> {
    return this.http.post<CustomCheckoutResponse>(
      `${this.apiBaseUrl}/activity-packages/checkout`,
      payload,
      { headers: this.getHeaders() }
    );
  }
}
