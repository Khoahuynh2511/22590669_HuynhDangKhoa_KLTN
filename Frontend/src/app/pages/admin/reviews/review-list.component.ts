import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminReviewService, Review, ReviewDetail } from '../../../services/admin/admin-review.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';
import { AdminBookingService, AdminBookingDetail } from '../../../services/admin/admin-booking.service';
import { AdminTourService, TourPackage } from '../../../services/admin/admin-tour.service';

@Component({
  selector: 'app-review-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './review-list.component.html',
  styleUrls: ['./review-list.component.scss']
})
export class ReviewListComponent implements OnInit {
  // Reviews list
  allReviews: Review[] = [];
  filteredReviews: Review[] = [];
  pendingReviews: Review[] = [];
  
  // Loading states
  isLoadingReviews: boolean = false;
  isLoadingPending: boolean = false;
  isApproving: boolean = false;
  isDeleting: boolean = false;
  
  // Filters
  filterStatus: 'all' | 'pending' | 'approved' | 'rejected' = 'all';
  filterRating: number | null = null;
  searchTerm: string = '';
  filterUserId: string = '';
  filterPackageId: string = '';
  
  // Pagination
  currentPage: number = 0;
  pageSize: number = 20;
  totalReviews: number = 0;
  
  // Selected review
  selectedReview: ReviewDetail | null = null;
  showDetailModal: boolean = false;
  showDeleteConfirmModal: boolean = false;
  
  // Add review modal
  showAddModal: boolean = false;
  isCreating: boolean = false;
  newReview: any = {
    booking_id: '',
    package_id: '',
    rating: 5,
    comment: ''
  };
  
  // Fetched info for creating review
  selectedBookingInfo: AdminBookingDetail | null = null;
  selectedPackageInfo: TourPackage | null = null;
  isFetchingBooking: boolean = false;
  isFetchingPackage: boolean = false;
  
  // Messages
  errorMessage: string = '';
  successMessage: string = '';
  
  // Active tab
  activeTab: 'all' | 'pending' = 'all';

  // Expose Math to template
  Math = Math;

  constructor(
    private reviewService: AdminReviewService,
    private dialogService: AdminDialogService,
    private bookingService: AdminBookingService,
    private tourService: AdminTourService
  ) {}

  ngOnInit() {
    this.loadAllReviews();
    this.loadPendingReviews();
  }

