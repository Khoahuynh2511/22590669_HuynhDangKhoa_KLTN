import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { BusService, Bus, BusStation } from '../../services/bus.service';

@Component({
  selector: 'app-buses',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './buses.component.html',
  styleUrl: './buses.component.scss'
})
export class BusesComponent implements OnInit {
  departure = '';
  destination = '';
  departureDate = '';
  passengers = 1;

  stations: BusStation[] = [];
  searchResults: Bus[] = [];
  isSearching = false;
  hasSearched = false;
  errorMessage = '';

  popularRoutes = [
    { from: 'BXSG', to: 'BXHN', fromCity: 'TP. Hồ Chí Minh', toCity: 'Hà Nội', duration: '36h', price: 650000 },
    { from: 'BXSG', to: 'BXDL', fromCity: 'TP. Hồ Chí Minh', toCity: 'Đà Lạt', duration: '7h', price: 300000 },
    { from: 'BXSG', to: 'BXNT', fromCity: 'TP. Hồ Chí Minh', toCity: 'Nha Trang', duration: '10h', price: 280000 },
    { from: 'BXHN', to: 'BXDN', fromCity: 'Hà Nội', toCity: 'Đà Nẵng', duration: '18h', price: 400000 },
    { from: 'BXSG', to: 'BXVL', fromCity: 'TP. Hồ Chí Minh', toCity: 'Vũng Tàu', duration: '2h30', price: 150000 },
    { from: 'BXSG', to: 'BXPT', fromCity: 'TP. Hồ Chí Minh', toCity: 'Phan Thiết', duration: '4h30', price: 180000 },
  ];

  constructor(private busService: BusService, private router: Router) {}

  async ngOnInit() {
    try {
      const res = await this.busService.getStations();
      if (res.EC === 0) this.stations = res.data;
    } catch (e) { console.error(e); }
  }

  async onSearch() {
    if (!this.departure || !this.destination) {
      this.errorMessage = 'Vui lòng chọn bến xe đi và bến xe đến';
      this.hasSearched = true;
      return;
    }
    if (this.departure === this.destination) {
      this.errorMessage = 'Bến xe đi và bến xe đến không được trùng nhau';
      this.hasSearched = true;
      return;
    }

    this.isSearching = true;
    this.hasSearched = true;
    this.errorMessage = '';

    try {
      const res = await this.busService.searchBuses(this.departure, this.destination, this.departureDate || undefined);
      if (res.EC === 0 && res.data) {
        this.searchResults = res.data.buses;
      } else {
        this.errorMessage = res.EM || 'Không tìm thấy chuyến xe';
        this.searchResults = [];
      }
    } catch (e: any) {
      this.errorMessage = 'Lỗi kết nối. Vui lòng thử lại.';
      this.searchResults = [];
    } finally {
      this.isSearching = false;
    }
  }

  selectRoute(route: any) {
    this.departure = route.from;
    this.destination = route.to;
    this.onSearch();
  }

  openAIChat() {
    this.router.navigate(['/chat-room']);
  }

  getLowestPrice(bus: Bus): number {
    const prices = Object.values(bus.seats).map(s => s.price);
    return Math.min(...prices);
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }
}
