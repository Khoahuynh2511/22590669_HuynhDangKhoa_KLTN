import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminActivityService, ActivityPackageItem } from '../../../services/admin/admin-activity.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

@Component({
  selector: 'app-activity-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './activity-list.component.html',
  styleUrl: './activity-list.component.scss'
})
export class ActivityListComponent implements OnInit {
  activities: ActivityPackageItem[] = [];
  filteredActivities: ActivityPackageItem[] = [];
  isLoading = true;

  // Modal states
  showAddModal = false;
  showEditModal = false;
  showDetailModal = false;

  // Current selected activity
  currentActivity: Partial<ActivityPackageItem> = {};
  formData: any = {};

  // Search & Filters
  searchTerm = '';
  destinationFilter = '';
  categoryFilter = '';
  timeSlotFilter = '';

  // Options lists
  destinations: string[] = ['Đà Lạt', 'Hội An', 'Nha Trang', 'Đà Nẵng', 'Phú Quốc', 'Sapa', 'Huế', 'Vũng Tàu'];
  categories: string[] = ['nature', 'relax', 'culture', 'adventure', 'spiritual', 'food'];
  timeSlots = ['morning', 'afternoon', 'evening'];
  difficulties = ['easy', 'moderate', 'hard'];

  constructor(
    private activityService: AdminActivityService,
    private dialogService: AdminDialogService
  ) {}

  async ngOnInit() {
    await this.loadActivities();
  }

  async loadActivities() {
    this.isLoading = true;
    try {
      // Fetch high number first since we filter client side for better experience
      const res = await this.activityService.getActivities({ limit: 200 }).toPromise();
      if (res?.EC === 0) {
        this.activities = res.data.activities || [];
        this.applyFilters();
      }
    } catch (e) {
      console.error('Error loading activities:', e);
    } finally {
      this.isLoading = false;
    }
  }

  applyFilters() {
    this.filteredActivities = this.activities.filter(act => {
      const matchSearch = !this.searchTerm ||
        act.name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        act.location?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        act.activity_id?.toLowerCase().includes(this.searchTerm.toLowerCase());

      const matchDest = !this.destinationFilter || act.destination === this.destinationFilter;
      const matchCat = !this.categoryFilter || act.category === this.categoryFilter;
      const matchSlot = !this.timeSlotFilter || act.time_slot === this.timeSlotFilter;

      return matchSearch && matchDest && matchCat && matchSlot;
    });
  }

  // Add modal
  openAddModal() {
    this.formData = {
      name: '',
      description: '',
      destination: this.destinations[0],
      time_slot: 'morning',
      category: 'nature',
      duration_hours: 2.0,
      price: 100000,
      difficulty: 'easy',
      location: '',
      image_url: 'https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg',
      max_participants: 20,
      min_participants: 1,
      is_active: true,
      included_services: '',
    };
    this.showAddModal = true;
  }

