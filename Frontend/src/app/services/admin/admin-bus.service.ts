import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

export interface BusItem {
  bus_id: string;
  bus_number: string;
  company_id: string;
  bus_type_id: string;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time: string;
  duration_hours: number;
  total_seats: number;
  available_seats: number;
  base_price: number;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BusListResponse {
  EC: number;
  EM: string;
  data: {
    buses: BusItem[];
    total: number;
  };
}

export interface BusDetailResponse {
  EC: number;
  EM: string;
  data: BusItem;
}

export interface CreateBusRequest {
  bus_number: string;
  company_id: string;
  bus_type_id: string;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time: string;
  duration_hours: number;
  total_seats: number;
  available_seats: number;
  base_price: number;
  status?: string;
}

export interface CompanyItem {
  company_id: string;
  name: string;
  logo_url?: string;
  phone?: string;
  amenities?: string[];
  rating?: number;
}

export interface StationItem {
  station_id: string;
  name: string;
  city: string;
  region: string;
  address?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AdminBusService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/admin/buses`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  getBuses(): Observable<BusListResponse> {
    return this.http.get<BusListResponse>(this.apiBaseUrl, { headers: this.getHeaders() });
  }

  getBusById(busId: string): Observable<BusDetailResponse> {
    return this.http.get<BusDetailResponse>(`${this.apiBaseUrl}/${busId}`, { headers: this.getHeaders() });
  }

  createBus(data: CreateBusRequest): Observable<BusDetailResponse> {
    return this.http.post<BusDetailResponse>(this.apiBaseUrl, data, { headers: this.getHeaders() });
  }

  updateBus(busId: string, data: Partial<BusItem>): Observable<BusDetailResponse> {
    return this.http.put<BusDetailResponse>(`${this.apiBaseUrl}/${busId}`, data, { headers: this.getHeaders() });
  }

  deleteBus(busId: string): Observable<{ EC: number; EM: string; data: null }> {
    return this.http.delete<{ EC: number; EM: string; data: null }>(`${this.apiBaseUrl}/${busId}`, { headers: this.getHeaders() });
  }

  updateBusStatus(busId: string, status: string): Observable<BusDetailResponse> {
    return this.http.patch<BusDetailResponse>(`${this.apiBaseUrl}/${busId}/status`, { status }, { headers: this.getHeaders() });
  }

  getCompanies(): Observable<{ EC: number; EM: string; data: CompanyItem[] }> {
    return this.http.get<{ EC: number; EM: string; data: CompanyItem[] }>(`${this.apiBaseUrl}/companies`, { headers: this.getHeaders() });
  }

  getStations(): Observable<{ EC: number; EM: string; data: StationItem[] }> {
    return this.http.get<{ EC: number; EM: string; data: StationItem[] }>(`${this.apiBaseUrl}/stations`, { headers: this.getHeaders() });
  }
}
