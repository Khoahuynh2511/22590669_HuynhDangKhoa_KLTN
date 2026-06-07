import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AdminPaymentService, AdminPaymentItem, AdminPaymentListParams } from '../../../services/admin/admin-payment.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

interface StatusOption {
  value: string;
  label: string;
}

@Component({
  selector: 'app-payment-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './payment-management.component.html',
  styleUrl: './payment-management.component.scss'
})
export class PaymentManagementComponent implements OnInit {
  payments: AdminPaymentItem[] = [];
  filteredPayments: AdminPaymentItem[] = [];
  total = 0;
  stats = {
    total: 0,
    completed: 0,
    pending: 0,
    refunded: 0,
    failed: 0,
    totalAmount: 0
  };
  isLoading = false;
  errorMessage = '';

  // Status and method options
  paymentStatusOptions: StatusOption[] = [];
  bookingStatusOptions: StatusOption[] = [];
  paymentMethodOptions: StatusOption[] = [];

  statusFilter = '';
  bookingStatusFilter = '';
  userFilter = '';
  paymentMethodFilter = '';
  tourFilter = '';
  minAmount: number | null = null;
  maxAmount: number | null = null;
  minAmountDisplay: string = '';
  maxAmountDisplay: string = '';
  paidFrom: string = '';
  paidTo: string = '';

  showCreateModal = false;
  showRefundModal = false;
  showDetailModal = false;

  selectedPayment: AdminPaymentItem | null = null;
  refundReason = '';

  createPayload = {
    booking_id: '',
    payment_method: 'bank_transfer',
    transaction_id: '',
    notes: ''
  };

  constructor(
    private adminPaymentService: AdminPaymentService,
    private dialogService: AdminDialogService,
    private http: HttpClient
  ) { }

  ngOnInit() {
    this.initializeDefaultOptions();
    this.loadStatusOptions();
    this.loadPayments();
  }

  initializeDefaultOptions() {
    // Default payment status options
    this.paymentStatusOptions = [
      { value: 'pending', label: 'Chờ thanh toán' },
      { value: 'completed', label: 'Đã thanh toán' },
      { value: 'refunded', label: 'Đã hoàn tiền' }
    ];

    // Default payment method options
    this.paymentMethodOptions = [
      { value: 'bank_transfer', label: 'Chuyển khoản ngân hàng' },
      { value: 'vnpay', label: 'VNPay' }
    ];
  }

  async loadStatusOptions() {
    try {
      const response: any = await this.http.get('/api/v1/config/payment-statuses').toPromise();
      if (response?.data && response.data.length > 0) {
        this.paymentStatusOptions = response.data;
      }
    } catch (error) {
      console.error('Error loading payment statuses:', error);
    }

    try {
      const response: any = await this.http.get('/api/v1/config/payment-methods').toPromise();
      if (response?.data && response.data.length > 0) {
        this.paymentMethodOptions = response.data;
      }
    } catch (error) {
      console.error('Error loading payment methods:', error);
    }
  }

  async loadPayments() {
    this.isLoading = true;
    this.errorMessage = '';
    try {
      const params: AdminPaymentListParams = {
        status: this.statusFilter || undefined,
        user_id: this.userFilter || undefined,
        limit: 100,
        offset: 0
      };
      const response = await this.adminPaymentService.getPayments(params).toPromise();
      if (response && response.EC === 0) {
        this.payments = response.data;
        this.total = response.total;
        this.applyFilters();
      } else {
        this.errorMessage = response?.EM || 'Không thể tải danh sách thanh toán';
        this.payments = [];
        this.filteredPayments = [];
      }
    } catch (error: any) {
      console.error('Error loading payments:', error);
      this.errorMessage = error?.error?.EM || 'Lỗi khi tải danh sách thanh toán';
      this.payments = [];
      this.filteredPayments = [];
    } finally {
      this.isLoading = false;
    }
  }

  openCreateModal() {
    this.createPayload = {
      booking_id: '',
      payment_method: 'bank_transfer',
      transaction_id: '',
      notes: ''
    };
    this.showCreateModal = true;
  }

