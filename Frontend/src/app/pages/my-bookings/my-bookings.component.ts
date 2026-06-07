import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, NavigationEnd } from '@angular/router';
import { filter, Subscription } from 'rxjs';
import { BookingService, MyBooking, MyBookingDetail, BookingUpdateRequest } from '../../services/booking.service';
import { PaymentService, PaymentData } from '../../services/payment.service';

@Component({
  selector: 'app-my-bookings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './my-bookings.component.html',
  styleUrl: './my-bookings.component.scss'
})
export class MyBookingsComponent implements OnInit, OnDestroy {
  bookings: MyBooking[] = [];
  filteredBookings: MyBooking[] = [];
  isLoading = false;
  errorMessage = '';

  statusFilter: 'pending' | 'otp_sent' | 'confirmed' | 'cancelled' | 'completed' | '' = '';
  currentPage = 1;
  pageSize = 10;
  total = 0;

  showDetailModal = false;
  bookingDetail: MyBookingDetail | null = null;
  isLoadingDetail = false;
  detailErrorMessage = '';
  paymentInfo: PaymentData | null = null;
  isLoadingPayment = false;

  showEditModal = false;
  showDeleteConfirm = false;
  bookingToDelete: string | null = null;
  isDeleting = false;
  isUpdating = false;
  updateErrorMessage = '';
  updateSuccessMessage = '';

  isProcessingPayment: Set<string> = new Set();
  paymentErrorMessage: Map<string, string> = new Map();

  editForm: BookingUpdateRequest = {
    number_of_people: 0,
    contact_phone: '',
    contact_name: '',
    special_requests: '',
    status: ''
  };

  stats = {
    total: 0,
    pending: 0,
    otp_sent: 0,
    confirmed: 0,
    cancelled: 0,
    completed: 0
  };

  // Store all bookings for stats calculation
  private allBookings: MyBooking[] = [];
  private routerSubscription?: Subscription;

