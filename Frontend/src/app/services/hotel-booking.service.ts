import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface HotelBookingCreateRequest {
  hotel_id: string;
  user_id: string;
  check_in: string;
  check_out: string;
  num_rooms: number;
  num_guests: number;
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  special_requests?: string;
}

export interface HotelBookingOTPResponse {
  EC: number;
  EM: string;
  data: {
    booking_id: string;
    awaiting_otp: boolean;
    status: string;
    contact_email: string;
    total_price: number;
    nights: number;
    hotel_name: string;
    otp_code?: string;
  } | null;
}

export interface HotelVerifyOTPRequest {
  booking_id: string;
  otp_code: string;
}

export interface MyHotelBooking {
  booking_id: string;
  hotel_name: string;
  location: string;
  check_in: string;
  check_out: string;
  num_rooms: number;
  num_guests: number;
  total_price: number;
  status: string;
  image_urls: string | null;
  created_at: string;
}

export interface HotelBookingDetail {
  booking_id: string;
  status: string;
  check_in: string;
  check_out: string;
  num_rooms: number;
  num_guests: number;
  total_price: number;
  guest_name: string;
  guest_phone: string;
  guest_email: string | null;
  special_requests: string | null;
  created_at: string;
  updated_at: string;
  hotel: {
    hotel_id: string;
    hotel_name: string;
    location: string;
    star_rating: number;
    image_urls: string | null;
    price: number;
    address: string;
  } | null;
}

@Injectable({
  providedIn: 'root'
})
export class HotelBookingService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/hotel-bookings`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  createBooking(data: HotelBookingCreateRequest): Observable<HotelBookingOTPResponse> {
    return this.http.post<HotelBookingOTPResponse>(
      `${this.apiBaseUrl}/create-with-otp`,
      data,
      { headers: this.getHeaders() }
    );
  }

  verifyOTP(bookingId: string, otpCode: string): Observable<HotelBookingOTPResponse> {
    return this.http.post<HotelBookingOTPResponse>(
      `${this.apiBaseUrl}/verify-otp`,
      { booking_id: bookingId, otp_code: otpCode },
      { headers: this.getHeaders() }
    );
  }

  resendOTP(bookingId: string): Observable<HotelBookingOTPResponse> {
    return this.http.post<HotelBookingOTPResponse>(
      `${this.apiBaseUrl}/resend-otp`,
      { booking_id: bookingId },
      { headers: this.getHeaders() }
    );
  }

  getMyBookings(): Observable<{ EC: number; EM: string; data: MyHotelBooking[]; total: number }> {
    return this.http.get<{ EC: number; EM: string; data: MyHotelBooking[]; total: number }>(
      `${this.apiBaseUrl}/my-bookings`,
      { headers: this.getHeaders() }
    );
  }

  getBookingDetail(bookingId: string): Observable<{ EC: number; EM: string; data: HotelBookingDetail }> {
    return this.http.get<{ EC: number; EM: string; data: HotelBookingDetail }>(
      `${this.apiBaseUrl}/my-bookings/${bookingId}`,
      { headers: this.getHeaders() }
    );
  }

  cancelBooking(bookingId: string, reason?: string): Observable<HotelBookingOTPResponse> {
    return this.http.post<HotelBookingOTPResponse>(
      `${this.apiBaseUrl}/${bookingId}/cancel`,
      { reason },
      { headers: this.getHeaders() }
    );
  }
}
