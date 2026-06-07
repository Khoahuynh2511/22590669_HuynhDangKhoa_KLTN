import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

// Admin Booking List Item (response từ /admin/all và /admin/user/{user_id})
export interface AdminBookingItem {
  booking_id: string;
  user_id: string;
  user_email: string;
  user_full_name: string;
  tour_name: string;
  destination: string;
  start_date: string;
  number_of_people: number;
  total_amount: number;
  status: string;
  created_at: string;
}

// Admin Booking Detail (response từ /admin/{booking_id})
export interface TourPackageInfo {
  package_id: string;
  package_name: string;
  destination: string;
  description: string;
  duration_days: number;
  start_date: string;
  end_date: string;
  price: number;
  image_urls: string;
}

export interface AdminBookingDetail {
  booking_id: string;
  status: string;
  number_of_people: number;
  total_amount: number;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  special_requests: string;
  created_at: string;
  updated_at: string;
  tour_package: TourPackageInfo;
}

// Standard Booking Item (cho các endpoints thông thường)
export interface BookingItem {
  booking_id: string;
  package_id: string;
  user_id: string;
  number_of_people: number;
  total_amount: number;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  special_requests?: string;
  promotion_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BookingListParams {
  status?: string;
  limit?: number;
  offset?: number;
}

export interface AdminBookingListResponse {
  EC: number;
  EM: string;
  data: AdminBookingItem[];
  total: number;
}

export interface AdminBookingDetailResponse {
  EC: number;
  EM: string;
  data: AdminBookingDetail;
}

export interface BookingListResponse {
  EC: number;
  EM: string;
  data: BookingItem[];
  total: number;
}

export interface BookingCreateRequest {
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  number_of_people: number;
  package_id: string;
  promotion_code?: string;
  special_requests?: string;
  user_id: string;
  skip_otp?: boolean; // Admin/trusted flow
}

// Response cho OTP flow
export interface BookingOTPResponse {
  EC: number;
  EM: string;
  data: {
    booking_id: string;
    awaiting_otp?: boolean;
    booking?: BookingItem;
  };
}

// Request verify OTP
export interface BookingVerifyOTPRequest {
  booking_id: string;
  otp_code: string;
}

// Request resend OTP
export interface BookingResendOTPRequest {
  booking_id: string;
}

// Legacy response (deprecated)
export interface BookingCreateResponse {
  EC: number;
  EM: string;
  data: BookingItem;
}

export interface BookingDetailResponse {
  EC: number;
  EM: string;
  data: BookingItem;
}

export interface BookingUpdateRequest {
  contact_phone?: string;
  contact_name?: string;
  contact_email?: string;
  number_of_people?: number;
  promotion_code?: string;
  special_requests?: string;
  status?: string;
}

export interface BookingUpdateResponse {
  EC: number;
  EM: string;
  data: BookingItem;
}

export interface BookingCancelRequest {
  reason?: string;
}

export interface BookingCancelResponse {
  EC: number;
  EM: string;
  data: BookingItem;
}

export interface BookingDeleteResponse {
  EC: number;
  EM: string;
}

// Booking Cancellation Item (from booking_cancellations table)
export interface BookingCancellationItem {
  cancellation_id: string;
  booking_id: string;
  user_id: string;
  user_email: string;
  user_full_name: string;
  package_id: string;
  tour_name: string;
  // Booking snapshot
  number_of_people: number;
  total_amount: number;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  special_requests?: string;
  previous_status: string;
  booking_created_at: string;
  // Cancellation info
  reason?: string;
  cancelled_at: string;
  cancelled_by: 'user' | 'admin' | 'system';
  created_at: string;
}

export interface BookingCancellationListResponse {
  EC: number;
  EM: string;
  data: BookingCancellationItem[];
  total: number;
}

export interface CancellationListParams {
  cancelled_by?: string;
  limit?: number;
  offset?: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminBookingService {
  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) { }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  /**
   * GET /api/v1/bookings/admin/all
   * Admin: Lấy tất cả bookings trong hệ thống với filters
   */
  getAllBookingsAdmin(params?: BookingListParams): Observable<AdminBookingListResponse> {
    let httpParams = new HttpParams();

    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<AdminBookingListResponse>(
      `${this.apiBaseUrl}/bookings/admin/all`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * GET /api/v1/bookings/admin/user/{user_id}
   * Admin: Lấy tất cả bookings của 1 user cụ thể
   */
  getUserBookingsAdmin(userId: string, params?: BookingListParams): Observable<AdminBookingListResponse> {
    let httpParams = new HttpParams();

    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<AdminBookingListResponse>(
      `${this.apiBaseUrl}/bookings/admin/user/${userId}`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * GET /api/v1/bookings/admin/{booking_id}
   * Admin: Lấy chi tiết bất kỳ booking nào với thông tin tour package
   */
  getBookingDetailAdmin(bookingId: string): Observable<AdminBookingDetailResponse> {
    return this.http.get<AdminBookingDetailResponse>(
      `${this.apiBaseUrl}/bookings/admin/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * GET /api/v1/bookings/
   * Lấy danh sách bookings với filters (deprecated - dùng getAllBookingsAdmin thay thế)
   * @deprecated Sử dụng getAllBookingsAdmin() hoặc getUserBookingsAdmin() thay thế
   */
  getBookings(params?: BookingListParams): Observable<BookingListResponse> {
    let httpParams = new HttpParams();

    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<BookingListResponse>(
      `${this.apiBaseUrl}/bookings/`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * POST /api/v1/bookings/create-with-otp
   * Tạo booking mới với OTP verification flow
   * 
   * Flow:
   * 1. Validate package & check slots
   * 2. Create booking với status="otp_sent"
   * 3. Generate OTP (6 số)
   * 4. Store OTP vào database
   * 5. Send OTP qua email
   * 6. Update package slots
   * 7. Return booking_id và awaiting_otp=True
   */
  createBookingWithOTP(booking: BookingCreateRequest): Observable<BookingOTPResponse> {
    return this.http.post<BookingOTPResponse>(
      `${this.apiBaseUrl}/bookings/create-with-otp`,
      booking,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * POST /api/v1/bookings/verify-otp
   * Verify OTP code và confirm booking
   * 
   * Flow:
   * 1. Get OTP record từ database
   * 2. Validate OTP code
   * 3. Check expiry (5 minutes)
   * 4. Check attempts (max 3)
   * 5. Mark OTP as verified
   * 6. Update booking status: "otp_sent" → "pending"
   * 7. Return booking confirmation
   */
  verifyOTP(request: BookingVerifyOTPRequest): Observable<BookingOTPResponse> {
    return this.http.post<BookingOTPResponse>(
      `${this.apiBaseUrl}/bookings/verify-otp`,
      request,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * POST /api/v1/bookings/resend-otp
   * Gửi lại OTP khi mã cũ hết hạn hoặc không nhận được
   * 
   * Flow:
   * 1. Get booking info và validate status (phải là "otp_sent")
   * 2. Get email từ OTP record cũ
   * 3. Delete OTP records cũ
   * 4. Generate OTP mới
   * 5. Store OTP mới vào database
   * 6. Send OTP qua email
   * 7. Return confirmation
   */
  resendOTP(request: BookingResendOTPRequest): Observable<BookingOTPResponse> {
    return this.http.post<BookingOTPResponse>(
      `${this.apiBaseUrl}/bookings/resend-otp`,
      request,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * @deprecated Sử dụng createBookingWithOTP() thay thế
   * Legacy method for backward compatibility
   */
  createBooking(booking: BookingCreateRequest): Observable<BookingOTPResponse> {
    return this.createBookingWithOTP(booking);
  }

  /**
   * GET /api/v1/bookings/{booking_id}
   * Lấy chi tiết một booking (deprecated - dùng getBookingDetailAdmin thay thế)
   * @deprecated Sử dụng getBookingDetailAdmin() để lấy thêm thông tin tour package
   */
  getBookingById(bookingId: string): Observable<BookingDetailResponse> {
    return this.http.get<BookingDetailResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * PUT /api/v1/bookings/{booking_id}
   * Cập nhật booking
   */
  updateBooking(bookingId: string, data: BookingUpdateRequest): Observable<BookingUpdateResponse> {
    return this.http.put<BookingUpdateResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}`,
      data,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * POST /api/v1/bookings/{booking_id}/cancel
   * Soft-cancel booking và hoàn slot tour
   */
  cancelBooking(bookingId: string, data?: BookingCancelRequest): Observable<BookingCancelResponse> {
    return this.http.post<BookingCancelResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}/cancel`,
      data || {},
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * DELETE /api/v1/bookings/{booking_id}
   * Xóa booking (hard delete)
   */
  deleteBooking(bookingId: string): Observable<BookingDeleteResponse> {
    return this.http.delete<BookingDeleteResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  /**
   * GET /api/v1/bookings/admin/cancellations
   * Admin: Lấy danh sách tất cả booking cancellations
   */
  getCancellationsAdmin(params?: CancellationListParams): Observable<BookingCancellationListResponse> {
    let httpParams = new HttpParams();

    if (params?.cancelled_by) {
      httpParams = httpParams.set('cancelled_by', params.cancelled_by);
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<BookingCancellationListResponse>(
      `${this.apiBaseUrl}/bookings/admin/cancellations`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }
}
