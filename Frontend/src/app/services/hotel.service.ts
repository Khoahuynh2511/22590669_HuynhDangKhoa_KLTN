import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { ConfigService } from './config.service';
import { StateHotel } from '../shared/models/hotelState.model';

@Injectable({
  providedIn: 'root'
})
export class HotelService {

  private apiBaseUrl: string;

  public hotelState: BehaviorSubject<StateHotel[]> = new BehaviorSubject<StateHotel[]>([]);

  constructor(private http: HttpClient, private configService: ConfigService) {
    this.apiBaseUrl = this.configService.getApiUrl();
  }

  /** Load danh sach khach san tu API */
  loadHotels(location?: string, search?: string): void {
    let url = `${this.apiBaseUrl}/hotels?`;
    const params: string[] = [];
    if (location) params.push(`location=${encodeURIComponent(location)}`);
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    url += params.join('&');

    this.http.get<{ EC: number; EM: string; hotels: StateHotel[] }>(url).subscribe({
      next: (res) => {
        if (res.EC === 0) {
          this.hotelState.next(res.hotels);
        }
      },
      error: (err) => {
        console.error('Error loading hotels:', err);
      }
    });
  }

  /** Lay chi tiet 1 khach san */
  getHotelById(hotelId: string): Observable<{ EC: number; EM: string; hotel: any }> {
    return this.http.get<{ EC: number; EM: string; hotel: any }>(`${this.apiBaseUrl}/hotels/${hotelId}`);
  }

  /** Lay danh sach dia diem */
  getLocations(): Observable<{ EC: number; EM: string; data: string[] }> {
    return this.http.get<{ EC: number; EM: string; data: string[] }>(`${this.apiBaseUrl}/hotels/locations`);
  }

  /** Filter hotels client-side (fallback) */
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

      return matchesName && matchesLocation;
    });
  }
}
