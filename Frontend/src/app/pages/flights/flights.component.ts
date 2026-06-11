import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { FlightService, Airport, Flight } from '../../services/flight.service';

@Component({
  selector: 'app-flights',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './flights.component.html',
  styleUrl: './flights.component.scss'
})
export class FlightsComponent implements OnInit {
  tripType: 'one-way' | 'round-trip' = 'round-trip';
  departure = '';
  destination = '';
  departureDate = '';
  returnDate = '';
  passengers = 1;

  airports: Airport[] = [];
  searchResults: Flight[] = [];
  isSearching = false;
  hasSearched = false;
  errorMessage = '';

  // Sort
  sortBy: 'price' | 'departure' | 'duration' = 'price';

  // Expose Math to template
  Math = Math;

  popularRoutes = [
    { from: 'SGN', to: 'HAN', fromCity: 'TP. Hồ Chí Minh', toCity: 'Hà Nội', airline: 'Vietnam Airlines, VietJet', duration: '2h 10m', price: 1590000 },
    { from: 'SGN', to: 'DAD', fromCity: 'TP. Hồ Chí Minh', toCity: 'Đà Nẵng', airline: 'Bamboo Airways, VietJet', duration: '1h 20m', price: 990000 },
    { from: 'HAN', to: 'PQC', fromCity: 'Hà Nội', toCity: 'Phú Quốc', airline: 'Vietnam Airlines', duration: '2h 20m', price: 1890000 },
    { from: 'HAN', to: 'DLI', fromCity: 'Hà Nội', toCity: 'Đà Lạt', airline: 'VietJet Air', duration: '1h 50m', price: 1290000 },
    { from: 'SGN', to: 'CXR', fromCity: 'TP. Hồ Chí Minh', toCity: 'Nha Trang', airline: 'Bamboo Airways', duration: '1h 10m', price: 890000 },
    { from: 'DAD', to: 'SGN', fromCity: 'Đà Nẵng', toCity: 'TP. Hồ Chí Minh', airline: 'Vietnam Airlines', duration: '1h 20m', price: 1090000 },
  ];

  constructor(private flightService: FlightService, private router: Router) {}

  async ngOnInit() {
    try {
      const res = await this.flightService.getAirports();
      if (res.EC === 0) this.airports = res.data;
    } catch (e) {
      console.error('Error loading airports:', e);
    }
  }

  swapAirports() {
    const temp = this.departure;
    this.departure = this.destination;
    this.destination = temp;
  }

  async onSearch() {
    if (!this.departure || !this.destination) {
      this.errorMessage = 'Vui lòng chọn sân bay đi và sân bay đến';
      this.hasSearched = true;
      return;
    }
    if (this.departure === this.destination) {
      this.errorMessage = 'Sân bay đi và sân bay đến không được trùng nhau';
      this.hasSearched = true;
      return;
    }

    this.isSearching = true;
    this.hasSearched = true;
    this.errorMessage = '';

    try {
      const res = await this.flightService.searchFlights(this.departure, this.destination, this.departureDate || undefined);
      if (res.EC === 0 && res.data) {
        this.searchResults = res.data.flights;
        this.sortResults();
      } else {
        this.errorMessage = res.EM || 'Không tìm thấy chuyến bay';
        this.searchResults = [];
      }
    } catch (e: any) {
      this.errorMessage = 'Lỗi kết nối. Vui lòng thử lại.';
      this.searchResults = [];
    } finally {
      this.isSearching = false;
    }
  }

  sortResults() {
    if (this.sortBy === 'price') {
      this.searchResults.sort((a, b) => this.getLowestPrice(a) - this.getLowestPrice(b));
    } else if (this.sortBy === 'departure') {
      this.searchResults.sort((a, b) => a.departure.time.localeCompare(b.departure.time));
    } else if (this.sortBy === 'duration') {
      this.searchResults.sort((a, b) => a.duration_minutes - b.duration_minutes);
    }
  }

  selectRoute(route: any) {
    this.departure = route.from;
    this.destination = route.to;
    this.onSearch();
  }

  bookFlight(flight: Flight) {
    this.router.navigate(['/flight-booking', flight.flight_id], {
      state: { flight: flight }
    });
  }

  openAIChat() {
    this.router.navigate(['/chat-room']);
  }

  getLowestPrice(flight: Flight): number {
    return Math.min(flight.price.economy, flight.price.business, flight.price.first_class);
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }
}
