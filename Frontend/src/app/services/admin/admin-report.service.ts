import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../config.service';

// Revenue Report
export interface RevenuePeriod {
  period_start: string;
  period_end: string;
  total_revenue: number;
  total_bookings: number;
}

export interface RevenueReportResponse {
  EC: number;
  EM: string;
  period_type: string;
  data: RevenuePeriod[];
  total_revenue: number;
  total_bookings: number;
}

// People by Price Range
export interface PriceRangeData {
  price_range: string;
  min_price: number;
  max_price: number;
  total_people: number;
  total_bookings: number;
}

export interface PeopleByPriceRangeResponse {
  EC: number;
  EM: string;
  period_type: string;
  period_start: string;
  period_end: string;
  data: PriceRangeData[];
  total_people_all_ranges: number;
  total_bookings_all_ranges: number;
}

@Injectable({
  providedIn: 'root'
})
export class ReportService {
  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/reports`;
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
   * GET /api/v1/reports/revenue
   * Get revenue report by week or month
   */
  getRevenueReport(params: {
    period_type: 'week' | 'month';
    start_date?: string;
    end_date?: string;
    num_periods?: number;
  }): Observable<RevenueReportResponse> {
    let httpParams = new HttpParams()
      .set('period_type', params.period_type);

    if (params.start_date) httpParams = httpParams.set('start_date', params.start_date);
    if (params.end_date) httpParams = httpParams.set('end_date', params.end_date);
    if (params.num_periods) httpParams = httpParams.set('num_periods', params.num_periods.toString());

    return this.http.get<RevenueReportResponse>(
      `${this.apiBaseUrl}/revenue`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * GET /api/v1/reports/people-by-price-range/week
   * Get people by price range for a week
   */
  getPeopleByPriceRangeWeek(target_date?: string): Observable<PeopleByPriceRangeResponse> {
    let httpParams = new HttpParams();
    if (target_date) httpParams = httpParams.set('target_date', target_date);

    return this.http.get<PeopleByPriceRangeResponse>(
      `${this.apiBaseUrl}/people-by-price-range/week`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * GET /api/v1/reports/people-by-price-range/month
   * Get people by price range for a month
   */
  getPeopleByPriceRangeMonth(target_date?: string): Observable<PeopleByPriceRangeResponse> {
    let httpParams = new HttpParams();
    if (target_date) httpParams = httpParams.set('target_date', target_date);

    return this.http.get<PeopleByPriceRangeResponse>(
      `${this.apiBaseUrl}/people-by-price-range/month`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }

  /**
   * GET /api/v1/reports/people-by-price-range
   * Get people by price range (unified API)
   */
  getPeopleByPriceRange(params: {
    period_type: 'week' | 'month';
    target_date?: string;
  }): Observable<PeopleByPriceRangeResponse> {
    let httpParams = new HttpParams()
      .set('period_type', params.period_type);

    if (params.target_date) httpParams = httpParams.set('target_date', params.target_date);

    return this.http.get<PeopleByPriceRangeResponse>(
      `${this.apiBaseUrl}/people-by-price-range`,
      {
        headers: this.getHeaders(),
        params: httpParams
      }
    );
  }
}
