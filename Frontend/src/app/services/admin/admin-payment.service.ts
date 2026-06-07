import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../config.service';

export interface AdminPaymentItem {
  payment_id: string;
  booking_id: string;
  user_id: string;
  amount: number;
  payment_method: string;
  payment_status: string;
  transaction_id: string;
  payment_url?: string;
  paid_at?: string;
  created_at: string;
  tour_name?: string;
  start_date?: string;
  user_name?: string;
  contact_phone?: string;
  contact_email?: string;
  created_by_admin_id?: string;
  refunded_by?: string;
  refunded_at?: string;
  refund_amount?: number;
  refund_reason?: string;
  notes?: string;
}

export interface AdminPaymentListResponse {
  EC: number;
  EM: string;
  data: AdminPaymentItem[];
  total: number;
}

export interface AdminCreatePaymentRequest {
  booking_id: string;
  payment_method: string;
  transaction_id?: string;
  notes?: string;
}

export interface AdminCreatePaymentResponse {
  EC: number;
  EM: string;
  data: AdminPaymentItem;
}

export interface AdminRefundRequest {
  refund_reason: string;
}

export interface AdminRefundResponse {
  EC: number;
  EM: string;
  data: AdminPaymentItem;
}

export interface AdminPaymentListParams {
  status?: string;
  user_id?: string;
  limit?: number;
  offset?: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminPaymentService {
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

  getPayments(params?: AdminPaymentListParams): Observable<AdminPaymentListResponse> {
    let httpParams = new HttpParams();

    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.user_id) {
      httpParams = httpParams.set('user_id', params.user_id);
    }
    if (params?.limit !== undefined) {
      httpParams = httpParams.set('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      httpParams = httpParams.set('offset', params.offset.toString());
    }

    return this.http.get<AdminPaymentListResponse>(
      `${this.apiBaseUrl}/payments/admin/list`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  createPayment(payload: AdminCreatePaymentRequest): Observable<AdminCreatePaymentResponse> {
    return this.http.post<AdminCreatePaymentResponse>(
      `${this.apiBaseUrl}/payments/admin/create`,
      payload,
      {
        headers: this.getHeaders()
      }
    );
  }

  refundPayment(paymentId: string, payload: AdminRefundRequest): Observable<AdminRefundResponse> {
    return this.http.post<AdminRefundResponse>(
      `${this.apiBaseUrl}/payments/admin/${paymentId}/refund`,
      payload,
      {
        headers: this.getHeaders()
      }
    );
  }

  confirmPayment(paymentId: string): Observable<AdminCreatePaymentResponse> {
    return this.http.post<AdminCreatePaymentResponse>(
      `${this.apiBaseUrl}/payments/admin/${paymentId}/confirm`,
      {},
      {
        headers: this.getHeaders()
      }
    );
  }
}
