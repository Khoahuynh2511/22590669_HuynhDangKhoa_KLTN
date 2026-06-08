import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';

export interface Airport {
  code: string;
  name: string;
  city: string;
  region: string;
  terminals: string[];
}

export interface Airline {
  code: string;
  name: string;
  logo: string;
  baggage_checked: string;
  baggage_carry: string;
}

export interface Flight {
  flight_id: string;
  flight_number: string;
  airline: { code: string; name: string; logo: string };
  departure: { airport: string; city: string; iata: string; terminal: string; scheduled: string; date: string; time: string };
  arrival: { airport: string; city: string; iata: string; terminal: string; scheduled: string; date: string; time: string };
  duration_minutes: number;
  duration_formatted: string;
  price: { economy: number; business: number; first_class: number; currency: string };
  available_seats: number;
  aircraft: string;
  status: string;
  baggage: { carry_on: string; checked: string };
}

export interface FlightSearchResponse {
  EC: number;
  EM: string;
  data: {
    departure: { iata: string; city: string; airport: string };
    arrival: { iata: string; city: string; airport: string };
    date: string;
    total: number;
    flights: Flight[];
  } | null;
}

@Injectable({
  providedIn: 'root'
})
export class FlightService {

  constructor(private configService: ConfigService) {}

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  async getAirports(): Promise<{ EC: number; EM: string; data: Airport[] }> {
    const response = await fetch(`${this.apiBaseUrl}/flights/airports`);
    return response.json();
  }

  async getAirlines(): Promise<{ EC: number; EM: string; data: Airline[] }> {
    const response = await fetch(`${this.apiBaseUrl}/flights/airlines`);
    return response.json();
  }

  async searchFlights(departure: string, arrival: string, date?: string, limit: number = 10): Promise<FlightSearchResponse> {
    const params = new URLSearchParams({ departure, arrival });
    if (date) params.append('date', date);
    if (limit) params.append('limit', limit.toString());
    const response = await fetch(`${this.apiBaseUrl}/flights/search?${params.toString()}`);
    return response.json();
  }
}
