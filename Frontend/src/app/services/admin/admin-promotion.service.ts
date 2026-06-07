import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../config.service';

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

export interface PromotionUpdateRequest {
  name?: string;
  description?: string;
  discount_type?: 'PERCENTAGE' | 'FIXED';
  discount_value?: number;
  start_date?: string;
  end_date?: string;
  quantity?: number;
  is_active?: boolean;
  code?: string;
}

export interface Promotion {
  promotion_id: string;
  code: string;
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

export interface DeleteResponse {
  EC: number;
  EM: string;
}

@Injectable({
  providedIn: 'root'
})
export class AdminPromotionService {
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

  updatePromotion(promotionId: string, promotion: PromotionUpdateRequest): Observable<PromotionDetailResponse> {
    return this.http.put<PromotionDetailResponse>(
      `${this.apiBaseUrl}/promotions/${promotionId}`,
      promotion,
      {
        headers: this.getHeaders()
      }
    );
  }

  deletePromotion(promotionId: string): Observable<DeleteResponse> {
    return this.http.delete<DeleteResponse>(
      `${this.apiBaseUrl}/promotions/${promotionId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  getPromotionByCode(code: string): Observable<PromotionDetailResponse> {
    return this.http.get<PromotionDetailResponse>(
      `${this.apiBaseUrl}/promotions/code/${code}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * Filter promotions by discount value range
   */
  filterByDiscount(params: {
    min_discount_value?: number;
    max_discount_value?: number;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<PromotionListResponse> {
    let httpParams = new HttpParams();
    
    if (params.min_discount_value !== undefined) {
      httpParams = httpParams.set('min_discount_value', params.min_discount_value.toString());
    }
    if (params.max_discount_value !== undefined) {
      httpParams = httpParams.set('max_discount_value', params.max_discount_value.toString());
    }
    if (params.is_active !== undefined) {
      httpParams = httpParams.set('is_active', params.is_active.toString());
    }
    if (params.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<PromotionListResponse>(
      `${this.apiBaseUrl}/promotions/filter/by-discount`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * Filter promotions by date range
   */
  filterByDateRange(params: {
    start_date?: string;
    end_date?: string;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<PromotionListResponse> {
    let httpParams = new HttpParams();
    
    if (params.start_date) {
      httpParams = httpParams.set('start_date', params.start_date);
    }
    if (params.end_date) {
      httpParams = httpParams.set('end_date', params.end_date);
    }
    if (params.is_active !== undefined) {
      httpParams = httpParams.set('is_active', params.is_active.toString());
    }
    if (params.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<PromotionListResponse>(
      `${this.apiBaseUrl}/promotions/filter/by-date-range`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * Filter promotions by quantity range
   */
  filterByQuantity(params: {
    min_quantity?: number;
    max_quantity?: number;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<PromotionListResponse> {
    let httpParams = new HttpParams();
    
    if (params.min_quantity !== undefined) {
      httpParams = httpParams.set('min_quantity', params.min_quantity.toString());
    }
    if (params.max_quantity !== undefined) {
      httpParams = httpParams.set('max_quantity', params.max_quantity.toString());
    }
    if (params.is_active !== undefined) {
      httpParams = httpParams.set('is_active', params.is_active.toString());
    }
    if (params.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<PromotionListResponse>(
      `${this.apiBaseUrl}/promotions/filter/by-quantity`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * Filter promotions by user count (used_count) range
   */
  filterByUserCount(params: {
    min_user_count?: number;
    max_user_count?: number;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<PromotionListResponse> {
    let httpParams = new HttpParams();
    
    if (params.min_user_count !== undefined) {
      httpParams = httpParams.set('min_user_count', params.min_user_count.toString());
    }
    if (params.max_user_count !== undefined) {
      httpParams = httpParams.set('max_user_count', params.max_user_count.toString());
    }
    if (params.is_active !== undefined) {
      httpParams = httpParams.set('is_active', params.is_active.toString());
    }
    if (params.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<PromotionListResponse>(
      `${this.apiBaseUrl}/promotions/filter/by-user-count`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }
}
