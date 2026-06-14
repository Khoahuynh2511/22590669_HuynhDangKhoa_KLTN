import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, NavigationEnd, ActivatedRoute } from '@angular/router';
import { filter, Subscription } from 'rxjs';
import { BookingService, MyBooking, MyBookingDetail, BookingUpdateRequest } from '../../services/booking.service';
import { PaymentService, PaymentData } from '../../services/payment.service';
import { TrainBookingService } from '../../services/train-booking.service';
import { BusBookingService } from '../../services/bus-booking.service';
import { FlightBookingService } from '../../services/flight-booking.service';
import { HotelBookingService, HotelBookingDetail } from '../../services/hotel-booking.service';
import { FlightBookingDetail } from '../../services/flight-booking.service';
import { BusBookingDetail } from '../../services/bus-booking.service';
import { TrainBookingDetail } from '../../services/train-booking.service';

type TransportBookingDetail = FlightBookingDetail | BusBookingDetail | TrainBookingDetail | HotelBookingDetail;

@Component({
  selector: 'app-my-bookings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './my-bookings.component.html',
  styleUrl: './my-bookings.component.scss'
})
export class MyBookingsComponent implements OnInit, OnDestroy {
  activeTab: 'tour' | 'train' | 'bus' | 'flight' | 'hotel' = 'tour';

  bookings: MyBooking[] = [];
  filteredBookings: MyBooking[] = [];
  transportBookings: any[] = [];  // for train/bus/flight/hotel data
  isLoading = false;
  errorMessage = '';

  statusFilter: 'pending' | 'otp_sent' | 'confirmed' | 'cancelled' | 'completed' | '' = '';
  currentPage = 1;
  pageSize = 10;
  total = 0;

  showDetailModal = false;
  bookingDetail: MyBookingDetail | null = null;
  transportDetail: TransportBookingDetail | null = null;
  isLoadingDetail = false;
  detailErrorMessage = '';
  paymentInfo: PaymentData | null = null;
  isLoadingPayment = false;
  customItinerary: any = null;
  isCustomTrip = false;

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

  transportStats = {
    total: 0,
    active: 0,
    pending: 0,
    totalSpent: 0
  };

  // Store all bookings for stats calculation
  private allBookings: MyBooking[] = [];
  private routerSubscription?: Subscription;

  constructor(
    private bookingService: BookingService,
    private paymentService: PaymentService,
    private trainBookingService: TrainBookingService,
    private busBookingService: BusBookingService,
    private flightBookingService: FlightBookingService,
    private hotelBookingService: HotelBookingService,
    private router: Router,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    // Check query param for initial tab
    this.route.queryParams.subscribe(params => {
      const tab = params['tab'] as 'tour' | 'train' | 'bus' | 'flight' | 'hotel';
      if (tab && ['tour', 'train', 'bus', 'flight', 'hotel'].includes(tab)) {
        this.activeTab = tab;
      }
    });

    if (this.activeTab === 'tour') {
      this.loadAllStats(); // Load stats first
      this.loadBookings();
    } else {
      this.loadTransportBookings();
    }

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

  // Switch between booking type tabs
  switchTab(tab: 'tour' | 'train' | 'bus' | 'flight' | 'hotel'): void {
    this.activeTab = tab;
    this.currentPage = 1;
    this.statusFilter = '';
    this.errorMessage = '';
    if (tab === 'tour') {
      this.loadBookings();
      this.loadAllStats();
    } else {
      this.loadTransportBookings();
    }
  }

  // Load transport bookings (train/bus/flight/hotel)
  loadTransportBookings(): void {
    this.isLoading = true;
    this.errorMessage = '';

    let serviceCall: any;

    switch (this.activeTab) {
      case 'train':
        serviceCall = this.trainBookingService.getMyBookings();
        break;
      case 'bus':
        serviceCall = this.busBookingService.getMyBookings();
        break;
      case 'flight':
        serviceCall = this.flightBookingService.getMyBookings();
        break;
      case 'hotel':
        serviceCall = this.hotelBookingService.getMyBookings();
        break;
      default:
        this.isLoading = false;
        return;
    }

    serviceCall.subscribe({
      next: (response: any) => {
        if (response.EC === 0) {
          this.transportBookings = response.data || [];
          this.total = response.total || 0;
          this.calculateTransportStats();
        } else {
          this.errorMessage = response.EM || 'Có lỗi xảy ra khi tải danh sách đặt chỗ';
          this.transportBookings = [];
        }
        this.isLoading = false;
      },
      error: (error: any) => {
        console.error(`Error loading ${this.activeTab} bookings:`, error);
        this.errorMessage = 'Không thể tải danh sách đặt chỗ. Vui lòng thử lại sau.';
        this.transportBookings = [];
        this.isLoading = false;
      }
    });
  }

  // Cancel transport booking (train/bus/flight/hotel)
  cancelTransportBooking(bookingId: string | null): void {
    if (!bookingId) return;

    this.isDeleting = true;
    this.errorMessage = '';

    let serviceCall: any;

    switch (this.activeTab) {
      case 'train':
        serviceCall = this.trainBookingService.cancelBooking(bookingId);
        break;
      case 'bus':
        serviceCall = this.busBookingService.cancelBooking(bookingId);
        break;
      case 'flight':
        serviceCall = this.flightBookingService.cancelBooking(bookingId);
        break;
      case 'hotel':
        serviceCall = this.hotelBookingService.cancelBooking(bookingId);
        break;
      default:
        this.isDeleting = false;
        return;
    }

    serviceCall.subscribe({
      next: (response: any) => {
        if (response.EC === 0) {
          this.showDeleteConfirm = false;
          this.bookingToDelete = null;
          if (this.showDetailModal) {
            this.closeDetailModal();
          }
          this.loadTransportBookings();
        } else {
          this.errorMessage = response.EM || 'Không thể hủy đặt chỗ';
        }
        this.isDeleting = false;
      },
      error: (error: any) => {
        console.error(`Error cancelling ${this.activeTab} booking:`, error);
        this.errorMessage = 'Có lỗi xảy ra khi hủy đặt chỗ. Vui lòng thử lại sau.';
        this.isDeleting = false;
      }
    });
  }

  // Helper method to check if current tab is a transport booking
  isTransportTab(): boolean {
    return this.activeTab !== 'tour';
  }

  getTabLabel(tab: string): string {
    const labels: { [key: string]: string } = {
      'train': 'tàu hỏa',
      'bus': 'xe khách',
      'flight': 'máy bay',
      'hotel': 'khách sạn'
    };
    return labels[tab] || tab;
  }

  // Load all bookings for stats (no filter) - tour bookings only
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
    if (this.activeTab === 'tour') {
      this.loadBookings();
    } else {
      this.loadTransportBookings();
    }
  }

