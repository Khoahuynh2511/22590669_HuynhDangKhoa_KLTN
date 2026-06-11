import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

export interface FlightItem {
  flight_id: string;
  flight_number: string;
  airline_id: string;
  departure_airport: string;
  arrival_airport: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  aircraft: string;
  economy_price: number;
  business_price: number;
  first_class_price: number;
  economy_seats: number;
  business_seats: number;
  first_class_seats: number;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FlightListResponse {
  EC: number;
  EM: string;
  data: {
    flights: FlightItem[];
    total: number;
  };
}

export interface FlightDetailResponse {
  EC: number;
  EM: string;
  data: FlightItem;
}

export interface AirlineItem {
  airline_id: string;
  name: string;
  logo_url?: string;
  baggage_carry?: string;
  baggage_checked?: string;
}

export interface AirportItem {
  airport_id: string;
  name: string;
  city: string;
  region: string;
  terminals?: string[];
  address?: string;
}

export interface CsvImportResponse {
  EC: number;
  EM: string;
  data: {
    success_count: number;
    fail_count: number;
    errors: { row: number; error: string }[];
  };
}

@Injectable({
  providedIn: 'root'
})
export class AdminFlightService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/admin/flights`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  getFlights(): Observable<FlightListResponse> {
    return this.http.get<FlightListResponse>(this.apiBaseUrl, { headers: this.getHeaders() });
  }

  getFlightById(flightId: string): Observable<FlightDetailResponse> {
    return this.http.get<FlightDetailResponse>(`${this.apiBaseUrl}/${flightId}`, { headers: this.getHeaders() });
  }

  createFlight(data: Partial<FlightItem>): Observable<FlightDetailResponse> {
    return this.http.post<FlightDetailResponse>(this.apiBaseUrl, data, { headers: this.getHeaders() });
  }

  updateFlight(flightId: string, data: Partial<FlightItem>): Observable<FlightDetailResponse> {
    return this.http.put<FlightDetailResponse>(`${this.apiBaseUrl}/${flightId}`, data, { headers: this.getHeaders() });
  }

  deleteFlight(flightId: string): Observable<{ EC: number; EM: string; data: null }> {
    return this.http.delete<{ EC: number; EM: string; data: null }>(`${this.apiBaseUrl}/${flightId}`, { headers: this.getHeaders() });
  }

  updateFlightStatus(flightId: string, status: string): Observable<FlightDetailResponse> {
    return this.http.patch<FlightDetailResponse>(`${this.apiBaseUrl}/${flightId}/status`, { status }, { headers: this.getHeaders() });
  }

  getAirlines(): Observable<{ EC: number; EM: string; data: AirlineItem[] }> {
    return this.http.get<{ EC: number; EM: string; data: AirlineItem[] }>(`${this.apiBaseUrl}/airlines`, { headers: this.getHeaders() });
  }

  getAirports(): Observable<{ EC: number; EM: string; data: AirportItem[] }> {
    return this.http.get<{ EC: number; EM: string; data: AirportItem[] }>(`${this.apiBaseUrl}/airports`, { headers: this.getHeaders() });
  }

  createFlightsFromCSV(csvText: string): Observable<CsvImportResponse> {
    return this.http.post<CsvImportResponse>(`${this.apiBaseUrl}/csv`, { csv_text: csvText }, { headers: this.getHeaders() });
  }
}
