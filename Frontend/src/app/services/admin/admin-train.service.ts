import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

export interface TrainItem {
  train_id: string;
  train_number: string;
  train_type_id: string;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time: string;
  duration_hours: number;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TrainListResponse {
  EC: number;
  EM: string;
  data: {
    trains: TrainItem[];
    total: number;
  };
}

export interface TrainDetailResponse {
  EC: number;
  EM: string;
  data: TrainItem;
}

export interface TrainStationItem {
  station_id: string;
  name: string;
  city: string;
  region: string;
  address?: string;
}

export interface TrainTypeItem {
  type_id: string;
  name: string;
  description?: string;
  speed?: string;
  amenities?: string[];
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
export class AdminTrainService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/admin/trains`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  getTrains(): Observable<TrainListResponse> {
    return this.http.get<TrainListResponse>(this.apiBaseUrl, { headers: this.getHeaders() });
  }

  getTrainById(trainId: string): Observable<TrainDetailResponse> {
    return this.http.get<TrainDetailResponse>(`${this.apiBaseUrl}/${trainId}`, { headers: this.getHeaders() });
  }

  createTrain(data: Partial<TrainItem>): Observable<TrainDetailResponse> {
    return this.http.post<TrainDetailResponse>(this.apiBaseUrl, data, { headers: this.getHeaders() });
  }

  updateTrain(trainId: string, data: Partial<TrainItem>): Observable<TrainDetailResponse> {
    return this.http.put<TrainDetailResponse>(`${this.apiBaseUrl}/${trainId}`, data, { headers: this.getHeaders() });
  }

  deleteTrain(trainId: string): Observable<{ EC: number; EM: string; data: null }> {
    return this.http.delete<{ EC: number; EM: string; data: null }>(`${this.apiBaseUrl}/${trainId}`, { headers: this.getHeaders() });
  }

  updateTrainStatus(trainId: string, status: string): Observable<TrainDetailResponse> {
    return this.http.patch<TrainDetailResponse>(`${this.apiBaseUrl}/${trainId}/status`, { status }, { headers: this.getHeaders() });
  }

  getStations(): Observable<{ EC: number; EM: string; data: TrainStationItem[] }> {
    return this.http.get<{ EC: number; EM: string; data: TrainStationItem[] }>(`${this.apiBaseUrl}/stations`, { headers: this.getHeaders() });
  }

  getTypes(): Observable<{ EC: number; EM: string; data: TrainTypeItem[] }> {
    return this.http.get<{ EC: number; EM: string; data: TrainTypeItem[] }>(`${this.apiBaseUrl}/types`, { headers: this.getHeaders() });
  }

  createTrainsFromCSV(csvText: string): Observable<CsvImportResponse> {
    return this.http.post<CsvImportResponse>(`${this.apiBaseUrl}/csv`, { csv_text: csvText }, { headers: this.getHeaders() });
  }
}
