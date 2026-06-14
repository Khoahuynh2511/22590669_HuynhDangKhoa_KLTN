import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { BusService, Bus, BusStation } from '../../services/bus.service';
import { PaginationComponent } from '../../components/pagination/pagination.component';
import { paginateSlice } from '../../shared/utils/pagination.util';
import { getMinSearchDate, validateSearchDepartureDate } from '../../shared/utils/date-search.util';

@Component({
  selector: 'app-buses',
  standalone: true,
  imports: [CommonModule, FormsModule, PaginationComponent],
  templateUrl: './buses.component.html',
  styleUrl: './buses.component.scss'
})
export class BusesComponent implements OnInit {
  departure = '';
  destination = '';
  departureDate = '';
  passengers = 1;

  stations: BusStation[] = [];
  allSearchResults: Bus[] = [];
  paginatedResults: Bus[] = [];
  isSearching = false;
  hasSearched = false;
  errorMessage = '';

  currentPage = 1;
  pageSize = 5;
  totalResults = 0;

  sortBy: 'price' | 'departure' | 'duration' = 'price';
  minDate = getMinSearchDate();
  dateFieldError: 'departure' | '' = '';

  popularRoutes = [
    { from: 'BXSG', to: 'BXHN', fromCity: 'TP. Hồ Chí Minh', toCity: 'Hà Nội', duration: '36h', price: 650000 },
    { from: 'BXSG', to: 'BXDL', fromCity: 'TP. Hồ Chí Minh', toCity: 'Đà Lạt', duration: '7h', price: 300000 },
    { from: 'BXSG', to: 'BXNT', fromCity: 'TP. Hồ Chí Minh', toCity: 'Nha Trang', duration: '10h', price: 280000 },
    { from: 'BXHN', to: 'BXDN', fromCity: 'Hà Nội', toCity: 'Đà Nẵng', duration: '18h', price: 400000 },
    { from: 'BXSG', to: 'BXVL', fromCity: 'TP. Hồ Chí Minh', toCity: 'Vũng Tàu', duration: '2h30', price: 150000 },
    { from: 'BXSG', to: 'BXPT', fromCity: 'TP. Hồ Chí Minh', toCity: 'Phan Thiết', duration: '4h30', price: 180000 },
  ];

  constructor(
    private busService: BusService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  async ngOnInit() {
    try {
      const res = await this.busService.getStations();
      if (res.EC === 0) this.stations = res.data;

      this.route.queryParams.subscribe(params => {
        let hasParams = false;
        if (params['departure']) {
          this.departure = params['departure'];
          hasParams = true;
        }
        if (params['destination']) {
          this.destination = params['destination'];
          hasParams = true;
        }
        if (params['date']) {
          this.departureDate = params['date'];
        }
        if (params['passengers']) {
          this.passengers = parseInt(params['passengers']) || 1;
        }

        if (hasParams && this.departure && this.destination) {
          this.onSearch();
        }
      });
    } catch (e) { console.error(e); }
  }

  swapStations() {
    const temp = this.departure;
    this.departure = this.destination;
    this.destination = temp;
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

    const departureDateError = validateSearchDepartureDate(this.departureDate);
    if (departureDateError) {
      this.errorMessage = departureDateError;
      this.dateFieldError = 'departure';
      this.hasSearched = true;
      return;
    }

    this.isSearching = true;
    this.hasSearched = true;
    this.errorMessage = '';
    this.dateFieldError = '';
    this.currentPage = 1;

    try {
      const res = await this.busService.searchBuses(this.departure, this.destination, this.departureDate, 20);
      if (res.EC === 0 && res.data) {
        this.allSearchResults = res.data.buses;
        this.totalResults = res.data.total ?? res.data.buses.length;
        this.sortResults();
      } else {
        this.errorMessage = res.EM || 'Không tìm thấy chuyến xe';
        this.allSearchResults = [];
        this.paginatedResults = [];
        this.totalResults = 0;
      }
    } catch (e: any) {
      this.errorMessage = 'Lỗi kết nối. Vui lòng thử lại.';
      this.allSearchResults = [];
      this.paginatedResults = [];
      this.totalResults = 0;
    } finally {
      this.isSearching = false;
    }
  }

  sortResults() {
    if (this.sortBy === 'price') {
      this.allSearchResults.sort((a, b) => this.getLowestPrice(a) - this.getLowestPrice(b));
    } else if (this.sortBy === 'departure') {
      this.allSearchResults.sort((a, b) => a.departure.time.localeCompare(b.departure.time));
    } else if (this.sortBy === 'duration') {
      this.allSearchResults.sort((a, b) => a.duration_hours - b.duration_hours);
    }
    this.updatePaginatedResults();
  }

  onPageChange(page: number): void {
    this.currentPage = page;
    this.updatePaginatedResults();
    window.scrollTo({ top: 300, behavior: 'smooth' });
  }

  private updatePaginatedResults(): void {
    this.totalResults = this.allSearchResults.length;
    this.paginatedResults = paginateSlice(this.allSearchResults, this.currentPage, this.pageSize);
  }

  selectRoute(route: any) {
    this.departure = route.from;
    this.destination = route.to;
    if (!this.departureDate) {
      this.departureDate = this.minDate;
    }
    this.onSearch();
  }

  bookBus(bus: Bus) {
    this.router.navigate(['/bus-booking', bus.bus_id], {
      state: { bus: bus }
    });
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