  calculateStats(): void {
    this.stats.total = this.allBookings.length;
    this.stats.pending = this.allBookings.filter(b => b.status === 'pending').length;
    this.stats.otp_sent = this.allBookings.filter(b => b.status === 'otp_sent').length;
    this.stats.confirmed = this.allBookings.filter(b => b.status === 'confirmed').length;
    this.stats.cancelled = this.allBookings.filter(b => b.status === 'cancelled').length;
    this.stats.completed = this.allBookings.filter(b => b.status === 'completed').length;
  }

  calculateTransportStats(): void {
    this.transportStats.total = this.transportBookings.length;
    this.transportStats.pending = this.transportBookings.filter(
      b => b.status === 'pending' || b.status === 'otp_sent'
    ).length;
    this.transportStats.active = this.transportBookings.filter(
      b => b.status === 'confirmed' || b.status === 'completed'
    ).length;
    this.transportStats.totalSpent = this.transportBookings
      .filter(b => b.status === 'confirmed' || b.status === 'completed')
      .reduce((sum, b) => sum + (b.total_price || 0), 0);
  }

  getActiveTabLabel(): string {
    const labels: Record<string, string> = {
      tour: 'Tour',
      train: 'Tàu hỏa',
      bus: 'Xe khách',
      flight: 'Máy bay',
      hotel: 'Khách sạn'
    };
    return labels[this.activeTab] || 'Đơn hàng';
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
      if (this.activeTab === 'tour') {
        this.loadBookings();
      } else {
        this.loadTransportBookings();
      }
    }
  }

  refresh(): void {
    if (this.activeTab === 'tour') {
      this.loadBookings();
      this.loadAllStats();
    } else {
      this.loadTransportBookings();
    }
  }

  // Helper method to refresh both bookings list and stats
  refreshAll(): void {
    if (this.activeTab === 'tour') {
      this.loadBookings();
      this.loadAllStats();
    } else {
      this.loadTransportBookings();
    }
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
    if (this.isTransportTab()) {
      this.openTransportDetailModal(bookingId);
      return;
    }

    this.showDetailModal = true;
    this.isLoadingDetail = true;
    this.detailErrorMessage = '';
    this.bookingDetail = null;
    this.transportDetail = null;
    this.paymentInfo = null;

    this.bookingService.getMyBookingDetail(bookingId).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.bookingDetail = response.data;
          this.checkAndParseCustomItinerary();
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

  openTransportDetailModal(bookingId: string): void {
    this.showDetailModal = true;
    this.isLoadingDetail = true;
    this.detailErrorMessage = '';
    this.bookingDetail = null;
    this.transportDetail = null;
    this.paymentInfo = null;

    let serviceCall: any;
    switch (this.activeTab) {
      case 'flight':
        serviceCall = this.flightBookingService.getBookingDetail(bookingId);
        break;
      case 'bus':
        serviceCall = this.busBookingService.getBookingDetail(bookingId);
        break;
      case 'train':
        serviceCall = this.trainBookingService.getBookingDetail(bookingId);
        break;
      case 'hotel':
        serviceCall = this.hotelBookingService.getBookingDetail(bookingId);
        break;
      default:
        this.isLoadingDetail = false;
        return;
    }

    serviceCall.subscribe({
      next: (response: any) => {
        if (response.EC === 0) {
          this.transportDetail = response.data;
        } else {
          this.detailErrorMessage = response.EM || 'Không thể tải chi tiết đơn hàng';
        }
        this.isLoadingDetail = false;
      },
      error: (error: any) => {
        console.error('Error loading transport detail:', error);
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
    this.transportDetail = null;
    this.detailErrorMessage = '';
    this.paymentInfo = null;
    this.customItinerary = null;
    this.isCustomTrip = false;
  }

  checkAndParseCustomItinerary(): void {
    this.customItinerary = null;
    this.isCustomTrip = false;
    
    if (this.bookingDetail && this.bookingDetail.special_requests) {
      try {
        const parsed = JSON.parse(this.bookingDetail.special_requests);
        if (parsed && parsed.source === 'trip_planner') {
          this.customItinerary = parsed;
          this.isCustomTrip = true;
        }
      } catch (e) {
        // Ignored - not custom trip plan
      }
    }
  }

  getItineraryDays(itinerary: any): string[] {
    if (!itinerary) return [];
    return Object.keys(itinerary).sort((a, b) => {
      const numA = parseInt(a.replace('day_', '')) || 0;
      const numB = parseInt(b.replace('day_', '')) || 0;
      return numA - numB;
    });
  }

  getDayLabel(dayKey: string): string {
    const num = parseInt(dayKey.replace('day_', '')) || 0;
    return `Ngày ${num}`;
  }

  hasItineraryActivities(daySlots: any): boolean {
    if (!daySlots) return false;
    return (
      (daySlots.morning && daySlots.morning.length > 0) ||
      (daySlots.afternoon && daySlots.afternoon.length > 0) ||
      (daySlots.evening && daySlots.evening.length > 0)
    );
  }

  asArray(val: any): string[] {
    if (!val) return [];
    if (Array.isArray(val)) return val;
    return [val];
  }

  formatTime(dateString: string): string {
    if (!dateString) return '--:--';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  formatDurationMinutes(minutes: number | null | undefined): string {
    if (!minutes) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}g ${m}p`;
    if (h > 0) return `${h} giờ`;
    return `${m} phút`;
  }

  formatDurationHours(hours: number | null | undefined): string {
    if (!hours) return '';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    if (h > 0 && m > 0) return `${h}g ${m}p`;
    if (h > 0) return `${h} giờ`;
    return `${m} phút`;
  }

  getUnitPrice(total: number, quantity: number): number {
    if (!quantity) return total;
    return Math.round(total / quantity);
  }

  getSeatClassLabel(seatClass: string): string {
    const labels: Record<string, string> = {
      economy: 'Phổ thông',
      business: 'Thương gia',
      first: 'Hạng nhất'
    };
    return labels[seatClass] || seatClass;
  }

  getTransportTypeLabel(): string {
    const labels: Record<string, string> = {
      flight: 'Vé máy bay',
      bus: 'Vé xe khách',
      train: 'Vé tàu hỏa',
      hotel: 'Đặt phòng khách sạn'
    };
    return labels[this.activeTab] || 'Đơn hàng';
  }

  getTransportThemeClass(): string {
    const themes: Record<string, string> = {
      flight: 'theme-flight',
      bus: 'theme-bus',
      train: 'theme-train',
      hotel: 'theme-hotel'
    };
    return themes[this.activeTab] || '';
  }

  getHotelNights(checkIn: string, checkOut: string): number {
    if (!checkIn || !checkOut) return 0;
    const start = new Date(checkIn);
    const end = new Date(checkOut);
    const diff = Math.abs(end.getTime() - start.getTime());
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  asFlightDetail(): FlightBookingDetail | null {
    return this.activeTab === 'flight' ? (this.transportDetail as FlightBookingDetail) : null;
  }

  asBusDetail(): BusBookingDetail | null {
    return this.activeTab === 'bus' ? (this.transportDetail as BusBookingDetail) : null;
  }

  asTrainDetail(): TrainBookingDetail | null {
    return this.activeTab === 'train' ? (this.transportDetail as TrainBookingDetail) : null;
  }

  asHotelDetail(): HotelBookingDetail | null {
    return this.activeTab === 'hotel' ? (this.transportDetail as HotelBookingDetail) : null;
  }

  canCancelTransport(status: string): boolean {
    return status === 'confirmed' || status === 'otp_sent';
  }

  printTransportBill(): void {
    window.print();
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

  canPayTransport(status: string, paymentStatus?: string): boolean {
    return (this.activeTab === 'flight' || this.activeTab === 'train') && 
           status === 'pending' && 
           paymentStatus !== 'paid';
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

  processTransportPayment(bookingId: string, bookingType: string): void {
    if (this.isProcessingPayment.has(bookingId)) {
      return;
    }

    this.isProcessingPayment.add(bookingId);
    this.paymentErrorMessage.delete(bookingId);

    this.paymentService.createTransportPayment(bookingType, bookingId).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data.payment_url) {
          console.log('Transport Payment URL created:', response.data.payment_url);
          window.location.href = response.data.payment_url;
        } else {
          this.paymentErrorMessage.set(bookingId, response.EM || 'Không thể tạo yêu cầu thanh toán');
          this.isProcessingPayment.delete(bookingId);
        }
      },
      error: (error) => {
        console.error('Error creating transport payment:', error);
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
