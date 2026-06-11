import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface FlightBookingCreateRequest {
  flight_id: string;
  seat_class: string;
  num_passengers: number;
  passenger_name: string;
  passenger_email: string;
  passenger_phone: string;
}

export interface FlightBookingOTPResponse {
  EC: number;
  EM: string;
  data: {
    booking_id: string;
    awaiting_otp: boolean;
    status: string;
    contact_email: string;
    total_price: number;
    flight_number: string;
    otp_code?: string;
  } | null;
}

export interface MyFlightBooking {
  booking_id: string;
  flight_number: string;
  airline_name: string;
  departure_city: string;
  arrival_city: string;
  departure_time: string;
  seat_class: string;
  num_passengers: number;
  total_price: number;
  status: string;
  created_at: string;
}

export interface FlightBookingDetail {
  booking_id: string;
  status: string;
  passenger_name: string;
  passenger_phone: string;
  passenger_email: string | null;
  seat_class: string;
  num_passengers: number;
  total_price: number;
  created_at: string;
  updated_at: string;
  flight: {
    flight_id: string;
    flight_number: string;
    airline: { name: string; logo_url: string };
    departure_airport: string;
    arrival_airport: string;
    departure_time: string;
    arrival_time: string;
    duration_minutes: number;
    aircraft: string;
  } | null;
}

@Injectable({
  providedIn: 'root'
})
export class FlightBookingService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/flight-bookings`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  createBooking(data: FlightBookingCreateRequest): Observable<FlightBookingOTPResponse> {
    return this.http.post<FlightBookingOTPResponse>(
      `${this.apiBaseUrl}/create-with-otp`,
      data,
      { headers: this.getHeaders() }
    );
  }

  verifyOTP(bookingId: string, otpCode: string): Observable<FlightBookingOTPResponse> {
    return this.http.post<FlightBookingOTPResponse>(
      `${this.apiBaseUrl}/verify-otp`,
      { booking_id: bookingId, otp_code: otpCode },
      { headers: this.getHeaders() }
    );
  }

  resendOTP(bookingId: string): Observable<FlightBookingOTPResponse> {
    return this.http.post<FlightBookingOTPResponse>(
      `${this.apiBaseUrl}/resend-otp`,
      { booking_id: bookingId },
      { headers: this.getHeaders() }
    );
  }

  getMyBookings(): Observable<{ EC: number; EM: string; data: MyFlightBooking[]; total: number }> {
    return this.http.get<{ EC: number; EM: string; data: MyFlightBooking[]; total: number }>(
      `${this.apiBaseUrl}/my-bookings`,
      { headers: this.getHeaders() }
    );
  }

  getBookingDetail(bookingId: string): Observable<{ EC: number; EM: string; data: FlightBookingDetail }> {
    return this.http.get<{ EC: number; EM: string; data: FlightBookingDetail }>(
      `${this.apiBaseUrl}/my-bookings/${bookingId}`,
      { headers: this.getHeaders() }
    );
  }

  cancelBooking(bookingId: string, reason?: string): Observable<FlightBookingOTPResponse> {
    return this.http.post<FlightBookingOTPResponse>(
      `${this.apiBaseUrl}/${bookingId}/cancel`,
      { reason },
      { headers: this.getHeaders() }
    );
  }
}