  closeCreateModal() {
    this.showCreateModal = false;
  }

  openDetail(payment: AdminPaymentItem) {
    this.selectedPayment = payment;
    this.showDetailModal = true;
  }

  closeDetail() {
    this.showDetailModal = false;
    this.selectedPayment = null;
  }

  async submitCreate() {
    if (!this.createPayload.booking_id) {
      await this.dialogService.alert('Thiếu thông tin', 'Vui lòng nhập Booking ID');
      return;
    }

    this.isLoading = true;
    try {
      const response = await this.adminPaymentService.createPayment(this.createPayload).toPromise();
      if (response && response.EC === 0) {
        await this.dialogService.alert('Thành công', 'Đã tạo thanh toán và xác nhận booking.');
        this.showCreateModal = false;
        await this.loadPayments();
      } else {
        await this.dialogService.alert('Lỗi', response?.EM || 'Không thể tạo thanh toán');
      }
    } catch (error: any) {
      console.error('Error creating payment:', error);
      await this.dialogService.alert('Lỗi', error?.error?.EM || 'Không thể tạo thanh toán');
    } finally {
      this.isLoading = false;
    }
  }

  openRefundModal(payment: AdminPaymentItem) {
    if (!this.canRefund(payment)) return;
    this.selectedPayment = payment;
    this.refundReason = '';
    this.showRefundModal = true;
  }

  closeRefundModal() {
    this.showRefundModal = false;
    this.selectedPayment = null;
    this.refundReason = '';
  }

  async submitRefund() {
    if (!this.selectedPayment) return;
    if (!this.refundReason.trim()) {
      await this.dialogService.alert('Thiếu lý do', 'Vui lòng nhập lý do hoàn tiền.');
      return;
    }
    this.isLoading = true;
    try {
      const response = await this.adminPaymentService.refundPayment(this.selectedPayment.payment_id, {
        refund_reason: this.refundReason
      }).toPromise();

      if (response && response.EC === 0) {
        await this.dialogService.alert('Thành công', 'Đã hoàn tiền và cập nhật trạng thái booking.');
        this.closeRefundModal();
        await this.loadPayments();
      } else {
        await this.dialogService.alert('Lỗi', response?.EM || 'Không thể hoàn tiền');
      }
    } catch (error: any) {
      console.error('Error refunding payment:', error);
      await this.dialogService.alert('Lỗi', error?.error?.EM || 'Không thể hoàn tiền');
    } finally {
      this.isLoading = false;
    }
  }

  canRefund(payment: AdminPaymentItem): boolean {
    return payment.payment_status === 'completed' && !payment.refunded_at;
  }

  applyFilters() {
    this.filteredPayments = this.payments.filter((p) => {
      const matchesStatus = !this.statusFilter || p.payment_status === this.statusFilter;
      const userFilterLower = this.userFilter.toLowerCase();
      const matchesUser = !this.userFilter ||
        (p.user_id || '').includes(this.userFilter) ||
        (p.user_name || '').toLowerCase().includes(userFilterLower) ||
        (p.contact_email || '').toLowerCase().includes(userFilterLower) ||
        (p.contact_phone || '').includes(this.userFilter);
      const matchesMethod = !this.paymentMethodFilter || p.payment_method === this.paymentMethodFilter;
      const matchesTour = !this.tourFilter || (p.tour_name || '').toLowerCase().includes(this.tourFilter.toLowerCase());

      const amount = p.amount || 0;
      const matchesMin = this.minAmount === null || amount >= this.minAmount;
      const matchesMax = this.maxAmount === null || amount <= this.maxAmount;

      const paidAt = p.paid_at || p.created_at;
      let matchesFrom = true;
      let matchesTo = true;
      if (paidAt && this.paidFrom) {
        matchesFrom = new Date(paidAt) >= new Date(this.paidFrom);
      }
      if (paidAt && this.paidTo) {
        const toDate = new Date(this.paidTo);
        toDate.setHours(23, 59, 59, 999);
        matchesTo = new Date(paidAt) <= toDate;
      }

      return matchesStatus && matchesUser && matchesMethod && matchesTour && matchesMin && matchesMax && matchesFrom && matchesTo;
    });

    this.computeStats();
  }

