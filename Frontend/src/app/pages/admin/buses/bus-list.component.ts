import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminBusService, BusItem, CompanyItem, StationItem } from '../../../services/admin/admin-bus.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

@Component({
  selector: 'app-bus-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './bus-list.component.html',
  styleUrl: './bus-list.component.scss'
})
export class BusListComponent implements OnInit {
  buses: BusItem[] = [];
  filteredBuses: BusItem[] = [];
  isLoading = true;

  // Modal states
  showAddModal = false;
  showEditModal = false;
  showDeleteModal = false;

  // Current bus being edited/deleted
  currentBus: Partial<BusItem> = {};
  deleteId = '';

  // Search & filter
  searchTerm = '';
  statusFilter = '';

  // Reference data
  companies: CompanyItem[] = [];
  stations: StationItem[] = [];

  // Form
  formData: any = {};

  // Bus types for dropdown
  busTypes = [
    { id: 'limousine_9', name: 'Limousine 9 chỗ' },
    { id: 'limousine_11', name: 'Limousine 11 chỗ' },
    { id: 'sleeper_40', name: 'Giường nằm 40 chỗ' },
    { id: 'sleeper_34', name: 'Cabin 34 chỗ' },
  ];

  statusList = ['scheduled', 'boarding', 'departed', 'arrived', 'cancelled'];

  constructor(
    private busService: AdminBusService,
    private dialogService: AdminDialogService
  ) {}

  async ngOnInit() {
    await this.loadBuses();
    this.loadReferenceData();
  }

  async loadBuses() {
    this.isLoading = true;
    try {
      const res = await this.busService.getBuses().toPromise();
      if (res?.EC === 0) {
        this.buses = res.data.buses || [];
        this.applyFilters();
      }
    } catch (e) {
      console.error('Error loading buses:', e);
    } finally {
      this.isLoading = false;
    }
  }

  loadReferenceData() {
    this.busService.getCompanies().subscribe({
      next: (res) => { if (res.EC === 0) this.companies = res.data || []; },
      error: () => {}
    });
    this.busService.getStations().subscribe({
      next: (res) => { if (res.EC === 0) this.stations = res.data || []; },
      error: () => {}
    });
  }

  applyFilters() {
    this.filteredBuses = this.buses.filter(bus => {
      const matchSearch = !this.searchTerm ||
        bus.bus_number?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        bus.bus_id?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchStatus = !this.statusFilter || bus.status === this.statusFilter;
      return matchSearch && matchStatus;
    });
  }

  // Add modal
  openAddModal() {
    this.formData = {
      bus_number: '',
      company_id: '',
      bus_type_id: '',
      departure_station: '',
      arrival_station: '',
      departure_time: '',
      arrival_time: '',
      duration_hours: 8,
      total_seats: 40,
      available_seats: 40,
      base_price: 300000,
      status: 'scheduled'
    };
    this.showAddModal = true;
  }

  async saveBus() {
    try {
      const res = await this.busService.createBus(this.formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo chuyến xe thành công!');
        this.showAddModal = false;
        await this.loadBuses();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo chuyến xe thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Edit modal
  openEditModal(bus: BusItem) {
    this.currentBus = { ...bus };
    this.formData = {
      bus_number: bus.bus_number,
      company_id: bus.company_id,
      bus_type_id: bus.bus_type_id,
      departure_station: bus.departure_station,
      arrival_station: bus.arrival_station,
      departure_time: bus.departure_time?.slice(0, 16),
      arrival_time: bus.arrival_time?.slice(0, 16),
      duration_hours: bus.duration_hours,
      total_seats: bus.total_seats,
      available_seats: bus.available_seats,
      base_price: bus.base_price,
      status: bus.status
    };
    this.showEditModal = true;
  }

  async updateBus() {
    try {
      const res = await this.busService.updateBus(this.currentBus.bus_id!, this.formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.showEditModal = false;
        await this.loadBuses();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Delete modal
  async confirmDelete(bus: BusItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa chuyến xe',
      message: `Bạn có chắc chắn muốn xóa chuyến xe "${bus.bus_number}"?`,
      confirmText: 'Xóa',
      cancelText: 'Hủy',
      type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.busService.deleteBus(bus.bus_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa chuyến xe thành công!');
          await this.loadBuses();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // Status change
  async changeStatus(bus: BusItem, newStatus: string) {
    try {
      const res = await this.busService.updateBusStatus(bus.bus_id, newStatus).toPromise();
      if (res?.EC === 0) {
        await this.loadBuses();
      }
    } catch (e) {
      console.error('Error changing status:', e);
    }
  }

  // Helpers
  getCompanyName(id: string): string {
    return this.companies.find(c => c.company_id === id)?.name || id;
  }

  getStationName(id: string): string {
    return this.stations.find(s => s.station_id === id)?.name || id;
  }

  getBusTypeName(id: string): string {
    return this.busTypes.find(t => t.id === id)?.name || id;
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
      'boarding': 'Đang lên xe',
      'departed': 'Đã xuất phát',
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
    this.showDeleteModal = false;
  }
}
