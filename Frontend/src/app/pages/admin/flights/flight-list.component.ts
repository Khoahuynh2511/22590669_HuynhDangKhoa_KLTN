import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminFlightService, FlightItem, AirlineItem, AirportItem } from '../../../services/admin/admin-flight.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

@Component({
  selector: 'app-flight-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './flight-list.component.html',
  styleUrl: './flight-list.component.scss'
})
export class FlightListComponent implements OnInit {
  flights: FlightItem[] = [];
  filteredFlights: FlightItem[] = [];
  isLoading = true;

  // Modal states
  showAddModal = false;
  showEditModal = false;

  // Current flight being edited
  currentFlight: Partial<FlightItem> = {};

  // Search & filter
  searchTerm = '';
  statusFilter = '';

  // Reference data
  airlines: AirlineItem[] = [];
  airports: AirportItem[] = [];

  // Form
  formData: any = {};

  statusList = ['scheduled', 'boarding', 'departed', 'arrived', 'cancelled'];

  constructor(
    private flightService: AdminFlightService,
    private dialogService: AdminDialogService
  ) {}

  async ngOnInit() {
    await this.loadFlights();
    this.loadReferenceData();
  }

  async loadFlights() {
    this.isLoading = true;
    try {
      const res = await this.flightService.getFlights().toPromise();
      if (res?.EC === 0) {
        this.flights = res.data.flights || [];
        this.applyFilters();
      }
    } catch (e) {
      console.error('Error loading flights:', e);
    } finally {
      this.isLoading = false;
    }
  }

  loadReferenceData() {
    this.flightService.getAirlines().subscribe({
      next: (res) => { if (res.EC === 0) this.airlines = res.data || []; },
      error: () => {}
    });
    this.flightService.getAirports().subscribe({
      next: (res) => { if (res.EC === 0) this.airports = res.data || []; },
      error: () => {}
    });
  }

  applyFilters() {
    this.filteredFlights = this.flights.filter(flight => {
      const matchSearch = !this.searchTerm ||
        flight.flight_number?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        flight.flight_id?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchStatus = !this.statusFilter || flight.status === this.statusFilter;
      return matchSearch && matchStatus;
    });
  }

  // Add modal
  openAddModal() {
    this.formData = {
      flight_number: '',
      airline_id: '',
      departure_airport: '',
      arrival_airport: '',
      departure_time: '',
      arrival_time: '',
      duration_minutes: 120,
      aircraft: 'Airbus A321',
      economy_price: 1500000,
      business_price: 3750000,
      first_class_price: 6000000,
      economy_seats: 150,
      business_seats: 20,
      first_class_seats: 8,
      status: 'scheduled'
    };
    this.showAddModal = true;
  }

  async saveFlight() {
    try {
      const res = await this.flightService.createFlight(this.formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo chuyến bay thành công!');
        this.showAddModal = false;
        await this.loadFlights();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo chuyến bay thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Edit modal
  openEditModal(flight: FlightItem) {
    this.currentFlight = { ...flight };
    this.formData = {
      flight_number: flight.flight_number,
      airline_id: flight.airline_id,
      departure_airport: flight.departure_airport,
      arrival_airport: flight.arrival_airport,
      departure_time: flight.departure_time?.slice(0, 16),
      arrival_time: flight.arrival_time?.slice(0, 16),
      duration_minutes: flight.duration_minutes,
      aircraft: flight.aircraft,
      economy_price: flight.economy_price,
      business_price: flight.business_price,
      first_class_price: flight.first_class_price,
      economy_seats: flight.economy_seats,
      business_seats: flight.business_seats,
      first_class_seats: flight.first_class_seats,
      status: flight.status
    };
    this.showEditModal = true;
  }

  async updateFlight() {
    try {
      const res = await this.flightService.updateFlight(this.currentFlight.flight_id!, this.formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.showEditModal = false;
        await this.loadFlights();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Delete
  async confirmDelete(flight: FlightItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa chuyến bay',
      message: `Bạn có chắc chắn muốn xóa chuyến bay "${flight.flight_number}"?`,
      confirmText: 'Xóa',
      cancelText: 'Hủy',
      type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.flightService.deleteFlight(flight.flight_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa chuyến bay thành công!');
          await this.loadFlights();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // Status change
  async changeStatus(flight: FlightItem, newStatus: string) {
    try {
      const res = await this.flightService.updateFlightStatus(flight.flight_id, newStatus).toPromise();
      if (res?.EC === 0) {
        await this.loadFlights();
      }
    } catch (e) {
      console.error('Error changing status:', e);
    }
  }

  // Helpers
  getAirlineName(id: string): string {
    return this.airlines.find(a => a.airline_id === id)?.name || id;
  }

  getAirportName(id: string): string {
    const airport = this.airports.find(a => a.airport_id === id);
    return airport ? `${airport.city} (${id})` : id;
  }

  getStatusClass(status: string): string {
    const map: { [key: string]: string } = {
      'scheduled': 'bg-blue-100 text-blue-700',
      'boarding': 'bg-yellow-100 text-yellow-700',
      'departed': 'bg-purple-100 text-purple-700',
      'arrived': 'bg-green-100 text-green-700',
      'cancelled': 'bg-red-100 text-red-700'
    };
    return map[status] || 'bg-gray-100 text-gray-700';
  }

  getStatusLabel(status: string): string {
    const map: { [key: string]: string } = {
      'scheduled': 'Đã lên lịch',
      'boarding': 'Đang lên máy bay',
      'departed': 'Đã cất cánh',
      'arrived': 'Đã đến',
      'cancelled': 'Đã hủy'
    };
    return map[status] || status;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  formatDateTime(dt: string): string {
    if (!dt) return '';
    return new Date(dt).toLocaleString('vi-VN');
  }

  closeModal() {
    this.showAddModal = false;
    this.showEditModal = false;
  }
}
