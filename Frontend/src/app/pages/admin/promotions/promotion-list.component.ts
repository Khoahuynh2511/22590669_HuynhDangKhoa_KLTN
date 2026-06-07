import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminPromotionService, Promotion, PromotionCreateRequest, PromotionUpdateRequest } from '../../../services/admin/admin-promotion.service';

@Component({
  selector: 'app-promotion-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './promotion-list.component.html',
  styleUrl: './promotion-list.component.scss'
})
export class PromotionListComponent implements OnInit {
  promotions: Promotion[] = [];
  filteredPromotions: Promotion[] = [];
  
  searchTerm = '';
  statusFilter: string = '';
  
  // Advanced Filters
  showAdvancedFilters = false;
  
  // Discount filter
  minDiscountFilter: number | '' = '';
  maxDiscountFilter: number | '' = '';
  isDiscountFilterActive = false;
  
  // Date range filter
  startDateFilter = '';
  endDateFilter = '';
  isDateRangeFilterActive = false;
  
  // Quantity filter
  minQuantityFilter: number | '' = '';
  maxQuantityFilter: number | '' = '';
  isQuantityFilterActive = false;
  
  // User count filter
  minUserCountFilter: number | '' = '';
  maxUserCountFilter: number | '' = '';
  isUserCountFilterActive = false;
  
  showAddModal = false;
  showEditModal = false;
  showDeleteModal = false;
  
  currentPromotion: Partial<PromotionCreateRequest> = {};
  editPromotion: Promotion | null = null;
  deleteId = '';
  
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  constructor(private promotionService: AdminPromotionService) {}

  ngOnInit() {
    this.loadPromotions();
  }

