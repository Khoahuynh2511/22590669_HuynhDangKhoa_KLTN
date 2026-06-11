import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminTrainService, TrainItem, TrainStationItem, TrainTypeItem } from '../../../services/admin/admin-train.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

@Component({
  selector: 'app-train-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './train-list.component.html',
  styleUrl: './train-list.component.scss'
})
export class TrainListComponent implements OnInit {
  trains: TrainItem[] = [];
  filteredTrains: TrainItem[] = [];
  isLoading = true;

  // Modal states
  showAddModal = false;
  showEditModal = false;

  // Current train being edited
  currentTrain: Partial<TrainItem> = {};

  // Search & filter
  searchTerm = '';
  statusFilter = '';

  // Reference data
  stations: TrainStationItem[] = [];
  trainTypes: TrainTypeItem[] = [];

  // Form
  formData: any = {};

  statusList = ['scheduled', 'departed', 'arrived', 'cancelled'];

  constructor(
    private trainService: AdminTrainService,
    private dialogService: AdminDialogService
  ) {}

  async ngOnInit() {
    await this.loadTrains();
    this.loadReferenceData();
  }

  async loadTrains() {
    this.isLoading = true;
    try {
      const res = await this.trainService.getTrains().toPromise();
      if (res?.EC === 0) {
        this.trains = res.data.trains || [];
        this.applyFilters();
      }
    } catch (e) {
      console.error('Error loading trains:', e);
    } finally {
      this.isLoading = false;
    }
  }

  loadReferenceData() {
    this.trainService.getStations().subscribe({
      next: (res) => { if (res.EC === 0) this.stations = res.data || []; },
      error: () => {}
    });
    this.trainService.getTypes().subscribe({
      next: (res) => { if (res.EC === 0) this.trainTypes = res.data || []; },
      error: () => {}
    });
  }

  applyFilters() {
    this.filteredTrains = this.trains.filter(train => {
      const matchSearch = !this.searchTerm ||
        train.train_number?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        train.train_id?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchStatus = !this.statusFilter || train.status === this.statusFilter;
      return matchSearch && matchStatus;
    });
  }

  // Add modal
  openAddModal() {
    this.formData = {
      train_number: '',
      train_type_id: '',
      departure_station: '',
      arrival_station: '',
      departure_time: '',
      arrival_time: '',
      duration_hours: 10,
      status: 'scheduled'
    };
    this.showAddModal = true;
  }

  async saveTrain() {
    try {
      const res = await this.trainService.createTrain(this.formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo chuyến tàu thành công!');
        this.showAddModal = false;
        await this.loadTrains();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo chuyến tàu thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Edit modal
  openEditModal(train: TrainItem) {
    this.currentTrain = { ...train };
    this.formData = {
      train_number: train.train_number,
      train_type_id: train.train_type_id,
      departure_station: train.departure_station,
      arrival_station: train.arrival_station,
      departure_time: train.departure_time?.slice(0, 16),
      arrival_time: train.arrival_time?.slice(0, 16),
      duration_hours: train.duration_hours,
      status: train.status
    };
    this.showEditModal = true;
  }

  async updateTrain() {
    try {
      const res = await this.trainService.updateTrain(this.currentTrain.train_id!, this.formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.showEditModal = false;
        await this.loadTrains();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Delete
  async confirmDelete(train: TrainItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa chuyến tàu',
      message: `Bạn có chắc chắn muốn xóa chuyến tàu "${train.train_number}"?`,
      confirmText: 'Xóa',
      cancelText: 'Hủy',
      type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.trainService.deleteTrain(train.train_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa chuyến tàu thành công!');
          await this.loadTrains();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // Status change
  async changeStatus(train: TrainItem, newStatus: string) {
    try {
      const res = await this.trainService.updateTrainStatus(train.train_id, newStatus).toPromise();
      if (res?.EC === 0) {
        await this.loadTrains();
      }
    } catch (e) {
      console.error('Error changing status:', e);
    }
  }

  // Helpers
  getStationName(id: string): string {
    return this.stations.find(s => s.station_id === id)?.name || id;
  }

  getStationCity(id: string): string {
    return this.stations.find(s => s.station_id === id)?.city || '';
  }

  getTrainTypeName(id: string): string {
    return this.trainTypes.find(t => t.type_id === id)?.name || id;
  }

  getStatusClass(status: string): string {
    const map: { [key: string]: string } = {
      'scheduled': 'bg-blue-100 text-blue-700',
      'departed': 'bg-purple-100 text-purple-700',
      'arrived': 'bg-green-100 text-green-700',
      'cancelled': 'bg-red-100 text-red-700'
    };
    return map[status] || 'bg-gray-100 text-gray-700';
  }

  getStatusLabel(status: string): string {
    const map: { [key: string]: string } = {
      'scheduled': 'Đã lên lịch',
      'departed': 'Đã xuất phát',
      'arrived': 'Đã đến',
      'cancelled': 'Đã hủy'
    };
    return map[status] || status;
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
