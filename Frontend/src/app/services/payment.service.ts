import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface PaymentCreateRequest {
  booking_id: string;
  payment_method: string;
}

export interface PaymentData {
  payment_id: string;
  booking_id: string;
  amount: number;
  payment_method: string;
  payment_status: string;
  transaction_id: string;
  payment_url: string;
  paid_at: string | null;
  created_at: string;
}

export interface PaymentCreateResponse {
  EC: number;
  EM: string;
  data: PaymentData;
}

export interface MyPayment {
  payment_id: string;
  booking_id: string;
  amount: number;
  payment_method: string;
  payment_status: string;
  transaction_id: string;
  paid_at: string | null;
  created_at: string;
  tour_name: string;
  destination: string;
}

export interface PaymentListParams {
  status?: 'pending' | 'completed' | 'failed';
  limit?: number;
  offset?: number;
}

export interface PaymentListResponse {
  EC: number;
  EM: string;
  data: MyPayment[];
  total: number;
}

export interface PaymentStatusResponse {
  EC: number;
  EM: string;
  data: PaymentData;
}

@Injectable({
  providedIn: 'root'
})
export class PaymentService {
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

  createPayment(payment: PaymentCreateRequest): Observable<PaymentCreateResponse> {
    return this.http.post<PaymentCreateResponse>(
      `${this.apiBaseUrl}/payments/create`,
      payment,
      {
        headers: this.getHeaders()
      }
    );
  }

  getMyPayments(params?: PaymentListParams): Observable<PaymentListResponse> {
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

    return this.http.get<PaymentListResponse>(
      `${this.apiBaseUrl}/payments/my-payments`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  getPaymentByBookingId(bookingId: string): Observable<PaymentStatusResponse> {
    return this.http.get<PaymentStatusResponse>(
      `${this.apiBaseUrl}/payments/booking/${bookingId}`,
      {
        headers: this.getHeaders()
      }
    );
  }

  getPaymentStatus(paymentId: string): Observable<PaymentStatusResponse> {
    return this.http.get<PaymentStatusResponse>(
      `${this.apiBaseUrl}/payments/${paymentId}`,
      {
        headers: this.getHeaders()
      }
    );
  }
}

