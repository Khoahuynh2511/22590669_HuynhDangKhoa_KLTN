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

  // Filters
  searchTerm = '';
  statusFilter: string = '';
  locationFilter = '';

  // Advanced Filters toggle
  showAdvancedFilters = false;

  // Advanced Filters states
  priceSegmentFilter: '' | 'budget' | 'mid' | 'premium' | 'custom' = '';
  minPriceFilter: number | '' = '';
  maxPriceFilter: number | '' = '';
  isPriceFilterActive = false;

  starRatingFilter: number | '' = '';
  isStarFilterActive = false;

  minRoomFilter: number | '' = '';
  maxRoomFilter: number | '' = '';
  isRoomFilterActive = false;

  // Modals
  showAddModal = false;
  showEditModal = false;
  showDetailModal = false;
  showDeleteModal = false;
  showBulkUploadModal = false;
  showPreview = false;

  // Current hotel for edit/delete/detail
  currentHotel: Partial<HotelItem> = {};
  originalHotelData: HotelItem | null = null;
  deleteId = '';

  // Loading state
  isLoading = false;
  errorMessage = '';

  // Bulk upload
  selectedCSVFile: File | null = null;
  bulkUploadResult: any = null;

  // Image management
  selectedFiles: File[] = [];
  imageUrls: string[] = [];
  originalImageUrls: string[] = [];
  draggedImageIndex: number | null = null;
  originalImageCount: number = 0;
  hasImageChanges: boolean = false;

  // Upload progress
  uploadProgress: number = 0;
  uploadStatus: string = '';
  isUploading: boolean = false;

  // Copy state
  copiedHotelId: boolean = false;

  // Amenities input
  amenitiesText = '';

  // Track original status
  originalHotelStatus: boolean = true;

  constructor(
    private hotelService: AdminHotelService,
    private dialogService: AdminDialogService
  ) {}

  ngOnInit() {
    this.loadHotels();
  }

  async loadHotels() {
    try {
      this.isLoading = true;
      this.errorMessage = '';
      const response = await this.hotelService.getHotels().toPromise();
      if (response?.EC === 0) {
        this.hotels = response.data.hotels || [];
      }
      this.applyFilters();
    } catch (error: any) {
      this.errorMessage = error.message || 'Không thể tải danh sách khách sạn';
      console.error('Load hotels error:', error);
    } finally {
      this.isLoading = false;
    }
  }

  applyFilters() {
    const hasPriceFilter = this.priceSegmentFilter;
    const hasStarFilter = this.starRatingFilter;
    const hasRoomFilter = this.minRoomFilter || this.maxRoomFilter;

    this.filteredHotels = this.hotels.filter(hotel => {
      const matchesSearch = !this.searchTerm ||
        hotel.hotel_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        hotel.location?.toLowerCase().includes(this.searchTerm.toLowerCase());

      const matchesStatus = !this.statusFilter ||
        (this.statusFilter === 'active' && hotel.is_active) ||
        (this.statusFilter === 'inactive' && !hotel.is_active);

      const matchesLocation = !this.locationFilter ||
        hotel.location?.toLowerCase().includes(this.locationFilter.toLowerCase());

      // Price filter (client-side)
      const matchesPrice = !hasPriceFilter || (() => {
        let min = this.minPriceFilter ? Number(this.minPriceFilter) : 0;
        let max = this.maxPriceFilter ? Number(this.maxPriceFilter) : Infinity;

        if (this.priceSegmentFilter === 'budget') { min = 0; max = 500000; }
        else if (this.priceSegmentFilter === 'mid') { min = 500000; max = 2000000; }
        else if (this.priceSegmentFilter === 'premium') { min = 2000000; max = Infinity; }

        return hotel.price >= min && hotel.price <= max;
      })();

      // Star rating filter
      const matchesStar = !hasStarFilter || hotel.star_rating >= Number(this.starRatingFilter);

      // Room filter
      const matchesRoom = !hasRoomFilter || (() => {
        const min = this.minRoomFilter ? Number(this.minRoomFilter) : 0;
        const max = this.maxRoomFilter ? Number(this.maxRoomFilter) : Infinity;
        return hotel.available_rooms >= min && hotel.available_rooms <= max;
      })();

      return matchesSearch && matchesStatus && matchesLocation && matchesPrice && matchesStar && matchesRoom;
    });

    this.isPriceFilterActive = !!hasPriceFilter;
    this.isStarFilterActive = !!hasStarFilter;
    this.isRoomFilterActive = !!hasRoomFilter;
  }

  onFilterChange() {
    this.applyFilters();
  }

  // ========== Stats ==========
  getActiveHotels(): number {
    return this.hotels.filter(h => h.is_active).length;
  }

  getInactiveHotels(): number {
    return this.hotels.filter(h => !h.is_active).length;
  }

  getAveragePrice(): string {
    if (this.hotels.length === 0) return '0 ₫';
    const total = this.hotels.reduce((sum, h) => sum + h.price, 0);
    return this.formatPrice(total / this.hotels.length);
  }

  // ========== Add Modal ==========
  openAddModal() {
    this.currentHotel = {
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
      is_active: true
    };
    this.amenitiesText = '';
    this.imageUrls = [];
    this.selectedFiles = [];
    this.showPreview = true;
    this.showAddModal = true;
  }

  closeAddModal() {
    this.showAddModal = false;
    this.showPreview = false;
    this.currentHotel = {};
  }

  async saveHotel() {
    try {
      this.isLoading = true;
      this.isUploading = true;
      this.uploadProgress = 0;
      this.uploadStatus = 'Đang chuẩn bị...';
      this.errorMessage = '';

      if (!this.currentHotel.hotel_name || !this.currentHotel.location || !this.currentHotel.description) {
        this.errorMessage = 'Vui lòng điền đầy đủ thông tin bắt buộc';
        this.isUploading = false;
        return;
      }

      this.uploadProgress = 20;
      this.uploadStatus = 'Đang xử lý thông tin khách sạn...';

      const formData = new FormData();
      formData.append('hotel_name', this.currentHotel.hotel_name!);
      formData.append('location', this.currentHotel.location!);
      formData.append('description', this.currentHotel.description || '');
      formData.append('address', this.currentHotel.address || '');
      formData.append('star_rating', String(Number(this.currentHotel.star_rating)));
      formData.append('review_score', String(Number(this.currentHotel.review_score)));
      formData.append('review_count', String(Number(this.currentHotel.review_count)));
      formData.append('price', String(Number(this.currentHotel.price)));
      formData.append('available_rooms', String(Number(this.currentHotel.available_rooms)));
      formData.append('is_active', String(this.currentHotel.is_active ?? true));

      if (this.currentHotel.original_price) {
        formData.append('original_price', String(Number(this.currentHotel.original_price)));
      }
      if (this.currentHotel.discount) {
        formData.append('discount', String(Number(this.currentHotel.discount)));
      }
      if (this.amenitiesText) {
        formData.append('amenities', this.amenitiesText);
      }

      this.uploadProgress = 40;
      this.uploadStatus = `Đang tải lên ${this.selectedFiles.length} ảnh...`;

      const progressInterval = setInterval(() => {
        if (this.uploadProgress < 90) this.uploadProgress += 5;
      }, 200);

      this.selectedFiles.forEach(file => formData.append('images', file));

      const res = await this.hotelService.createHotelWithImages(formData).toPromise();

      clearInterval(progressInterval);
      this.uploadProgress = 100;
      this.uploadStatus = 'Hoàn tất!';

      if (res?.EC === 0) {
        await this.loadHotels();
        this.closeAddModal();
        this.isUploading = false;
        await this.dialogService.alert('Thành công', 'Thêm khách sạn thành công!');
      } else {
        this.isUploading = false;
        await this.dialogService.alert('Lỗi', res?.EM || 'Tạo khách sạn thất bại');
      }
    } catch (e: any) {
      this.isUploading = false;
      this.errorMessage = e?.error?.detail || e?.message || 'Lỗi kết nối server';
      await this.dialogService.alert('Lỗi', this.errorMessage);
    } finally {
      this.isLoading = false;
    }
  }

  // ========== Detail Modal ==========
  openDetailModal(hotel: HotelItem) {
    this.currentHotel = { ...hotel };
    this.imageUrls = hotel.image_urls ? hotel.image_urls.split('|').filter(url => url.trim()) : [];
    this.amenitiesText = (hotel.amenities || []).join(', ');
    this.showDetailModal = true;
    this.showPreview = false;
  }

  closeDetailModal() {
    this.showDetailModal = false;
    this.currentHotel = {};
  }

  // ========== Edit Modal ==========
  openEditModal(hotel: HotelItem) {
    this.currentHotel = { ...hotel };
    this.originalHotelData = { ...hotel };
    this.imageUrls = hotel.image_urls ? hotel.image_urls.split('|').filter(url => url.trim()) : [];
    this.originalImageUrls = [...this.imageUrls];
    this.originalImageCount = this.imageUrls.length;
    this.selectedFiles = [];
    this.hasImageChanges = false;
    this.amenitiesText = (hotel.amenities || []).join(', ');
    this.originalHotelStatus = hotel.is_active ?? true;
    this.showEditModal = true;
    this.showPreview = true;
  }

  closeEditModal() {
    this.showEditModal = false;
    this.showPreview = false;
    this.currentHotel = {};
    this.originalHotelData = null;
  }

  hasChanges(): boolean {
    if (!this.originalHotelData) return false;

    const fieldsToCompare: (keyof HotelItem)[] = [
      'hotel_name', 'location', 'description', 'address',
      'star_rating', 'review_score', 'review_count',
      'price', 'original_price', 'discount', 'available_rooms', 'is_active'
    ];

    const hasFieldChanges = fieldsToCompare.some(field => {
      const current = this.currentHotel[field];
      const original = this.originalHotelData![field];
      return current !== original;
    });

    if (hasFieldChanges) return true;

    // Check amenities change
    const currentAmenities = this.amenitiesText.split(',').map(s => s.trim()).filter(s => s).join(',');
    const originalAmenities = (this.originalHotelData.amenities || []).join(',');
    if (currentAmenities !== originalAmenities) return true;

    if (this.hasImageChanges || this.selectedFiles.length > 0) return true;

    const currentImageString = this.imageUrls.join('|');
    const originalImageString = this.originalImageUrls.join('|');
    if (currentImageString !== originalImageString) return true;

    return false;
  }

  async updateHotel() {
    try {
      if (!this.currentHotel.hotel_id) {
        this.errorMessage = 'Không tìm thấy ID khách sạn';
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';

      const hotelId = this.currentHotel.hotel_id;

      // Handle image changes
      if (this.hasImageChanges || this.selectedFiles.length > 0) {
        try {
          const hasDeletedOldImages = this.imageUrls.length < this.originalImageCount;
          const currentOldUrls = this.imageUrls.filter(url => this.originalImageUrls.includes(url));
          const hasReorderedImages = currentOldUrls.some((url, index) =>
            this.originalImageUrls[index] !== url
          );
          const hasNewImages = this.selectedFiles.length > 0;

          if (hasReorderedImages && !hasNewImages && !hasDeletedOldImages) {
            this.currentHotel.image_urls = this.imageUrls.join('|');
          } else if (hasDeletedOldImages || hasNewImages) {
            let filesToUpload: File[] = [];
            let shouldReplace = false;

            if (hasDeletedOldImages || hasReorderedImages) {
              const remainingOldUrls = this.imageUrls.filter(url => this.originalImageUrls.includes(url));

              if (remainingOldUrls.length > 0) {
                const downloadedFiles = await Promise.all(
                  remainingOldUrls.map((url) => {
                    const urlParts = url.split('/');
                    const filename = urlParts[urlParts.length - 1].split('?')[0];
                    return this.downloadImageAsFile(url, filename);
                  })
                );
                filesToUpload = [...downloadedFiles, ...this.selectedFiles];
              } else {
                filesToUpload = [...this.selectedFiles];
              }
              shouldReplace = true;
            } else {
              filesToUpload = [...this.selectedFiles];
              shouldReplace = false;
            }

            if (filesToUpload.length > 0) {
              const uploadResult = await this.hotelService.manageImages(hotelId, filesToUpload, shouldReplace);
              if (uploadResult && uploadResult.image_urls) {
                this.currentHotel.image_urls = uploadResult.image_urls.join('|');
              }
            }
          }
        } catch (uploadError: any) {
          console.error('Error uploading images:', uploadError);
          this.errorMessage = 'Cảnh báo: Không thể upload ảnh mới. Thông tin khác vẫn được cập nhật.';
        }
      }

      // Build update data
      const updateData: any = {
        hotel_name: this.currentHotel.hotel_name,
        location: this.currentHotel.location,
        description: this.currentHotel.description,
        address: this.currentHotel.address,
        star_rating: Number(this.currentHotel.star_rating),
        review_score: Number(this.currentHotel.review_score),
        review_count: Number(this.currentHotel.review_count),
        price: Number(this.currentHotel.price),
        original_price: Number(this.currentHotel.original_price),
        discount: Number(this.currentHotel.discount),
        available_rooms: Number(this.currentHotel.available_rooms),
        amenities: this.amenitiesText.split(',').map((s: string) => s.trim()).filter((s: string) => s),
        is_active: this.currentHotel.is_active,
      };

      if (this.hasImageChanges || this.selectedFiles.length > 0) {
        updateData.image_urls = this.currentHotel.image_urls;
      }

      const res = await this.hotelService.updateHotel(hotelId, updateData).toPromise();
      if (res?.EC === 0) {
        await this.loadHotels();
        this.closeEditModal();
        await this.dialogService.alert('Thành công', 'Cập nhật khách sạn thành công!');
      } else {
        await this.dialogService.alert('Lỗi', res?.EM || 'Cập nhật thất bại');
      }
    } catch (e: any) {
      this.errorMessage = e?.error?.detail || e?.message || 'Lỗi kết nối server';
      await this.dialogService.alert('Lỗi', this.errorMessage);
    } finally {
      this.isLoading = false;
    }
  }

  // ========== Delete ==========
  confirmDelete(hotel: HotelItem) {
    this.deleteId = hotel.hotel_id;
    this.showDeleteModal = true;
  }

  closeDeleteModal() {
    this.showDeleteModal = false;
    this.deleteId = '';
  }

  async deleteHotel() {
    try {
      if (!this.deleteId) return;
      this.isLoading = true;
      this.errorMessage = '';

      await this.hotelService.deleteHotel(this.deleteId).toPromise();
      await this.loadHotels();
      this.closeDeleteModal();
      await this.dialogService.alert('Thành công', 'Xóa khách sạn thành công!');
    } catch (error: any) {
      this.errorMessage = error.message || 'Không thể xóa khách sạn';
      await this.dialogService.alert('Lỗi', this.errorMessage);
    } finally {
      this.isLoading = false;
    }
  }

  // ========== Toggle Status ==========
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

  // ========== Image Handling ==========
  onFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      const files = Array.from(input.files);
      const currentImageCount = this.imageUrls.length;
      const totalImages = currentImageCount + files.length;

      if (totalImages > 10) {
        const remaining = 10 - currentImageCount;
        if (remaining <= 0) {
          this.dialogService.warning('Đã đủ 10 ảnh', 'Xóa bớt ảnh cũ để tải thêm.');
        } else {
          this.dialogService.warning('Vượt giới hạn', `Chỉ có thể tải thêm ${remaining} ảnh.`);
        }
        input.value = '';
        return;
      }

      const validFiles = files.filter(file => {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
        return validTypes.includes(file.type);
      });

      if (validFiles.length !== files.length) {
        this.dialogService.warning('File không hợp lệ', 'Chỉ chấp nhận JPEG, JPG, PNG, WebP');
        input.value = '';
        return;
      }

      this.selectedFiles.push(...validFiles);
      this.hasImageChanges = true;

      validFiles.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.imageUrls.push(e.target.result);
        };
        reader.readAsDataURL(file);
      });

      input.value = '';
    }
  }

  removeImage(index: number) {
    const oldImagesCount = this.originalImageUrls.length;
    if (index < oldImagesCount) {
      this.imageUrls.splice(index, 1);
    } else {
      const newFileIndex = index - oldImagesCount;
      if (newFileIndex >= 0 && newFileIndex < this.selectedFiles.length) {
        this.selectedFiles.splice(newFileIndex, 1);
      }
      this.imageUrls.splice(index, 1);
    }
    this.hasImageChanges = true;
  }

  onDragStart(index: number) {
    this.draggedImageIndex = index;
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
  }

  onDrop(event: DragEvent, dropIndex: number) {
    event.preventDefault();
    if (this.draggedImageIndex === null) return;

    const draggedUrl = this.imageUrls[this.draggedImageIndex];
    this.imageUrls.splice(this.draggedImageIndex, 1);
    this.imageUrls.splice(dropIndex, 0, draggedUrl);

    const newFileStartIndex = this.imageUrls.length - this.selectedFiles.length;
    if (this.draggedImageIndex >= newFileStartIndex && dropIndex >= newFileStartIndex) {
      const draggedFileIndex = this.draggedImageIndex - newFileStartIndex;
      const dropFileIndex = dropIndex - newFileStartIndex;
      const draggedFile = this.selectedFiles[draggedFileIndex];
      this.selectedFiles.splice(draggedFileIndex, 1);
      this.selectedFiles.splice(dropFileIndex, 0, draggedFile);
    }

    this.hasImageChanges = true;
    this.draggedImageIndex = null;
  }

  onDragEnd() {
    this.draggedImageIndex = null;
  }

  async downloadImageAsFile(url: string, filename: string): Promise<File> {
    const response = await fetch(url);
    const blob = await response.blob();
    let extension = '.jpg';
    const urlParts = url.split('.');
    if (urlParts.length > 1) {
      const urlExt = urlParts[urlParts.length - 1].split('?')[0].toLowerCase();
      if (['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(urlExt)) {
        extension = '.' + urlExt;
      }
    }
    if (blob.type === 'image/jpeg') extension = '.jpg';
    else if (blob.type === 'image/png') extension = '.png';
    else if (blob.type === 'image/webp') extension = '.webp';
    const finalFilename = filename.replace(/\.[^.]+$/, '') + extension;
    return new File([blob], finalFilename, { type: blob.type });
  }

  togglePreview() {
    this.showPreview = !this.showPreview;
  }

  // ========== CSV Bulk Upload ==========
  openBulkUploadModal() {
    this.showBulkUploadModal = true;
    this.selectedCSVFile = null;
    this.bulkUploadResult = null;
  }

  closeBulkUploadModal() {
    this.showBulkUploadModal = false;
    this.selectedCSVFile = null;
    this.bulkUploadResult = null;
  }

  onCSVFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
        this.selectedCSVFile = file;
      } else {
        this.dialogService.warning('File không hợp lệ', 'Vui lòng chọn file CSV!');
        input.value = '';
      }
    }
  }

  async uploadCSV() {
    if (!this.selectedCSVFile) {
      await this.dialogService.warning('Chưa chọn file', 'Vui lòng chọn file CSV!');
      return;
    }

    this.isLoading = true;
    try {
      const result = await this.hotelService.createHotelsFromCSV(this.selectedCSVFile);
      this.bulkUploadResult = result;

      if (result.EC === 0) {
        await this.dialogService.alert('Upload thành công!', `${result.data.successful} khách sạn được tạo, ${result.data.failed} thất bại.`);
        if (result.data.successful > 0) {
          await this.loadHotels();
        }
      } else {
        await this.dialogService.alert('Lỗi', `Có lỗi xảy ra: ${result.EM}`);
      }
    } catch (error: any) {
      console.error('Error uploading CSV:', error);
      await this.dialogService.alert('Lỗi', error.message || 'Lỗi khi upload file CSV!');
    } finally {
      this.isLoading = false;
    }
  }

  downloadCSVTemplate() {
    const template = `hotel_name,location,description,address,star_rating,review_score,review_count,price,original_price,discount,available_rooms,amenities,image_urls,is_active
Khách Sạn Mẫu Đà Nẵng,Đà Nẵng,Khách sạn 4 sao trung tâm thành phố,123 Nguyễn Văn Linh,4,8.5,120,1500000,2000000,25,50,Spa|Pool|WiFi|Breakfast,,true
Khách Sạn Mẫu Hà Nội,Hà Nội,Khách sạn 3 sao phố cổ,45 Hàng Bạc,3,7.8,85,800000,1000000,20,30,WiFi|Breakfast,,true`;

    const blob = new Blob([template], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'hotel_template.csv';
    link.click();
  }

  // ========== Copy & Utilities ==========
  async copyToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      this.copiedHotelId = true;
      setTimeout(() => { this.copiedHotelId = false; }, 3000);
    } catch (err) {
      await this.dialogService.alert('Lỗi', 'Không thể copy!');
    }
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN').format(price) + ' VNĐ';
  }

  formatPreviewPrice(price: number): string {
    if (!price) return '0 ₫';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  formatDate(dt: string): string {
    if (!dt) return '';
    return new Date(dt).toLocaleDateString('vi-VN');
  }

  formatDateTime(dateString: string): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('vi-VN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
  }

  getImageUrl(imageUrls: string): string {
    return imageUrls?.split('|')[0] || 'https://via.placeholder.com/300x200?text=No+Image';
  }

  closeModal() {
    this.showAddModal = false;
    this.showEditModal = false;
    this.showDetailModal = false;
    this.showPreview = false;
    this.currentHotel = {};
    this.originalHotelData = null;
  }

  // ========== Filter Clear ==========
  clearPriceFilter() {
    this.priceSegmentFilter = '';
    this.minPriceFilter = '';
    this.maxPriceFilter = '';
    this.isPriceFilterActive = false;
    this.applyFilters();
  }

  clearStarFilter() {
    this.starRatingFilter = '';
    this.isStarFilterActive = false;
    this.applyFilters();
  }

  clearRoomFilter() {
    this.minRoomFilter = '';
    this.maxRoomFilter = '';
    this.isRoomFilterActive = false;
    this.applyFilters();
  }

  onPriceSegmentChange() {
    if (this.priceSegmentFilter !== 'custom') {
      this.minPriceFilter = '';
      this.maxPriceFilter = '';
    }
  }
}
