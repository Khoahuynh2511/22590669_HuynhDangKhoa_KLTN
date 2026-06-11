import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface TrainBookingCreateRequest {
  train_id: string;
  seat_type_id: string;
  num_passengers: number;
  passenger_name: string;
  passenger_email: string;
  passenger_phone: string;
}

export interface TrainBookingOTPResponse {
  EC: number;
  EM: string;
  data: {
    booking_id: string;
    awaiting_otp: boolean;
    status: string;
    contact_email: string;
    total_price: number;
    train_number: string;
    seat_type_name: string;
    otp_code?: string;
  } | null;
}

export interface MyTrainBooking {
  booking_id: string;
  train_number: string;
  departure_city: string;
  arrival_city: string;
  departure_time: string;
  seat_type: string;
  num_passengers: number;
  total_price: number;
  status: string;
  created_at: string;
}

export interface TrainBookingDetail {
  booking_id: string;
  status: string;
  passenger_name: string;
  passenger_phone: string;
  passenger_email: string | null;
  seat_type: string;
  num_passengers: number;
  total_price: number;
  created_at: string;
  updated_at: string;
  train: {
    train_id: string;
    train_number: string;
    train_type: { name: string };
    departure_station: string;
    arrival_station: string;
    departure_time: string;
    arrival_time: string;
    duration_hours: number;
  } | null;
}

@Injectable({
  providedIn: 'root'
})
export class TrainBookingService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/train-bookings`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  createBooking(data: TrainBookingCreateRequest): Observable<TrainBookingOTPResponse> {
    return this.http.post<TrainBookingOTPResponse>(
      `${this.apiBaseUrl}/create-with-otp`,
      data,
      { headers: this.getHeaders() }
    );
  }

  verifyOTP(bookingId: string, otpCode: string): Observable<TrainBookingOTPResponse> {
    return this.http.post<TrainBookingOTPResponse>(
      `${this.apiBaseUrl}/verify-otp`,
      { booking_id: bookingId, otp_code: otpCode },
      { headers: this.getHeaders() }
    );
  }

  resendOTP(bookingId: string): Observable<TrainBookingOTPResponse> {
    return this.http.post<TrainBookingOTPResponse>(
      `${this.apiBaseUrl}/resend-otp`,
      { booking_id: bookingId },
      { headers: this.getHeaders() }
    );
  }

  getMyBookings(): Observable<{ EC: number; EM: string; data: MyTrainBooking[]; total: number }> {
    return this.http.get<{ EC: number; EM: string; data: MyTrainBooking[]; total: number }>(
      `${this.apiBaseUrl}/my-bookings`,
      { headers: this.getHeaders() }
    );
  }

  getBookingDetail(bookingId: string): Observable<{ EC: number; EM: string; data: TrainBookingDetail }> {
    return this.http.get<{ EC: number; EM: string; data: TrainBookingDetail }>(
      `${this.apiBaseUrl}/my-bookings/${bookingId}`,
      { headers: this.getHeaders() }
    );
  }

  cancelBooking(bookingId: string, reason?: string): Observable<TrainBookingOTPResponse> {
    return this.http.post<TrainBookingOTPResponse>(
      `${this.apiBaseUrl}/${bookingId}/cancel`,
      { reason },
      { headers: this.getHeaders() }
    );
  }
}
