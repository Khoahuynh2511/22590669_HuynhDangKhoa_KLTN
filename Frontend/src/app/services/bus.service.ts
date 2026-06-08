import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';

export interface BusStation {
  code: string;
  name: string;
  city: string;
  region: string;
  address: string;
}

export interface BusType {
  name: string;
  description: string;
  capacity: number;
  amenities: string[];
}

export interface BusSeatType {
  name: string;
  code: string;
  price_multiplier: number;
  description: string;
}

export interface BusSeatPrice {
  name: string;
  code: string;
  price: number;
  description: string;
}

export interface Bus {
  bus_id: string;
  bus_number: string;
  company: { code: string; name: string; logo: string; phone: string; rating: number };
  bus_type: { code: string; name: string; description: string; capacity: number; amenities: string[] };
  departure: { station: string; city: string; code: string; address: string; scheduled: string; date: string; time: string };
  arrival: { station: string; city: string; code: string; address: string; scheduled: string; date: string; time: string };
  duration_hours: number;
  duration_formatted: string;
  seats: { [key: string]: BusSeatPrice };
  availability: { [key: string]: number };
  total_seats: number;
  available_seats: number;
  status: string;
  currency: string;
}

export interface BusSearchResponse {
  EC: number;
  EM: string;
  data: {
    departure: { code: string; city: string; station: string };
    arrival: { code: string; city: string; station: string };
    date: string;
    total: number;
    buses: Bus[];
    seat_types: { [key: string]: BusSeatType };
  } | null;
}

@Injectable({
  providedIn: 'root'
})
export class BusService {

  constructor(private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  async getStations(): Promise<{ EC: number; EM: string; data: BusStation[] }> {
    const response = await fetch(`${this.apiBaseUrl}/buses/stations`);
    return response.json();
  }

  async getBusTypes(): Promise<{ EC: number; EM: string; data: { bus_types: { [key: string]: BusType }; seat_types: { [key: string]: BusSeatType } } }> {
    const response = await fetch(`${this.apiBaseUrl}/buses/types`);
    return response.json();
  }

  async searchBuses(departure: string, arrival: string, date?: string, limit: number = 10): Promise<BusSearchResponse> {
    const params = new URLSearchParams({ departure, arrival });
    if (date) params.append('date', date);
    if (limit) params.append('limit', limit.toString());
    const response = await fetch(`${this.apiBaseUrl}/buses/search?${params.toString()}`);
    return response.json();
  }
}