  loadPromotions() {
    this.isLoading = true;
    this.errorMessage = '';
    
    const params: any = {};
    if (this.statusFilter === 'active') {
      params.is_active = true;
    } else if (this.statusFilter === 'inactive') {
      params.is_active = false;
    }
    
    this.promotionService.getPromotions(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.promotions = response.promotions || [];
          this.applyFilters();
        } else {
          this.errorMessage = response.EM || 'Không thể tải danh sách mã khuyến mãi';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi tải danh sách mã khuyến mãi';
        console.error('Load promotions error:', error);
        this.isLoading = false;
      }
    });
  }

  applyFilters() {
    this.filteredPromotions = this.promotions.filter(promo => {
      const matchesSearch = !this.searchTerm || 
        promo.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        promo.description.toLowerCase().includes(this.searchTerm.toLowerCase());
      
      return matchesSearch;
    });
  }

  onFilterChange() {
    this.applyFilters();
  }

  openAddModal() {
    this.currentPromotion = {
      name: '',
      description: '',
      discount_type: 'PERCENTAGE',
      discount_value: 0,
      start_date: '',
      end_date: '',
      quantity: 0,
      is_active: true
    };
    this.showAddModal = true;
    this.errorMessage = '';
  }

  closeAddModal() {
    this.showAddModal = false;
    this.currentPromotion = {};
  }

  openEditModal(promo: Promotion) {
    this.editPromotion = { ...promo };
    this.showEditModal = true;
    this.errorMessage = '';
  }

  closeEditModal() {
    this.showEditModal = false;
    this.editPromotion = null;
  }

  savePromotion() {
    if (!this.validatePromotion()) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    
    const data: PromotionCreateRequest = {
      name: this.currentPromotion.name!,
      description: this.currentPromotion.description!,
      discount_type: this.currentPromotion.discount_type as 'PERCENTAGE' | 'FIXED',
      discount_value: this.currentPromotion.discount_value!,
      start_date: this.formatDateTime(this.currentPromotion.start_date!),
      end_date: this.formatDateTime(this.currentPromotion.end_date!),
      quantity: this.currentPromotion.quantity!,
      is_active: this.currentPromotion.is_active!
    };
    
    this.promotionService.createPromotion(data).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.successMessage = 'Tạo mã khuyến mãi thành công';
          this.loadPromotions();
          this.closeAddModal();
          setTimeout(() => this.successMessage = '', 3000);
        } else {
          this.errorMessage = response.EM || 'Không thể tạo mã khuyến mãi';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi tạo mã khuyến mãi';
        console.error('Create promotion error:', error);
        this.isLoading = false;
      }
    });
  }

  confirmDelete(promotionId: string) {
    this.deleteId = promotionId;
    this.showDeleteModal = true;
  }

  closeDeleteModal() {
    this.showDeleteModal = false;
    this.deleteId = '';
  }

  deletePromotion() {
    if (!this.deleteId) return;

    this.isLoading = true;
    this.errorMessage = '';

    this.promotionService.deletePromotion(this.deleteId).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.successMessage = 'Xóa mã khuyến mãi thành công';
          this.closeDeleteModal();
          // Reload sau khi đóng modal để tránh lỗi UI
          setTimeout(() => {
            this.loadPromotions();
          }, 100);
          setTimeout(() => this.successMessage = '', 3000);
        } else {
          this.errorMessage = response.EM || 'Không thể xóa mã khuyến mãi. Có thể mã này đã được sử dụng.';
          this.closeDeleteModal();
        }
        this.isLoading = false;
      },
      error: (error) => {
        const errorMsg = error?.error?.EM || error?.message || 'Lỗi khi xóa mã khuyến mãi. Mã này có thể đã được sử dụng bởi người dùng.';
        this.errorMessage = errorMsg;
        console.error('Delete promotion error:', error);
        this.isLoading = false;
        this.closeDeleteModal();
      }
    });
  }

  toggleStatus(promo: Promotion) {
    this.isLoading = true;
    this.errorMessage = '';

    const data: PromotionUpdateRequest = {
      is_active: !promo.is_active
    };

    this.promotionService.updatePromotion(promo.promotion_id, data).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.successMessage = 'Cập nhật trạng thái thành công';
          this.loadPromotions();
          setTimeout(() => this.successMessage = '', 3000);
        } else {
          this.errorMessage = response.EM || 'Không thể cập nhật trạng thái';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi cập nhật trạng thái';
        console.error('Toggle status error:', error);
        this.isLoading = false;
      }
    });
  }

  validatePromotion(): boolean {
    if (!this.currentPromotion.name?.trim()) {
      this.errorMessage = 'Vui lòng nhập tên mã khuyến mãi';
      return false;
    }
    if (!this.currentPromotion.description?.trim()) {
      this.errorMessage = 'Vui lòng nhập mô tả';
      return false;
    }
    if (!this.currentPromotion.discount_value || this.currentPromotion.discount_value <= 0) {
      this.errorMessage = 'Giá trị giảm giá phải lớn hơn 0';
      return false;
    }
    if (this.currentPromotion.discount_type === 'PERCENTAGE' && this.currentPromotion.discount_value > 100) {
      this.errorMessage = 'Giảm giá phần trăm không được vượt quá 100%';
      return false;
    }
    if (!this.currentPromotion.start_date) {
      this.errorMessage = 'Vui lòng chọn ngày bắt đầu';
      return false;
    }
    if (!this.currentPromotion.end_date) {
      this.errorMessage = 'Vui lòng chọn ngày kết thúc';
      return false;
    }
    if (new Date(this.currentPromotion.start_date) >= new Date(this.currentPromotion.end_date)) {
      this.errorMessage = 'Ngày kết thúc phải sau ngày bắt đầu';
      return false;
    }
    if (!this.currentPromotion.quantity || this.currentPromotion.quantity <= 0) {
      this.errorMessage = 'Số lượng phải lớn hơn 0';
      return false;
    }
    return true;
  }

  updatePromotion() {
    if (!this.validateEditPromotion()) {
      return;
    }

    if (!this.editPromotion) return;

    this.isLoading = true;
    this.errorMessage = '';

    const data: PromotionUpdateRequest = {
      name: this.editPromotion.name,
      description: this.editPromotion.description,
      discount_type: this.editPromotion.discount_type as 'PERCENTAGE' | 'FIXED',
      discount_value: this.editPromotion.discount_value,
      start_date: this.formatDateTime(this.editPromotion.start_date),
      end_date: this.formatDateTime(this.editPromotion.end_date),
      quantity: this.editPromotion.quantity,
      is_active: this.editPromotion.is_active
    };

    this.promotionService.updatePromotion(this.editPromotion.promotion_id, data).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.successMessage = 'Cập nhật mã khuyến mãi thành công';
          this.loadPromotions();
          this.closeEditModal();
          setTimeout(() => this.successMessage = '', 3000);
        } else {
          this.errorMessage = response.EM || 'Không thể cập nhật mã khuyến mãi';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi cập nhật mã khuyến mãi';
        console.error('Update promotion error:', error);
        this.isLoading = false;
      }
    });
  }

  validateEditPromotion(): boolean {
    if (!this.editPromotion) return false;

    if (!this.editPromotion.name?.trim()) {
      this.errorMessage = 'Vui lòng nhập tên mã khuyến mãi';
      return false;
    }
    if (!this.editPromotion.description?.trim()) {
      this.errorMessage = 'Vui lòng nhập mô tả';
      return false;
    }
    if (!this.editPromotion.discount_value || this.editPromotion.discount_value <= 0) {
      this.errorMessage = 'Giá trị giảm giá phải lớn hơn 0';
      return false;
    }
    if (this.editPromotion.discount_type === 'PERCENTAGE' && this.editPromotion.discount_value > 100) {
      this.errorMessage = 'Giảm giá phần trăm không được vượt quá 100%';
      return false;
    }
    if (!this.editPromotion.start_date) {
      this.errorMessage = 'Vui lòng chọn ngày bắt đầu';
      return false;
    }
    if (!this.editPromotion.end_date) {
      this.errorMessage = 'Vui lòng chọn ngày kết thúc';
      return false;
    }
    if (new Date(this.editPromotion.start_date) >= new Date(this.editPromotion.end_date)) {
      this.errorMessage = 'Ngày kết thúc phải sau ngày bắt đầu';
      return false;
    }
    if (!this.editPromotion.quantity || this.editPromotion.quantity <= 0) {
      this.errorMessage = 'Số lượng phải lớn hơn 0';
      return false;
    }
    return true;
  }
  formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toISOString();
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('vi-VN');
  }

  formatDiscount(promo: Promotion): string {
    if (promo.discount_type === 'PERCENTAGE') {
      return `Giảm ${promo.discount_value}%`;
    } else {
      return `Giảm ${this.formatPrice(promo.discount_value)}`;
    }
  }

  // Stats methods
  getActivePromotions(): number {
    return this.promotions.filter(promo => promo.is_active).length;
  }

  getInactivePromotions(): number {
    return this.promotions.filter(promo => !promo.is_active).length;
  }

  getAverageDiscount(): string {
    if (this.promotions.length === 0) return '0%';
    
    const percentagePromotions = this.promotions.filter(p => p.discount_type === 'PERCENTAGE');
    if (percentagePromotions.length === 0) return 'N/A';
    
    const total = percentagePromotions.reduce((sum, promo) => sum + promo.discount_value, 0);
    const average = total / percentagePromotions.length;
    return `${average.toFixed(1)}%`;
  }

  // Advanced Filter Methods
  applyDiscountFilter() {
    if (!this.minDiscountFilter && !this.maxDiscountFilter) {
      this.errorMessage = 'Vui lòng nhập giá trị giảm tối thiểu hoặc tối đa';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const params: any = { limit: 100 };

    if (this.minDiscountFilter) params.min_discount_value = Number(this.minDiscountFilter);
    if (this.maxDiscountFilter) params.max_discount_value = Number(this.maxDiscountFilter);
    if (this.statusFilter === 'active') params.is_active = true;
    else if (this.statusFilter === 'inactive') params.is_active = false;

    this.promotionService.filterByDiscount(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.promotions = response.promotions || [];
          this.applyFilters();
          this.isDiscountFilterActive = true;
        } else {
          this.errorMessage = response.EM || 'Không thể lọc theo giá trị giảm';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi lọc theo giá trị giảm';
        console.error('Filter by discount error:', error);
        this.isLoading = false;
      }
    });
  }

  clearDiscountFilter() {
    this.minDiscountFilter = '';
    this.maxDiscountFilter = '';
    this.isDiscountFilterActive = false;
    this.loadPromotions();
  }

  applyDateRangeFilter() {
    if (!this.startDateFilter && !this.endDateFilter) {
      this.errorMessage = 'Vui lòng nhập ngày bắt đầu hoặc ngày kết thúc';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const params: any = { limit: 100 };

    if (this.startDateFilter) params.start_date = this.startDateFilter;
    if (this.endDateFilter) params.end_date = this.endDateFilter;
    if (this.statusFilter === 'active') params.is_active = true;
    else if (this.statusFilter === 'inactive') params.is_active = false;

    this.promotionService.filterByDateRange(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.promotions = response.promotions || [];
          this.applyFilters();
          this.isDateRangeFilterActive = true;
        } else {
          this.errorMessage = response.EM || 'Không thể lọc theo ngày';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi lọc theo ngày';
        console.error('Filter by date range error:', error);
        this.isLoading = false;
      }
    });
  }

  clearDateRangeFilter() {
    this.startDateFilter = '';
    this.endDateFilter = '';
    this.isDateRangeFilterActive = false;
    this.loadPromotions();
  }

  applyQuantityFilter() {
    if (!this.minQuantityFilter && !this.maxQuantityFilter) {
      this.errorMessage = 'Vui lòng nhập số lượng tối thiểu hoặc tối đa';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const params: any = { limit: 100 };

    if (this.minQuantityFilter) params.min_quantity = Number(this.minQuantityFilter);
    if (this.maxQuantityFilter) params.max_quantity = Number(this.maxQuantityFilter);
    if (this.statusFilter === 'active') params.is_active = true;
    else if (this.statusFilter === 'inactive') params.is_active = false;

    this.promotionService.filterByQuantity(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.promotions = response.promotions || [];
          this.applyFilters();
          this.isQuantityFilterActive = true;
        } else {
          this.errorMessage = response.EM || 'Không thể lọc theo số lượng';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi lọc theo số lượng';
        console.error('Filter by quantity error:', error);
        this.isLoading = false;
      }
    });
  }

  clearQuantityFilter() {
    this.minQuantityFilter = '';
    this.maxQuantityFilter = '';
    this.isQuantityFilterActive = false;
    this.loadPromotions();
  }

  applyUserCountFilter() {
    if (!this.minUserCountFilter && !this.maxUserCountFilter) {
      this.errorMessage = 'Vui lòng nhập số lượt sử dụng tối thiểu hoặc tối đa';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const params: any = { limit: 100 };

    if (this.minUserCountFilter) params.min_user_count = Number(this.minUserCountFilter);
    if (this.maxUserCountFilter) params.max_user_count = Number(this.maxUserCountFilter);
    if (this.statusFilter === 'active') params.is_active = true;
    else if (this.statusFilter === 'inactive') params.is_active = false;

    this.promotionService.filterByUserCount(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.promotions = response.promotions || [];
          this.applyFilters();
          this.isUserCountFilterActive = true;
        } else {
          this.errorMessage = response.EM || 'Không thể lọc theo lượt sử dụng';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi lọc theo lượt sử dụng';
        console.error('Filter by user count error:', error);
        this.isLoading = false;
      }
    });
  }

  clearUserCountFilter() {
    this.minUserCountFilter = '';
    this.maxUserCountFilter = '';
    this.isUserCountFilterActive = false;
    this.loadPromotions();
  }
}

