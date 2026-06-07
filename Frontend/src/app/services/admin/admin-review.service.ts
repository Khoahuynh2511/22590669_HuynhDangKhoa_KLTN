import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

// Review interfaces
export interface Review {
  review_id: string;
  booking_id: string;
  user_id: string;
  package_id: string;
  rating: number;
  comment: string;
  is_approved: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReviewDetail extends Review {
  user_full_name: string;
  user_email: string;
  package_name: string;
  destination: string;
}

export interface ReviewListResponse {
  EC: number;
  EM: string;
  data: Review[];
  total: number;
}

export interface ReviewDetailResponse {
  EC: number;
  EM: string;
  data: ReviewDetail;
}

export interface ReviewCreateRequest {
  booking_id: string;
  package_id: string;
  rating: number;
  comment: string;
}

export interface ReviewUpdateRequest {
  rating?: number;
  comment?: string;
  is_approved?: boolean;
}

export interface ReviewApproveRequest {
  is_approved: boolean;
}

export interface ReviewResponse {
  EC: number;
  EM: string;
  data?: Review;
}

export interface ReviewStatsResponse {
  EC: number;
  EM: string;
  data: {
    total_reviews: number;
    average_rating: number;
    rating_distribution: {
      [key: number]: number;
    };
  };
}

@Injectable({
  providedIn: 'root'
})
export class AdminReviewService {
  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/reviews`;
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
   * GET /api/v1/reviews/
   * Get reviews with filters
   */
  getReviews(params?: {
    package_id?: string;
    user_id?: string;
    is_approved?: boolean;
    rating?: number;
    limit?: number;
    offset?: number;
  }): Observable<ReviewListResponse> {
    let httpParams = new HttpParams();
    
    if (params?.package_id) httpParams = httpParams.set('package_id', params.package_id);
    if (params?.user_id) httpParams = httpParams.set('user_id', params.user_id);
    if (params?.is_approved !== undefined) httpParams = httpParams.set('is_approved', params.is_approved.toString());
    if (params?.rating) httpParams = httpParams.set('rating', params.rating.toString());
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params?.offset) httpParams = httpParams.set('offset', params.offset.toString());

    return this.http.get<ReviewListResponse>(
      this.apiBaseUrl,
      { headers: this.getHeaders(), params: httpParams }
    );
  }

  /**
   * POST /api/v1/reviews/
   * Create a new review (authenticated users only)
   */
  createReview(request: ReviewCreateRequest): Observable<ReviewResponse> {
    return this.http.post<ReviewResponse>(
      this.apiBaseUrl,
      request,
      { headers: this.getHeaders() }
    );
  }

  /**
   * GET /api/v1/reviews/package/{package_id}
   * Get reviews for a specific package
   */
  getReviewsByPackage(
    packageId: string,
    params?: {
      is_approved?: boolean;
      limit?: number;
      offset?: number;
    }
  ): Observable<ReviewListResponse> {
    let httpParams = new HttpParams();
    
    if (params?.is_approved !== undefined) httpParams = httpParams.set('is_approved', params.is_approved.toString());
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params?.offset) httpParams = httpParams.set('offset', params.offset.toString());

    return this.http.get<ReviewListResponse>(
      `${this.apiBaseUrl}/package/${packageId}`,
      { headers: this.getHeaders(), params: httpParams }
    );
  }

  /**
   * GET /api/v1/reviews/package/{package_id}/stats
   * Get review statistics for a package
   */
  getReviewStats(packageId: string): Observable<ReviewStatsResponse> {
    return this.http.get<ReviewStatsResponse>(
      `${this.apiBaseUrl}/package/${packageId}/stats`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * GET /api/v1/reviews/{review_id}
   * Get review details
   */
  getReview(reviewId: string): Observable<ReviewDetailResponse> {
    return this.http.get<ReviewDetailResponse>(
      `${this.apiBaseUrl}/${reviewId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * PUT /api/v1/reviews/{review_id}
   * Update review (owner or admin only)
   */
  updateReview(reviewId: string, request: ReviewUpdateRequest): Observable<ReviewResponse> {
    return this.http.put<ReviewResponse>(
      `${this.apiBaseUrl}/${reviewId}`,
      request,
      { headers: this.getHeaders() }
    );
  }

  /**
   * DELETE /api/v1/reviews/{review_id}
   * Delete review (owner or admin only)
   */
  deleteReview(reviewId: string): Observable<ReviewResponse> {
    return this.http.delete<ReviewResponse>(
      `${this.apiBaseUrl}/${reviewId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * GET /api/v1/reviews/admin/pending
   * Get pending reviews (admin only)
   */
  getPendingReviews(params?: {
    package_id?: string;
    limit?: number;
    offset?: number;
  }): Observable<ReviewListResponse> {
    let httpParams = new HttpParams();
    
    if (params?.package_id) httpParams = httpParams.set('package_id', params.package_id);
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params?.offset) httpParams = httpParams.set('offset', params.offset.toString());

    return this.http.get<ReviewListResponse>(
      `${this.apiBaseUrl}/admin/pending`,
      { headers: this.getHeaders(), params: httpParams }
    );
  }

  /**
   * PUT /api/v1/reviews/admin/{review_id}/approve
   * Approve or reject review (admin only)
   */
  approveReview(reviewId: string, request: ReviewApproveRequest): Observable<ReviewResponse> {
    return this.http.put<ReviewResponse>(
      `${this.apiBaseUrl}/admin/${reviewId}/approve`,
      request,
      { headers: this.getHeaders() }
    );
  }

  /**
   * GET /api/v1/reviews/admin/all
   * Get all reviews including unapproved (admin only)
   */
  getAllReviewsAdmin(params?: {
    package_id?: string;
    user_id?: string;
    is_approved?: boolean;
    rating?: number;
    limit?: number;
    offset?: number;
  }): Observable<ReviewListResponse> {
    let httpParams = new HttpParams();
    
    if (params?.package_id) httpParams = httpParams.set('package_id', params.package_id);
    if (params?.user_id) httpParams = httpParams.set('user_id', params.user_id);
    if (params?.is_approved !== undefined) httpParams = httpParams.set('is_approved', params.is_approved.toString());
    if (params?.rating) httpParams = httpParams.set('rating', params.rating.toString());
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params?.offset) httpParams = httpParams.set('offset', params.offset.toString());

    return this.http.get<ReviewListResponse>(
      `${this.apiBaseUrl}/admin/all`,
      { headers: this.getHeaders(), params: httpParams }
    );
  }
}
