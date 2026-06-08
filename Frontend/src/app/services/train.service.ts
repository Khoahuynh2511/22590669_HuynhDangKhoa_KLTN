import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';

export interface TrainStation {
  code: string;
  name: string;
  city: string;
  region: string;
  address: string;
}

export interface TrainType {
  name: string;
  description: string;
  speed: string;
  amenities: string[];
}

export interface SeatType {
  name: string;
  code: string;
  price_multiplier: number;
  description: string;
}

export interface TrainSeatPrice {
  name: string;
  code: string;
  price: number;
  description: string;
}

export interface Train {
  train_id: string;
  train_number: string;
  train_type: { code: string; name: string; description: string; amenities: string[] };
  departure: { station: string; city: string; code: string; address: string; scheduled: string; date: string; time: string };
  arrival: { station: string; city: string; code: string; address: string; scheduled: string; date: string; time: string };
  duration_hours: number;
  duration_formatted: string;
  seats: { [key: string]: TrainSeatPrice };
  availability: { [key: string]: number };
  status: string;
  currency: string;
}

export interface TrainSearchResponse {
  EC: number;
  EM: string;
  data: {
    departure: { code: string; city: string; station: string };
    arrival: { code: string; city: string; station: string };
    date: string;
    total: number;
    trains: Train[];
    seat_types: { [key: string]: SeatType };
  } | null;
}

@Injectable({
  providedIn: 'root'
})
export class TrainService {

  constructor(private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  async getStations(): Promise<{ EC: number; EM: string; data: TrainStation[] }> {
    const response = await fetch(`${this.apiBaseUrl}/trains/stations`);
    return response.json();
  }

  async getTrainTypes(): Promise<{ EC: number; EM: string; data: { train_types: { [key: string]: TrainType }; seat_types: { [key: string]: SeatType } } }> {
    const response = await fetch(`${this.apiBaseUrl}/trains/types`);
    return response.json();
  }

  async searchTrains(departure: string, arrival: string, date?: string, limit: number = 10): Promise<TrainSearchResponse> {
    const params = new URLSearchParams({ departure, arrival });
    if (date) params.append('date', date);
    if (limit) params.append('limit', limit.toString());
    const response = await fetch(`${this.apiBaseUrl}/trains/search?${params.toString()}`);
    return response.json();
  }
}
