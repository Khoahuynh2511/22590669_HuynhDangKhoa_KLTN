import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

// Request Interfaces
export interface ReviewCreateRequest {
  booking_id: string;
  package_id: string;
  rating: number;
  comment: string;
  images?: string[];
}

export interface ReviewUpdateRequest {
  rating?: number;
  comment?: string;
  images?: string[];
}

// Response Interfaces
export interface Review {
  review_id: string;
  booking_id: string;
  package_id: string;
  user_id: string;
  rating: number;
  comment: string;
  images?: string[];
  is_approved: boolean;
  created_at: string;
  updated_at: string;
  // Flat fields from ReviewWithUserInfo
  user_full_name?: string;
  user_email?: string;
  user_profile_picture?: string;
  package_name?: string;
  destination?: string;
  // Nested objects (legacy support)
  package?: {
    package_id: string;
    title: string;
    destination: string;
  };
  user?: {
    user_id: string;
    full_name: string;
    email: string;
  };
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
  data: Review;
}

export interface ReviewCreateResponse {
  EC: number;
  EM: string;
  data?: Review;
}

export interface ReviewUpdateResponse {
  EC: number;
  EM: string;
  data?: Review;
}

export interface ReviewDeleteResponse {
  EC: number;
  EM: string;
}

export interface ReviewStatsResponse {
  EC: number;
  EM: string;
  data: {
    average_rating: number;
    total_reviews: number;
    rating_distribution: {
      [key: string]: number;
    };
  };
}

export interface ReviewListParams {
  package_id?: string;
  user_id?: string;
  is_approved?: boolean;
  rating?: number;
  limit?: number;
  offset?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ReviewService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) { }

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    let headers = new HttpHeaders();
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  }

  /**
   * Get all reviews with optional filters
   */
  getReviews(params?: ReviewListParams): Observable<ReviewListResponse> {
    let httpParams = new HttpParams();

    if (params) {
      if (params.package_id) httpParams = httpParams.set('package_id', params.package_id);
      if (params.user_id) httpParams = httpParams.set('user_id', params.user_id);
      if (params.is_approved !== undefined) httpParams = httpParams.set('is_approved', params.is_approved.toString());
      if (params.rating) httpParams = httpParams.set('rating', params.rating.toString());
      if (params.limit) httpParams = httpParams.set('limit', params.limit.toString());
      if (params.offset) httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<ReviewListResponse>(`${this.apiBaseUrl}/reviews`, {
      params: httpParams,
      headers: this.getHeaders()
    });
  }

  /**
   * Get reviews for a specific package
   */
  getReviewsByPackage(packageId: string, isApproved: boolean = true): Observable<ReviewListResponse> {
    return this.getReviews({ package_id: packageId, is_approved: isApproved });
  }

  /**
   * Get current user's reviews
   */
  getMyReviews(): Observable<ReviewListResponse> {
    return this.http.get<ReviewListResponse>(`${this.apiBaseUrl}/reviews/my-reviews`, {
      headers: this.getHeaders()
    });
  }

  /**
   * Get completed bookings that can be reviewed
   */
  getReviewableBookings(params?: { limit?: number; offset?: number }): Observable<any> {
    let httpParams = new HttpParams();

    if (params) {
      if (params.limit) httpParams = httpParams.set('limit', params.limit.toString());
      if (params.offset) httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<any>(`${this.apiBaseUrl}/reviews/my-reviewable-bookings`, {
      params: httpParams,
      headers: this.getHeaders()
    });
  }

  /**
   * Get a specific review by ID
   */
  getReviewById(reviewId: string): Observable<ReviewDetailResponse> {
    return this.http.get<ReviewDetailResponse>(`${this.apiBaseUrl}/reviews/${reviewId}`, {
      headers: this.getHeaders()
    });
  }

  /**
   * Create a new review
   */
  createReview(review: ReviewCreateRequest): Observable<ReviewCreateResponse> {
    return this.http.post<ReviewCreateResponse>(
      `${this.apiBaseUrl}/reviews/`,
      review,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Update an existing review
   */
  updateReview(reviewId: string, review: ReviewUpdateRequest): Observable<ReviewUpdateResponse> {
    return this.http.put<ReviewUpdateResponse>(
      `${this.apiBaseUrl}/reviews/${reviewId}`,
      review,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Delete a review
   */
  deleteReview(reviewId: string): Observable<ReviewDeleteResponse> {
    return this.http.delete<ReviewDeleteResponse>(
      `${this.apiBaseUrl}/reviews/${reviewId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Get review statistics for a package
   */
  getReviewStats(packageId: string): Observable<ReviewStatsResponse> {
    return this.http.get<ReviewStatsResponse>(
      `${this.apiBaseUrl}/reviews/stats/${packageId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Check if user can review a booking
   */
  canReviewBooking(bookingId: string): Observable<{ EC: number; EM: string; can_review: boolean; reason?: string }> {
    return this.http.get<{ EC: number; EM: string; can_review: boolean; reason?: string }>(
      `${this.apiBaseUrl}/reviews/can-review/${bookingId}`,
      { headers: this.getHeaders() }
    );
  }

  // Helper methods for displaying reviews
  getStarArray(rating: number): boolean[] {
    return Array(5).fill(false).map((_, i) => i < rating);
  }

  formatRating(rating: number): string {
    return rating.toFixed(1);
  }
}
