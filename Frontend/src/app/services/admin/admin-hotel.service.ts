import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './../config.service';

export interface HotelItem {
  hotel_id: string;
  hotel_name: string;
  location: string;
  description?: string;
  address?: string;
  star_rating: number;
  review_score: number;
  review_count: number;
  price: number;
  original_price: number;
  discount: number;
  amenities: string[];
  image_urls: string;
  available_rooms: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HotelListResponse {
  EC: number;
  EM: string;
  data: {
    hotels: HotelItem[];
    total: number;
  };
}

export interface HotelDetailResponse {
  EC: number;
  EM: string;
  data: HotelItem;
}

@Injectable({
  providedIn: 'root'
})
export class AdminHotelService {

  constructor(private http: HttpClient, private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return `${this.configService.getApiUrl()}/admin/hotels`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    });
  }

  getHotels(search?: string, isActive?: boolean): Observable<HotelListResponse> {
    let url = this.apiBaseUrl;
    const params: string[] = [];
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    if (isActive !== undefined) params.push(`is_active=${isActive}`);
    if (params.length) url += '?' + params.join('&');
    return this.http.get<HotelListResponse>(url, { headers: this.getHeaders() });
  }

  getHotelById(hotelId: string): Observable<HotelDetailResponse> {
    return this.http.get<HotelDetailResponse>(`${this.apiBaseUrl}/${hotelId}`, { headers: this.getHeaders() });
  }

  createHotel(data: Partial<HotelItem>): Observable<HotelDetailResponse> {
    return this.http.post<HotelDetailResponse>(this.apiBaseUrl, data, { headers: this.getHeaders() });
  }

  updateHotel(hotelId: string, data: Partial<HotelItem>): Observable<HotelDetailResponse> {
    return this.http.put<HotelDetailResponse>(`${this.apiBaseUrl}/${hotelId}`, data, { headers: this.getHeaders() });
  }

  deleteHotel(hotelId: string): Observable<{ EC: number; EM: string; data: null }> {
    return this.http.delete<{ EC: number; EM: string; data: null }>(`${this.apiBaseUrl}/${hotelId}`, { headers: this.getHeaders() });
  }

  toggleStatus(hotelId: string, isActive: boolean): Observable<HotelDetailResponse> {
    return this.http.patch<HotelDetailResponse>(`${this.apiBaseUrl}/${hotelId}/status`, { is_active: isActive }, { headers: this.getHeaders() });
  }

  createHotelWithImages(formData: FormData): Observable<HotelDetailResponse> {
    const token = localStorage.getItem('access_token');
    const headers = new HttpHeaders({
      'Authorization': token ? `Bearer ${token}` : ''
    });
    // Don't set Content-Type - browser will set multipart/form-data with boundary
    return this.http.post<HotelDetailResponse>(this.apiBaseUrl, formData, { headers });
  }
}
