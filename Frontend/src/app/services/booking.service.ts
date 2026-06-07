import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface MyBooking {
  booking_id: string;
  tour_name: string;
  destination: string;
  start_date: string;
  end_date: string;
  number_of_people: number;
  total_amount: number;
  status: 'pending' | 'otp_sent' | 'confirmed' | 'cancelled' | 'completed';
  created_at: string;
}

export interface MyBookingListResponse {
  EC: number;
  EM: string;
  data: MyBooking[];
  total: number;
}

export interface MyBookingParams {
  status?: 'pending' | 'otp_sent' | 'confirmed' | 'cancelled' | 'completed';
  limit?: number;
  offset?: number;
}

export interface TourPackage {
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

export interface MyBookingDetail {
  booking_id: string;
  status: 'pending' | 'otp_sent' | 'confirmed' | 'cancelled' | 'completed';
  number_of_people: number;
  total_amount: number;
  contact_name: string;
  contact_phone: string;
  special_requests: string;
  created_at: string;
  updated_at: string;
  tour_package: TourPackage;
}

export interface MyBookingDetailResponse {
  EC: number;
  EM: string;
  data: MyBookingDetail;
}

export interface BookingCreateRequest {
  package_id: string;
  number_of_people: number;
  contact_name: string;
  contact_phone: string;
  contact_email: string; // Required for OTP
  user_id: string;
  special_requests?: string;
  promotion_id?: string;
  promotion_code?: string;
}

export interface BookingCreateResponse {
  EC: number;
  EM: string;
  data?: {
    booking_id: string;
    package_id: string;
    user_id: string;
    number_of_people: number;
    total_amount: number;
    contact_name: string;
    contact_phone: string;
    contact_email?: string;
    special_requests?: string;
    promotion_id?: string;
    status: string;
    created_at: string;
    updated_at: string;
    awaiting_otp?: boolean; // For OTP flow
  };
}

export interface BookingDetail {
  booking_id: string;
  package_id: string;
  user_id: string;
  number_of_people: number;
  total_amount: number;
  contact_name: string;
  contact_phone: string;
  special_requests?: string;
  promotion_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BookingDetailResponse {
  EC: number;
  EM: string;
  data: BookingDetail;
}

export interface BookingUpdateRequest {
  contact_phone?: string;
  number_of_people?: number;
  promotion_id?: string;
  status?: string;
  contact_name?: string;
  special_requests?: string;
}

export interface BookingUpdateResponse {
  EC: number;
  EM: string;
  data: {
    booking_id: string;
    package_id: string;
    user_id: string;
    number_of_people: number;
    total_amount: number;
    contact_name: string;
    contact_phone: string;
    special_requests?: string;
    promotion_id?: string;
    status: string;
    created_at: string;
    updated_at: string;
  };
}

export interface BookingDeleteResponse {
  EC: number;
  EM: string;
}

@Injectable({
  providedIn: 'root'
})
export class BookingService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) { }

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

  getMyBookings(params?: MyBookingParams): Observable<MyBookingListResponse> {
    let httpParams = new HttpParams();

    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.limit) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<MyBookingListResponse>(
      `${this.apiBaseUrl}/bookings/my-bookings`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  getMyBookingDetail(bookingId: string): Observable<MyBookingDetailResponse> {
    return this.http.get<MyBookingDetailResponse>(
      `${this.apiBaseUrl}/bookings/my-bookings/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  createBooking(booking: BookingCreateRequest): Observable<BookingCreateResponse> {
    // Backend uses create-with-otp endpoint
    return this.http.post<BookingCreateResponse>(
      `${this.apiBaseUrl}/bookings/create-with-otp`,
      booking,
      {
        headers: this.getHeaders()
      }
    );
  }

  getBookingDetail(bookingId: string): Observable<BookingDetailResponse> {
    return this.http.get<BookingDetailResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  updateBooking(bookingId: string, booking: BookingUpdateRequest): Observable<BookingUpdateResponse> {
    return this.http.put<BookingUpdateResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}`,
      booking,
      {
        headers: this.getHeaders()
      }
    );
  }

  deleteBooking(bookingId: string): Observable<BookingDeleteResponse> {
    return this.http.delete<BookingDeleteResponse>(
      `${this.apiBaseUrl}/bookings/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  // Verify OTP for booking
  verifyOTP(bookingId: string, otpCode: string): Observable<BookingCreateResponse> {
    return this.http.post<BookingCreateResponse>(
      `${this.apiBaseUrl}/bookings/verify-otp`,
      {
        booking_id: bookingId,
        otp_code: otpCode
      },
      {
        headers: this.getHeaders()
      }
    );
  }

  // Resend OTP for booking
  resendOTP(bookingId: string): Observable<BookingCreateResponse> {
    return this.http.post<BookingCreateResponse>(
      `${this.apiBaseUrl}/bookings/resend-otp`,
      {
        booking_id: bookingId
      },
      {
        headers: this.getHeaders()
      }
    );
  }
}

