import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface BusBookingCreateRequest {
  bus_id: string;
  seat_type_id: string;
  num_passengers: number;
  passenger_name: string;
  passenger_email: string;
  passenger_phone: string;
}

export interface BusBookingOTPResponse {
  EC: number;
  EM: string;
  data: {
    booking_id: string;
    awaiting_otp: boolean;
    status: string;
    contact_email: string;
    total_price: number;
    bus_number: string;
    seat_type_name: string;
    otp_code?: string;
  } | null;
}

export interface MyBusBooking {
  booking_id: string;
  bus_number: string;
  company_name: string;
  departure_city: string;
  arrival_city: string;
  departure_time: string;
  seat_type: string;
  num_passengers: number;
  total_price: number;
  status: string;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class BusBookingService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/bus-bookings`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  createBooking(data: BusBookingCreateRequest): Observable<BusBookingOTPResponse> {
    return this.http.post<BusBookingOTPResponse>(
      `${this.apiBaseUrl}/create-with-otp`,
      data,
      { headers: this.getHeaders() }
    );
  }

  verifyOTP(bookingId: string, otpCode: string): Observable<BusBookingOTPResponse> {
    return this.http.post<BusBookingOTPResponse>(
      `${this.apiBaseUrl}/verify-otp`,
      { booking_id: bookingId, otp_code: otpCode },
      { headers: this.getHeaders() }
    );
  }

  resendOTP(bookingId: string): Observable<BusBookingOTPResponse> {
    return this.http.post<BusBookingOTPResponse>(
      `${this.apiBaseUrl}/resend-otp`,
      { booking_id: bookingId },
      { headers: this.getHeaders() }
    );
  }

  getMyBookings(): Observable<{ EC: number; EM: string; data: MyBusBooking[]; total: number }> {
    return this.http.get<{ EC: number; EM: string; data: MyBusBooking[]; total: number }>(
      `${this.apiBaseUrl}/my-bookings`,
      { headers: this.getHeaders() }
    );
  }

  cancelBooking(bookingId: string, reason?: string): Observable<BusBookingOTPResponse> {
    return this.http.post<BusBookingOTPResponse>(
      `${this.apiBaseUrl}/${bookingId}/cancel`,
      { reason },
      { headers: this.getHeaders() }
    );
  }
}