  reloadData() {
    this.loadPayments();
  }

  formatNumberInput(event: any, type: 'min' | 'max') {
    let value = event.target.value.replace(/\./g, '');
    
    if (value === '') {
      if (type === 'min') {
        this.minAmount = null;
        this.minAmountDisplay = '';
      } else {
        this.maxAmount = null;
        this.maxAmountDisplay = '';
      }
      return;
    }
    
    const numValue = parseInt(value, 10);
    if (!isNaN(numValue)) {
      const formatted = numValue.toLocaleString('vi-VN');
      if (type === 'min') {
        this.minAmount = numValue;
        this.minAmountDisplay = formatted;
      } else {
        this.maxAmount = numValue;
        this.maxAmountDisplay = formatted;
      }
    }
  }

  resetFilters() {
    this.statusFilter = '';
    this.userFilter = '';
    this.paymentMethodFilter = '';
    this.tourFilter = '';
    this.minAmount = null;
    this.maxAmount = null;
    this.paidFrom = '';
    this.paidTo = '';
    this.bookingStatusFilter = '';
    this.applyFilters();
  }

  private computeStats() {
    this.stats.total = this.payments.length;
    this.stats.completed = this.payments.filter(p => p.payment_status === 'completed').length;
    this.stats.pending = this.payments.filter(p => p.payment_status === 'pending').length;
    this.stats.refunded = this.payments.filter(p => p.payment_status === 'refunded').length;
    this.stats.failed = this.payments.filter(p => p.payment_status === 'failed').length;
    // Chỉ tính tổng tiền từ các payment đã completed
    this.stats.totalAmount = this.payments
      .filter(p => p.payment_status === 'completed')
      .reduce((sum, p) => sum + (p.amount || 0), 0);
  }

  formatDate(value?: string): string {
    if (!value) return '';
    const date = new Date(value);
    return new Intl.DateTimeFormat('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  getStatusClass(status: string): string {
    const map: { [key: string]: string } = {
      pending: 'bg-yellow-100 text-yellow-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
      refunded: 'bg-blue-100 text-blue-700'
    };
    return map[status] || 'bg-gray-100 text-gray-700';
  }

  getStatusText(status: string): string {
    const map: { [key: string]: string } = {
      pending: 'Chờ thanh toán',
      completed: 'Đã thanh toán',
      failed: 'Thất bại',
      refunded: 'Đã hoàn tiền'
    };
    return map[status] || status;
  }

  /**
   * Process a pending payment - mark as completed
   */
  async processPayment(payment: AdminPaymentItem) {
    const confirmed = await this.dialogService.confirm({
      title: 'Xác nhận thanh toán',
      message: `Bạn có muốn xác nhận thanh toán ${payment.amount?.toLocaleString('vi-VN')} VNĐ cho booking này?`,
      confirmText: 'Xác nhận',
      cancelText: 'Hủy'
    });

    if (!confirmed) return;

    this.isLoading = true;
    try {
      // Use confirmPayment to update existing pending payment to completed
      const response = await this.adminPaymentService.confirmPayment(payment.payment_id).toPromise();

      if (response && response.EC === 0) {
        await this.dialogService.alert('Thành công', 'Đã xác nhận thanh toán thành công!');
        this.closeDetail(); // Close modal after success
        await this.loadPayments();
      } else {
        await this.dialogService.alert('Lỗi', response?.EM || 'Không thể xác nhận thanh toán');
      }
    } catch (error: any) {
      console.error('Error processing payment:', error);
      await this.dialogService.alert('Lỗi', error?.error?.detail || error?.error?.EM || 'Không thể xác nhận thanh toán');
    } finally {
      this.isLoading = false;
    }
  }
}
