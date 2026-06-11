import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TrainService, Train, TrainStation } from '../../services/train.service';

// Re-export Train for template usage
export type { Train };

interface SeatPriceEntry {
  code: string;
  name: string;
  price: number;
  available: number;
}

@Component({
  selector: 'app-trains',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './trains.component.html'
})
export class TrainsComponent implements OnInit {
  departure = '';
  destination = '';
  departureDate = '';
  passengers = 1;
  stations: TrainStation[] = [];
  searchResults: Train[] = [];
  isSearching = false;
  hasSearched = false;
  errorMessage = '';

  // Sort
  sortBy: 'price' | 'departure' | 'duration' = 'price';

  popularRoutes = [
    { from: 'HNO', to: 'SGO', fromCity: 'Hà Nội', toCity: 'TP. Hồ Chí Minh', duration: '33h', price: 800000 },
    { from: 'HNO', to: 'DNA', fromCity: 'Hà Nội', toCity: 'Đà Nẵng', duration: '16h', price: 450000 },
    { from: 'HNO', to: 'LCA', fromCity: 'Hà Nội', toCity: 'Lào Cai (Sapa)', duration: '8h', price: 250000 },
    { from: 'SGO', to: 'NTR', fromCity: 'TP. Hồ Chí Minh', toCity: 'Nha Trang', duration: '8h', price: 300000 },
    { from: 'SGO', to: 'PTA', fromCity: 'TP. Hồ Chí Minh', toCity: 'Phan Thiết', duration: '4h', price: 120000 },
    { from: 'DNA', to: 'HUE', fromCity: 'Đà Nẵng', toCity: 'Huế', duration: '2h30', price: 80000 },
  ];

  constructor(private trainService: TrainService, private router: Router) {}

  async ngOnInit() {
    try {
      const res = await this.trainService.getStations();
      if (res.EC === 0) this.stations = res.data;
    } catch (e) { console.error(e); }
  }

  swapStations() {
    const temp = this.departure;
    this.departure = this.destination;
    this.destination = temp;
  }

  async onSearch() {
    if (!this.departure || !this.destination) { this.errorMessage = 'Vui lòng chọn ga đi và ga đến'; this.hasSearched = true; return; }
    if (this.departure === this.destination) { this.errorMessage = 'Ga đi và ga đến không được trùng nhau'; this.hasSearched = true; return; }
    this.isSearching = true; this.hasSearched = true; this.errorMessage = '';
    try {
      const res = await this.trainService.searchTrains(this.departure, this.destination, this.departureDate || undefined);
      if (res.EC === 0 && res.data) {
        this.searchResults = res.data.trains;
        this.sortResults();
      }
      else { this.errorMessage = res.EM; this.searchResults = []; }
    } catch (e: any) { this.errorMessage = 'Lỗi kết nối. Vui lòng thử lại.'; this.searchResults = []; }
    finally { this.isSearching = false; }
  }

  sortResults() {
    if (this.sortBy === 'price') {
      this.searchResults.sort((a, b) => this.getLowestPrice(a) - this.getLowestPrice(b));
    } else if (this.sortBy === 'departure') {
      this.searchResults.sort((a, b) => a.departure.time.localeCompare(b.departure.time));
    } else if (this.sortBy === 'duration') {
      this.searchResults.sort((a, b) => a.duration_hours - b.duration_hours);
    }
  }

  selectRoute(route: any) { this.departure = route.from; this.destination = route.to; this.onSearch(); }

  bookTrain(train: Train) {
    this.router.navigate(['/train-booking', train.train_id], {
      state: { train: train }
    });
  }

  openAIChat() { this.router.navigate(['/chat-room']); }

  getLowestPrice(train: Train): number {
    const prices = Object.values(train.seats).map(s => s.price);
    return Math.min(...prices);
  }

  getSeatPriceEntries(train: Train): SeatPriceEntry[] {
    const entries: SeatPriceEntry[] = [];
    for (const [code, seat] of Object.entries(train.seats)) {
      entries.push({
        code,
        name: seat.name,
        price: seat.price,
        available: train.availability[code] ?? 0
      });
    }
    return entries;
  }

  formatPrice(price: number): string { return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price); }
}