  /**
   * Load all reviews
   */
  async loadAllReviews() {
    this.isLoadingReviews = true;
    this.errorMessage = '';
    
    try {
      const params: any = {
        limit: this.pageSize,
        offset: this.currentPage * this.pageSize
      };
      
      if (this.filterRating) {
        params.rating = this.filterRating;
      }
      
      if (this.filterUserId) {
        params.user_id = this.filterUserId;
      }
      
      if (this.filterPackageId) {
        params.package_id = this.filterPackageId;
      }
      
      if (this.filterStatus === 'approved') {
        params.is_approved = true;
      } else if (this.filterStatus === 'rejected') {
        params.is_approved = false;
      }
      
      const response = await this.reviewService.getAllReviewsAdmin(params).toPromise();
      
      if (response?.EC === 0) {
        this.allReviews = response.data;
        this.totalReviews = response.total;
        this.filterReviews();
      } else {
        this.errorMessage = response?.EM || 'Không thể tải danh sách reviews';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi tải danh sách reviews';
      console.error('Error loading reviews:', error);
    } finally {
      this.isLoadingReviews = false;
    }
  }

  /**
   * Load pending reviews
   */
  async loadPendingReviews() {
    this.isLoadingPending = true;
    
    try {
      const response = await this.reviewService.getPendingReviews({ limit: 100 }).toPromise();
      
      if (response?.EC === 0) {
        this.pendingReviews = response.data;
      }
    } catch (error: any) {
      console.error('Error loading pending reviews:', error);
    } finally {
      this.isLoadingPending = false;
    }
  }

  /**
   * Filter reviews by search term
   */
  filterReviews() {
    const term = this.searchTerm.toLowerCase().trim();
    if (!term) {
      this.filteredReviews = [...this.allReviews];
      return;
    }
    
    this.filteredReviews = this.allReviews.filter(review =>
      review.comment.toLowerCase().includes(term) ||
      review.review_id.toLowerCase().includes(term) ||
      review.user_id.toLowerCase().includes(term) ||
      review.package_id.toLowerCase().includes(term)
    );
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'all' | 'pending') {
    this.activeTab = tab;
    if (tab === 'pending' && this.pendingReviews.length === 0) {
      this.loadPendingReviews();
    }
  }

  /**
   * Apply filters
   */
  applyFilters() {
    this.currentPage = 0;
    this.loadAllReviews();
  }

  /**
   * Reload data from API
   */
  reloadData() {
    this.loadAllReviews();
    this.loadPendingReviews();
  }

  /**
   * Clear filters
   */
  clearFilters() {
    this.filterStatus = 'all';
    this.filterRating = null;
    this.searchTerm = '';
    this.filterUserId = '';
    this.filterPackageId = '';
    this.applyFilters();
  }

  /**
   * Change page
   */
  changePage(page: number) {
    const totalPages = Math.ceil(this.totalReviews / this.pageSize);
    if (page < 0 || page >= totalPages) return;
    
    this.currentPage = page;
    this.loadAllReviews();
  }

  /**
   * View review details
   */
  async viewReviewDetails(review: Review) {
    try {
      const response = await this.reviewService.getReview(review.review_id).toPromise();
      if (response?.EC === 0 && response?.data) {
        this.selectedReview = response.data;
        this.showDetailModal = true;
      }
    } catch (error: any) {
      this.errorMessage = 'Không thể tải chi tiết review';
      console.error('Error loading review details:', error);
    }
  }

  /**
   * Close detail modal
   */
  closeDetailModal() {
    this.showDetailModal = false;
    this.selectedReview = null;
  }

  /**
   * Approve review
   */
  async approveReview(review: Review, approve: boolean) {
    const confirmed = await this.dialogService.confirm({
      title: approve ? 'Phê duyệt review' : 'Từ chối review',
      message: `Bạn có chắc chắn muốn ${approve ? 'phê duyệt' : 'từ chối'} review này?`,
      confirmText: approve ? 'Phê duyệt' : 'Từ chối',
      cancelText: 'Hủy'
    });
    
    if (!confirmed) {
      return;
    }
    
    this.isApproving = true;
    this.errorMessage = '';
    
    try {
      const response = await this.reviewService.approveReview(review.review_id, {
        is_approved: approve
      }).toPromise();
      
      if (response?.EC === 0) {
        this.successMessage = `${approve ? 'Phê duyệt' : 'Từ chối'} review thành công!`;
        await this.loadAllReviews();
        await this.loadPendingReviews();
        setTimeout(() => this.successMessage = '', 3000);
      } else {
        this.errorMessage = response?.EM || `Không thể ${approve ? 'phê duyệt' : 'từ chối'} review`;
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi cập nhật review';
      console.error('Error approving review:', error);
    } finally {
      this.isApproving = false;
    }
  }

  /**
   * Open delete confirm modal
   */
  openDeleteConfirmModal(review: Review) {
    this.selectedReview = review as ReviewDetail;
    this.showDeleteConfirmModal = true;
  }

  /**
   * Close delete confirm modal
   */
  closeDeleteConfirmModal() {
    this.showDeleteConfirmModal = false;
    this.selectedReview = null;
  }

  /**
   * Delete review
   */
  async deleteReview() {
    if (!this.selectedReview) return;
    
    this.isDeleting = true;
    this.errorMessage = '';
    
    try {
      const response = await this.reviewService.deleteReview(this.selectedReview.review_id).toPromise();
      
      if (response?.EC === 0) {
        this.successMessage = 'Xóa review thành công!';
        this.closeDeleteConfirmModal();
        await this.loadAllReviews();
        await this.loadPendingReviews();
        setTimeout(() => this.successMessage = '', 3000);
      } else {
        this.errorMessage = response?.EM || 'Không thể xóa review';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi xóa review';
      console.error('Error deleting review:', error);
    } finally {
      this.isDeleting = false;
    }
  }

  /**
   * Format date
   */
  formatDate(dateString: string): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN');
  }

  /**
   * Get rating stars
   */
  getStars(rating: number): string[] {
    return Array(5).fill('').map((_, i) => i < rating ? 'full' : 'empty');
  }

  /**
   * Get status badge class
   */
  getStatusBadgeClass(isApproved: boolean): string {
    return isApproved ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800';
  }

  /**
   * Open add modal
   */
  openAddModal() {
    this.newReview = {
      booking_id: '',
      package_id: '',
      rating: 5,
      comment: ''
    };
    this.showAddModal = true;
  }

  /**
   * Close add modal
   */
  closeAddModal() {
    this.showAddModal = false;
    this.newReview = {
      booking_id: '',
      package_id: '',
      rating: 5,
      comment: ''
    };    this.selectedBookingInfo = null;
    this.selectedPackageInfo = null;  }

  /**
   * Create review
   */
  async createReview() {
    if (!this.newReview.booking_id || !this.newReview.package_id || !this.newReview.comment) {
      await this.dialogService.alert('Lỗi', 'Vui lòng điền đầy đủ thông tin!');
      return;
    }

    this.isCreating = true;
    this.errorMessage = '';

    try {
      const response = await this.reviewService.createReview(this.newReview).toPromise();

      if (response?.EC === 0) {
        await this.dialogService.alert('Thành công', 'Tạo review mới thành công!');
        this.closeAddModal();
        await this.loadAllReviews();
        await this.loadPendingReviews();
      } else {
        this.errorMessage = response?.EM || 'Không thể tạo review';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.EM || 'Lỗi khi tạo review';
    } finally {
      this.isCreating = false;
    }
  }

  /**
   * Get status text
   */
  getStatusText(isApproved: boolean): string {
    return isApproved ? 'Đã phê duyệt' : 'Chờ phê duyệt';
  }

  /**
   * Get total pages
   */
  getTotalPages(): number {
    return Math.ceil(this.totalReviews / this.pageSize);
  }

  /**
   * Get page numbers
   */
  getPageNumbers(): number[] {
    const total = this.getTotalPages();
    const pages: number[] = [];
    const maxPages = 5;
    
    let start = Math.max(0, this.currentPage - Math.floor(maxPages / 2));
    let end = Math.min(total, start + maxPages);
    
    if (end - start < maxPages) {
      start = Math.max(0, end - maxPages);
    }
    
    for (let i = start; i < end; i++) {
      pages.push(i);
    }
    
    return pages;
  }

  /**
   * Get approved reviews count
   */
  getApprovedReviews(): number {
    return this.allReviews.filter(r => r.is_approved).length;
  }

  /**
   * Get average rating
   */
  getAverageRating(): string {
    if (this.allReviews.length === 0) return '0.0';
    const sum = this.allReviews.reduce((acc, r) => acc + r.rating, 0);
    return (sum / this.allReviews.length).toFixed(1);
  }

  /**
   * Fetch booking info when booking_id is entered
   */
  async onBookingIdChange() {
    const bookingId = this.newReview.booking_id?.trim();
    
    if (!bookingId) {
      this.selectedBookingInfo = null;
      return;
    }

    this.isFetchingBooking = true;
    
    try {
      const response = await this.bookingService.getBookingDetailAdmin(bookingId).toPromise();
      
      if (response?.EC === 0 && response.data) {
        this.selectedBookingInfo = response.data;
        // Auto-fill package_id from booking
        if (response.data.tour_package?.package_id) {
          this.newReview.package_id = response.data.tour_package.package_id;
          await this.onPackageIdChange();
        }
      } else {
        this.selectedBookingInfo = null;
        await this.dialogService.alert('Thông báo', 'Không tìm thấy booking với ID này');
      }
    } catch (error: any) {
      this.selectedBookingInfo = null;
      console.error('Error fetching booking:', error);
    } finally {
      this.isFetchingBooking = false;
    }
  }

  /**
   * Fetch package info when package_id is entered
   */
  async onPackageIdChange() {
    const packageId = this.newReview.package_id?.trim();
    
    if (!packageId) {
      this.selectedPackageInfo = null;
      return;
    }

    this.isFetchingPackage = true;
    
    try {
      const response = await this.tourService.getTourPackageById(packageId);
      
      if (response?.EC === 0 && response.package) {
        this.selectedPackageInfo = response.package;
      } else {
        this.selectedPackageInfo = null;
        await this.dialogService.alert('Thông báo', 'Không tìm thấy tour package với ID này');
      }
    } catch (error: any) {
      this.selectedPackageInfo = null;
      console.error('Error fetching package:', error);
    } finally {
      this.isFetchingPackage = false;
    }
  }

  /**
   * Format price for display
   */
  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }
}