  async saveActivity() {
    try {
      if (!this.formData.name || !this.formData.destination || !this.formData.location) {
        await this.dialogService.alert('Lỗi', 'Vui lòng nhập đầy đủ Tên, Điểm đến và Địa điểm');
        return;
      }

      // Convert included services string comma/newline-separated to string array
      let included: string[] = [];
      if (typeof this.formData.included_services === 'string' && this.formData.included_services.trim()) {
        included = this.formData.included_services.split(/,|\n/).map((s: string) => s.trim()).filter(Boolean);
      }

      const payload = {
        ...this.formData,
        included_services: included
      };

      const res = await this.activityService.createActivity(payload).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo hoạt động thành công!');
        this.showAddModal = false;
        await this.loadActivities();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo hoạt động thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Edit modal
  openEditModal(activity: Partial<ActivityPackageItem>) {
    this.currentActivity = { ...activity };
    
    // Parse included services back to string with comma separation
    const includedStr = Array.isArray(activity.included_services) 
      ? activity.included_services.join('\n') 
      : '';

    this.formData = {
      name: activity.name,
      description: activity.description,
      destination: activity.destination,
      time_slot: activity.time_slot,
      category: activity.category,
      duration_hours: activity.duration_hours,
      price: activity.price,
      difficulty: activity.difficulty,
      location: activity.location,
      image_url: activity.image_url,
      max_participants: activity.max_participants,
      min_participants: activity.min_participants,
      is_active: activity.is_active,
      included_services: includedStr
    };
    this.showEditModal = true;
  }

  async updateActivity() {
    try {
      if (!this.formData.name || !this.formData.destination || !this.formData.location) {
        await this.dialogService.alert('Lỗi', 'Vui lòng nhập đầy đủ Tên, Điểm đến và Địa điểm');
        return;
      }

      let included: string[] = [];
      if (typeof this.formData.included_services === 'string' && this.formData.included_services.trim()) {
        included = this.formData.included_services.split(/,|\n/).map((s: string) => s.trim()).filter(Boolean);
      } else if (Array.isArray(this.formData.included_services)) {
        included = this.formData.included_services;
      }

      const payload = {
        ...this.formData,
        included_services: included
      };

      const res = await this.activityService.updateActivity(this.currentActivity.activity_id!, payload).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.showEditModal = false;
        await this.loadActivities();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Detail Modal
  openDetailModal(activity: ActivityPackageItem) {
    this.currentActivity = activity;
    this.showDetailModal = true;
  }

  // Delete
  async confirmDelete(activity: ActivityPackageItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa hoạt động',
      message: `Bạn có chắc chắn muốn xóa hoạt động "${activity.name}"?`,
      confirmText: 'Xóa',
      cancelText: 'Hủy',
      type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.activityService.deleteActivity(activity.activity_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa hoạt động thành công!');
          await this.loadActivities();
        } else {
          await this.dialogService.alert('Lỗi', res?.EM || 'Xóa hoạt động thất bại');
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // Toggle active status
  async toggleStatus(activity: ActivityPackageItem) {
    try {
      const res = await this.activityService.updateActivity(activity.activity_id, {
        is_active: !activity.is_active
      }).toPromise();
      if (res?.EC === 0) {
        await this.loadActivities();
      }
    } catch (e) {
      console.error('Error toggling status:', e);
    }
  }

  // Helpers
  getCategoryLabel(cat: string): string {
    const map: { [key: string]: string } = {
      'nature': 'Thiên nhiên',
      'relax': 'Thư giãn',
      'culture': 'Văn hóa',
      'adventure': 'Mạo hiểm',
      'spiritual': 'Tâm linh',
      'food': 'Ẩm thực'
    };
    return map[cat] || cat;
  }

  getTimeSlotLabel(slot: string): string {
    const map: { [key: string]: string } = {
      'morning': 'Buổi sáng',
      'afternoon': 'Buổi chiều',
      'evening': 'Buổi tối'
    };
    return map[slot] || slot;
  }

  getDifficultyLabel(diff: string): string {
    const map: { [key: string]: string } = {
      'easy': 'Dễ',
      'moderate': 'Trung bình',
      'hard': 'Khó'
    };
    return map[diff] || diff;
  }

  getDifficultyClass(diff: string): string {
    const map: { [key: string]: string } = {
      'easy': 'bg-green-100 text-green-700',
      'moderate': 'bg-yellow-100 text-yellow-700',
      'hard': 'bg-red-100 text-red-700'
    };
    return map[diff] || 'bg-gray-100 text-gray-700';
  }

  getTimeSlotClass(slot: string): string {
    const map: { [key: string]: string } = {
      'morning': 'bg-sky-100 text-sky-700',
      'afternoon': 'bg-orange-100 text-orange-700',
      'evening': 'bg-indigo-100 text-indigo-700'
    };
    return map[slot] || 'bg-gray-100 text-gray-700';
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  closeModal() {
    this.showAddModal = false;
    this.showEditModal = false;
    this.showDetailModal = false;
  }
}