  constructor(
    private bookingService: BookingService,
    private paymentService: PaymentService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.loadAllStats(); // Load stats first
    this.loadBookings();

    // Subscribe to router events to refresh data when navigating to this page
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        // Only refresh if we're on the my-bookings route
        if (event.url === '/my-bookings' || event.urlAfterRedirects === '/my-bookings') {
          this.refreshAll();
        }
      });
  }

  ngOnDestroy(): void {
    if (this.routerSubscription) {
      this.routerSubscription.unsubscribe();
    }
  }

  // Load all bookings for stats (no filter)
  loadAllStats(): void {
    // Call API with high limit to get all bookings for stats
    this.bookingService.getMyBookings({ limit: 100, offset: 0 }).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.allBookings = response.data || [];
          this.calculateStats();
        }
      },
      error: (error) => {
        // Silent fail for stats - main list will still show
      }
    });
  }

  loadBookings(): void {
    this.isLoading = true;
    this.errorMessage = '';

    const params: any = {
      limit: this.pageSize,
      offset: (this.currentPage - 1) * this.pageSize
    };

    if (this.statusFilter) {
      params.status = this.statusFilter;
    }

    this.bookingService.getMyBookings(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.bookings = response.data || [];
          this.total = response.total || 0;
          this.filteredBookings = this.bookings;
        } else {
          this.errorMessage = response.EM || 'Có lỗi xảy ra khi tải danh sách đơn hàng';
          this.bookings = [];
          this.filteredBookings = [];
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading bookings:', error);
        this.errorMessage = 'Không thể tải danh sách đơn hàng. Vui lòng thử lại sau.';
        this.bookings = [];
        this.filteredBookings = [];
        this.isLoading = false;
      }
    });
  }

  onStatusFilterChange(): void {
    this.currentPage = 1;
    this.loadBookings();
  }

  calculateStats(): void {
    this.stats.total = this.allBookings.length;
    this.stats.pending = this.allBookings.filter(b => b.status === 'pending').length;
    this.stats.otp_sent = this.allBookings.filter(b => b.status === 'otp_sent').length;
    this.stats.confirmed = this.allBookings.filter(b => b.status === 'confirmed').length;
    this.stats.cancelled = this.allBookings.filter(b => b.status === 'cancelled').length;
    this.stats.completed = this.allBookings.filter(b => b.status === 'completed').length;
  }

  calculateTotalSpent(): number {
    return this.allBookings
      .filter(b => b.status === 'completed' || b.status === 'confirmed')
      .reduce((sum, b) => sum + b.total_amount, 0);
  }

  getDuration(start: string, end: string): number {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays + 1;
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'confirmed': 'bg-blue-100 text-blue-800',
      'cancelled': 'bg-red-100 text-red-800',
      'completed': 'bg-green-100 text-green-800',
      'otp_sent': 'bg-purple-100 text-purple-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  }

  getStatusText(status: string): string {
    const texts: { [key: string]: string } = {
      'pending': 'Chờ xử lý',
      'confirmed': 'Đã xác nhận',
      'cancelled': 'Đã hủy',
      'completed': 'Hoàn thành',
      'otp_sent': 'Chờ xác thực OTP'
    };
    return texts[status] || status;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(date);
  }

  getTotalPages(): number {
    return Math.ceil(this.total / this.pageSize);
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.getTotalPages()) {
      this.currentPage = page;
      this.loadBookings();
    }
  }

  refresh(): void {
    this.loadBookings();
    this.loadAllStats();
  }

  // Helper method to refresh both bookings list and stats
  refreshAll(): void {
    this.loadBookings();
    this.loadAllStats();
  }

  getPageNumbers(): number[] {
    const totalPages = this.getTotalPages();
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  getDisplayRange(): string {
    const start = (this.currentPage - 1) * this.pageSize + 1;
    const end = Math.min(this.currentPage * this.pageSize, this.total);
    return `${start} - ${end}`;
  }

  openDetailModal(bookingId: string): void {
    this.showDetailModal = true;
    this.isLoadingDetail = true;
    this.detailErrorMessage = '';
    this.bookingDetail = null;
    this.paymentInfo = null;

    this.bookingService.getMyBookingDetail(bookingId).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.bookingDetail = response.data;
          this.loadPaymentInfo(bookingId);
        } else {
          this.detailErrorMessage = response.EM || 'Không thể tải chi tiết đơn hàng';
        }
        this.isLoadingDetail = false;
      },
      error: (error) => {
        console.error('Error loading booking detail:', error);
        this.detailErrorMessage = 'Không thể tải chi tiết đơn hàng. Vui lòng thử lại sau.';
        this.isLoadingDetail = false;
      }
    });
  }

  loadPaymentInfo(bookingId: string): void {
    this.isLoadingPayment = true;
    this.paymentService.getPaymentByBookingId(bookingId).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.paymentInfo = response.data;
        }
        this.isLoadingPayment = false;
      },
      error: (error) => {
        console.error('Error loading payment info:', error);
        this.isLoadingPayment = false;
      }
    });
  }

  closeDetailModal(): void {
    this.showDetailModal = false;
    this.bookingDetail = null;
    this.detailErrorMessage = '';
    this.paymentInfo = null;
  }

  formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  getDescriptionParts(description: string): { main: string; note: string } {
    if (!description) return { main: '', note: '' };

    const noteIndex = description.indexOf('Lưu ý:');
    if (noteIndex === -1) {
      return { main: description, note: '' };
    }

    return {
      main: description.substring(0, noteIndex).trim(),
      note: description.substring(noteIndex).trim()
    };
  }

  openEditModal(bookingId: string): void {
    if (this.showDetailModal) {
      this.closeDetailModal();
    }

    this.showEditModal = true;
    this.updateErrorMessage = '';
    this.updateSuccessMessage = '';
    this.bookingDetail = null;

    this.bookingService.getMyBookingDetail(bookingId).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          this.bookingDetail = response.data;
          this.editForm = {
            number_of_people: response.data.number_of_people,
            contact_phone: response.data.contact_phone,
            contact_name: response.data.contact_name,
            special_requests: response.data.special_requests || '',
            status: response.data.status
          };
        } else {
          this.updateErrorMessage = response.EM || 'Không thể tải thông tin đơn hàng';
        }
      },
      error: (error) => {
        console.error('Error loading booking detail:', error);
        this.updateErrorMessage = 'Không thể tải thông tin đơn hàng. Vui lòng thử lại sau.';
      }
    });
  }

  closeEditModal(): void {
    this.showEditModal = false;
    this.bookingDetail = null;
    this.updateErrorMessage = '';
    this.updateSuccessMessage = '';
    this.editForm = {
      number_of_people: 0,
      contact_phone: '',
      contact_name: '',
      special_requests: '',
      status: ''
    };
  }

  updateBooking(): void {
    if (!this.bookingDetail) return;

    if (!this.editForm.contact_phone?.trim()) {
      this.updateErrorMessage = 'Vui lòng nhập số điện thoại';
      return;
    }

    if (!this.editForm.contact_name?.trim()) {
      this.updateErrorMessage = 'Vui lòng nhập tên người liên hệ';
      return;
    }

    this.isUpdating = true;
    this.updateErrorMessage = '';
    this.updateSuccessMessage = '';

    const updateData: BookingUpdateRequest = {
      // number_of_people is not included - users cannot change the number of slots after booking
      contact_phone: this.editForm.contact_phone,
      contact_name: this.editForm.contact_name,
      special_requests: this.editForm.special_requests || undefined
    };

    if (this.editForm.status && this.bookingDetail.status !== this.editForm.status) {
      updateData.status = this.editForm.status;
    }

    this.bookingService.updateBooking(this.bookingDetail.booking_id, updateData).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.updateSuccessMessage = 'Cập nhật đơn hàng thành công!';
          setTimeout(() => {
            const bookingId = this.bookingDetail!.booking_id;
            this.closeEditModal();
            this.refreshAll(); // Refresh both bookings and stats
          }, 1500);
        } else {
          this.updateErrorMessage = response.EM || 'Không thể cập nhật đơn hàng';
        }
        this.isUpdating = false;
      },
      error: (error) => {
        console.error('Error updating booking:', error);
        this.updateErrorMessage = 'Có lỗi xảy ra khi cập nhật đơn hàng. Vui lòng thử lại sau.';
        this.isUpdating = false;
      }
    });
  }

  confirmDelete(bookingId: string): void {
    this.bookingToDelete = bookingId;
    this.showDeleteConfirm = true;
  }

  cancelDelete(): void {
    this.showDeleteConfirm = false;
    this.bookingToDelete = null;
  }

  deleteBooking(): void {
    if (!this.bookingToDelete) return;

    this.isDeleting = true;
    this.errorMessage = '';

    this.bookingService.deleteBooking(this.bookingToDelete).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.showDeleteConfirm = false;
          this.bookingToDelete = null;
          this.refreshAll(); // Refresh both bookings and stats
          if (this.showDetailModal) {
            this.closeDetailModal();
          }
        } else {
          this.errorMessage = response.EM || 'Không thể xóa đơn hàng';
        }
        this.isDeleting = false;
      },
      error: (error) => {
        console.error('Error deleting booking:', error);
        this.errorMessage = 'Có lỗi xảy ra khi xóa đơn hàng. Vui lòng thử lại sau.';
        this.isDeleting = false;
      }
    });
  }

  canEditBooking(status: string): boolean {
    return status === 'pending' || status === 'confirmed';
  }

  canDeleteBooking(status: string): boolean {
    return status === 'pending' || status === 'confirmed';
  }

  canPayBooking(status: string): boolean {
    return status === 'pending';
  }

  processPayment(bookingId: string): void {
    if (this.isProcessingPayment.has(bookingId)) {
      return;
    }

    this.isProcessingPayment.add(bookingId);
    this.paymentErrorMessage.delete(bookingId);

    const paymentRequest = {
      booking_id: bookingId,
      payment_method: 'vnpay'
    };

    this.paymentService.createPayment(paymentRequest).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data.payment_url) {
          console.log('Payment URL created:', response.data.payment_url);
          console.log('Payment data:', response.data);
          window.location.href = response.data.payment_url;
        } else {
          this.paymentErrorMessage.set(bookingId, response.EM || 'Không thể tạo yêu cầu thanh toán');
          this.isProcessingPayment.delete(bookingId);
        }
      },
      error: (error) => {
        console.error('Error creating payment:', error);
        console.error('Error details:', error.error);
        this.paymentErrorMessage.set(bookingId, 'Có lỗi xảy ra khi tạo yêu cầu thanh toán. Vui lòng thử lại sau.');
        this.isProcessingPayment.delete(bookingId);
      }
    });
  }

  isBookingProcessingPayment(bookingId: string): boolean {
    return this.isProcessingPayment.has(bookingId);
  }

  getPaymentErrorMessage(bookingId: string): string {
    return this.paymentErrorMessage.get(bookingId) || '';
  }
}
