import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { ConfigService } from './config.service';
import { StateHotel } from '../shared/models/hotelState.model';

export interface HotelListResponse {
  EC: number;
  EM: string;
  total: number;
  hotels: StateHotel[];
}

@Injectable({
  providedIn: 'root'
})
export class HotelService {

  private apiBaseUrl: string;

  public hotelState: BehaviorSubject<StateHotel[]> = new BehaviorSubject<StateHotel[]>([]);
  public hotelTotalState: BehaviorSubject<number> = new BehaviorSubject<number>(0);

  constructor(private http: HttpClient, private configService: ConfigService) {
    this.apiBaseUrl = this.configService.getApiUrl();
  }

  loadHotels(location?: string, search?: string, limit?: number, offset?: number): void {
    const params: string[] = [];
    if (location) params.push(`location=${encodeURIComponent(location)}`);
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    if (limit !== undefined) params.push(`limit=${limit}`);
    if (offset !== undefined) params.push(`offset=${offset}`);

    const query = params.length ? `?${params.join('&')}` : '';
    const url = `${this.apiBaseUrl}/hotels${query}`;

    this.http.get<HotelListResponse>(url).subscribe({
      next: (res) => {
        if (res.EC === 0) {
          this.hotelState.next(res.hotels || []);
          this.hotelTotalState.next(res.total ?? res.hotels?.length ?? 0);
        }
      },
      error: (err) => {
        console.error('Error loading hotels:', err);
      }
    });
  }

  getHotelById(hotelId: string): Observable<{ EC: number; EM: string; hotel: any }> {
    return this.http.get<{ EC: number; EM: string; hotel: any }>(`${this.apiBaseUrl}/hotels/${hotelId}`);
  }

  getLocations(): Observable<{ EC: number; EM: string; data: string[] }> {
    return this.http.get<{ EC: number; EM: string; data: string[] }>(`${this.apiBaseUrl}/hotels/locations`);
  }

  searchHotels(search: string, limit: number = 5): Observable<HotelListResponse> {
    const params: string[] = [];
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    params.push(`limit=${limit}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return this.http.get<HotelListResponse>(`${this.apiBaseUrl}/hotels${query}`);
  }

  public filterHotels(
    name?: string,
    location?: string,
    priceRange?: { min: number; max: number }
  ): StateHotel[] {
    const hotels = this.hotelState.getValue();

    return hotels.filter((hotel) => {
      const matchesName = name ? hotel.hotel_name.toLowerCase().includes(name.toLowerCase()) : true;
      const matchesLocation = location ? hotel.location.toLowerCase().includes(location.toLowerCase()) : true;
      const matchesPrice =
        priceRange && priceRange.min !== undefined && priceRange.max !== undefined
          ? hotel.price >= priceRange.min && hotel.price <= priceRange.max
          : true;

      return matchesName && matchesLocation && matchesPrice;
    });
  }
}
