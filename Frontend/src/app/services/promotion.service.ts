import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface PromotionCreateRequest {
  name: string;
  description: string;
  discount_type: 'PERCENTAGE' | 'FIXED';
  discount_value: number;
  start_date: string;
  end_date: string;
  quantity: number;
  is_active: boolean;
}

export interface Promotion {
  promotion_id: string;
  code: string; // Add this field
  name: string;
  description: string;
  discount_type: string;
  discount_value: number;
  start_date: string;
  end_date: string;
  quantity: number;
  used_count: number;
  is_active: boolean;
}

export interface PromotionCreateResponse {
  EC: number;
  EM: string;
  promotion: Promotion;
}

export interface PromotionDetailResponse {
  EC: number;
  EM: string;
  promotion: Promotion;
}

export interface PromotionListParams {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export interface PromotionListResponse {
  EC: number;
  EM: string;
  found: number;
  promotions: Promotion[];
}

@Injectable({
  providedIn: 'root'
})
export class PromotionService {
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

  createPromotion(promotion: PromotionCreateRequest): Observable<PromotionCreateResponse> {
    return this.http.post<PromotionCreateResponse>(
      `${this.apiBaseUrl}/promotions/`,
      promotion,
      {
        headers: this.getHeaders()
      }
    );
  }

  getPromotions(params?: PromotionListParams): Observable<PromotionListResponse> {
    let httpParams = new HttpParams();
    
    if (params?.is_active !== undefined) {
      httpParams = httpParams.set('is_active', params.is_active.toString());
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<PromotionListResponse>(
      `${this.apiBaseUrl}/promotions/`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  getAvailablePromotions(): Observable<PromotionListResponse> {
    return this.http.get<PromotionListResponse>(
      `${this.apiBaseUrl}/promotions/available`,
      {
        headers: this.getHeaders()
      }
    );
  }

  getPromotionById(promotionId: string): Observable<PromotionDetailResponse> {
    return this.http.get<PromotionDetailResponse>(
      `${this.apiBaseUrl}/promotions/${promotionId}`,
      {
        headers: this.getHeaders()
      }
    );
  }
}

