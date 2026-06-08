import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TrainService, Train, TrainStation } from '../../services/train.service';

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

  popularRoutes = [
    { from: 'HNO', to: 'SGO', fromCity: 'Ha Noi', toCity: 'Ho Chi Minh', duration: '33h', price: 800000 },
    { from: 'HNO', to: 'DNA', fromCity: 'Ha Noi', toCity: 'Da Nang', duration: '16h', price: 450000 },
    { from: 'HNO', to: 'LCA', fromCity: 'Ha Noi', toCity: 'Lao Cai (Sapa)', duration: '8h', price: 250000 },
    { from: 'SGO', to: 'NTR', fromCity: 'Ho Chi Minh', toCity: 'Nha Trang', duration: '8h', price: 300000 },
    { from: 'SGO', to: 'PTA', fromCity: 'Ho Chi Minh', toCity: 'Phan Thiet', duration: '4h', price: 120000 },
    { from: 'DNA', to: 'HUE', fromCity: 'Da Nang', toCity: 'Hue', duration: '2h30', price: 80000 },
  ];

  constructor(private trainService: TrainService, private router: Router) {}

  async ngOnInit() {
    try {
      const res = await this.trainService.getStations();
      if (res.EC === 0) this.stations = res.data;
    } catch (e) { console.error(e); }
  }

  async onSearch() {
    if (!this.departure || !this.destination) { this.errorMessage = 'Vui long chon ga di va ga den'; this.hasSearched = true; return; }
    this.isSearching = true; this.hasSearched = true; this.errorMessage = '';
    try {
      const res = await this.trainService.searchTrains(this.departure, this.destination, this.departureDate || undefined);
      if (res.EC === 0 && res.data) { this.searchResults = res.data.trains; }
      else { this.errorMessage = res.EM; this.searchResults = []; }
    } catch (e: any) { this.errorMessage = 'Loi ket noi'; this.searchResults = []; }
    finally { this.isSearching = false; }
  }

  selectRoute(route: any) { this.departure = route.from; this.destination = route.to; this.onSearch(); }
  openAIChat() { this.router.navigate(['/chat-room']); }
  getLowestPrice(train: Train): number {
    const prices = Object.values(train.seats).map(s => s.price);
    return Math.min(...prices);
  }
  formatPrice(price: number): string { return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price); }
}
