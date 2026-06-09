import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminHotelService, HotelItem } from '../../../services/admin/admin-hotel.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

@Component({
  selector: 'app-hotel-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './hotel-list.component.html',
  styleUrl: './hotel-list.component.scss'
})
export class HotelListComponent implements OnInit {
  hotels: HotelItem[] = [];
  filteredHotels: HotelItem[] = [];
  isLoading = true;

  // Modal states
  showAddModal = false;
  showEditModal = false;

  // Current hotel being edited
  currentHotel: Partial<HotelItem> = {};

  // Search & filter
  searchTerm = '';
  activeFilter: string = '';

  // Form
  formData: any = {};

  // Amenities input
  amenitiesText = '';

  // Image upload
  selectedImages: File[] = [];
  imagePreviews: string[] = [];

  constructor(
    private hotelService: AdminHotelService,
    private dialogService: AdminDialogService
  ) {}

  async ngOnInit() {
    await this.loadHotels();
  }

  async loadHotels() {
    this.isLoading = true;
    try {
      const res = await this.hotelService.getHotels().toPromise();
      if (res?.EC === 0) {
        this.hotels = res.data.hotels || [];
        this.applyFilters();
      }
    } catch (e) {
      console.error('Error loading hotels:', e);
    } finally {
      this.isLoading = false;
    }
  }

  applyFilters() {
    this.filteredHotels = this.hotels.filter(hotel => {
      const matchSearch = !this.searchTerm ||
        hotel.hotel_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        hotel.location?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchActive = !this.activeFilter ||
        (this.activeFilter === 'active' ? hotel.is_active : !hotel.is_active);
      return matchSearch && matchActive;
    });
  }

  // Add modal
  openAddModal() {
    this.formData = {
      hotel_name: '',
      location: '',
      description: '',
      address: '',
      star_rating: 4.0,
      review_score: 8.0,
      review_count: 0,
      price: 0,
      original_price: 0,
      discount: 0,
      available_rooms: 0,
    };
    this.amenitiesText = '';
    this.selectedImages = [];
    this.imagePreviews = [];
    this.showAddModal = true;
  }

  async saveHotel() {
    try {
      // Build FormData for image upload
      const formData = new FormData();
      formData.append('hotel_name', this.formData.hotel_name);
      formData.append('location', this.formData.location);
      formData.append('description', this.formData.description);
      formData.append('address', this.formData.address);
      formData.append('star_rating', String(Number(this.formData.star_rating)));
      formData.append('review_score', String(Number(this.formData.review_score)));
      formData.append('review_count', String(Number(this.formData.review_count)));
      formData.append('price', String(Number(this.formData.price)));
      formData.append('available_rooms', String(Number(this.formData.available_rooms)));
      formData.append('is_active', 'true');

      if (this.formData.original_price) {
        formData.append('original_price', String(Number(this.formData.original_price)));
      }
      if (this.formData.discount) {
        formData.append('discount', String(Number(this.formData.discount)));
      }
      if (this.amenitiesText) {
        formData.append('amenities', this.amenitiesText);
      }

      // Add images
      this.selectedImages.forEach((file) => {
        formData.append('images', file);
      });

      const res = await this.hotelService.createHotelWithImages(formData).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo khách sạn thành công!');
        this.showAddModal = false;
        await this.loadHotels();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo khách sạn thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  onImageSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const files = Array.from(input.files);

      // Validate max 10 images
      if (this.selectedImages.length + files.length > 10) {
        this.dialogService.alert('Lỗi', 'Tối đa 10 ảnh cho phép');
        return;
      }

      files.forEach(file => {
        // Validate image type
        if (!file.type.match(/image\/(jpeg|jpg|png|webp)/)) {
          this.dialogService.alert('Lỗi', 'Chỉ chấp nhận định dạng JPEG, JPG, PNG, WebP');
          return;
        }

        this.selectedImages.push(file);

        // Create preview
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.imagePreviews.push(e.target.result);
        };
        reader.readAsDataURL(file);
      });
    }
  }

  removeImage(index: number): void {
    this.selectedImages.splice(index, 1);
    this.imagePreviews.splice(index, 1);
  }

  // Edit modal
  openEditModal(hotel: HotelItem) {
    this.currentHotel = { ...hotel };
    this.formData = {
      hotel_name: hotel.hotel_name,
      location: hotel.location,
      description: hotel.description || '',
      address: hotel.address || '',
      star_rating: hotel.star_rating,
      review_score: hotel.review_score,
      review_count: hotel.review_count,
      price: hotel.price,
      original_price: hotel.original_price,
      discount: hotel.discount,
      available_rooms: hotel.available_rooms,
      image_urls: hotel.image_urls || '',
    };
    this.amenitiesText = (hotel.amenities || []).join(', ');
    this.showEditModal = true;
  }

  async updateHotel() {
    try {
      const data = { ...this.formData };
      data.amenities = this.amenitiesText.split(',').map((s: string) => s.trim()).filter((s: string) => s);
      data.price = Number(data.price);
      data.original_price = Number(data.original_price);
      data.discount = Number(data.discount);
      data.star_rating = Number(data.star_rating);
      data.review_score = Number(data.review_score);
      data.review_count = Number(data.review_count);
      data.available_rooms = Number(data.available_rooms);

      const res = await this.hotelService.updateHotel(this.currentHotel.hotel_id!, data).toPromise();
      if (res?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Cập nhật thành công!');
        this.showEditModal = false;
        await this.loadHotels();
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      await this.dialogService.alert('Lỗi', e?.error?.detail || 'Lỗi kết nối server');
    }
  }

  // Delete
  async confirmDelete(hotel: HotelItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xóa khách sạn',
      message: `Bạn có chắc chắn muốn xóa khách sạn "${hotel.hotel_name}"?`,
      confirmText: 'Xóa',
      cancelText: 'Hủy',
      type: 'warning'
    });
    if (confirmed) {
      try {
        const res = await this.hotelService.deleteHotel(hotel.hotel_id).toPromise();
        if (res?.EC === 0) {
          await this.dialogService.alert('Thành công', 'Xóa khách sạn thành công!');
          await this.loadHotels();
        }
      } catch (e: any) {
        await this.dialogService.alert('Lỗi', e?.error?.detail || 'Xóa thất bại');
      }
    }
  }

  // Toggle status
  async toggleActive(hotel: HotelItem) {
    try {
      const res = await this.hotelService.toggleStatus(hotel.hotel_id, !hotel.is_active).toPromise();
      if (res?.EC === 0) {
        await this.loadHotels();
      }
    } catch (e) {
      console.error('Error toggling status:', e);
    }
  }

  // Helpers
  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  formatDate(dt: string): string {
    if (!dt) return '';
    return new Date(dt).toLocaleDateString('vi-VN');
  }

  closeModal() {
    this.showAddModal = false;
    this.showEditModal = false;
  }
}
