import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PaymentService, MyPayment, PaymentListParams } from '../../services/payment.service';

@Component({
  selector: 'app-my-payments',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './my-payments.component.html',
  styleUrl: './my-payments.component.scss'
})
export class MyPaymentsComponent implements OnInit {
  payments: MyPayment[] = [];
  filteredPayments: MyPayment[] = [];
  isLoading = false;
  errorMessage = '';
  
  statusFilter: 'pending' | 'completed' | 'failed' | '' = '';
  currentPage = 1;
  pageSize = 10;
  total = 0;

  stats = {
    total: 0,
    pending: 0,
    completed: 0,
    failed: 0,
    totalAmount: 0
  };

  constructor(private paymentService: PaymentService) {}

  ngOnInit(): void {
    this.loadPayments();
  }

  loadPayments(): void {
    this.isLoading = true;
    this.errorMessage = '';

    const params: PaymentListParams = {
      limit: this.pageSize,
      offset: (this.currentPage - 1) * this.pageSize
    };

    if (this.statusFilter) {
      params.status = this.statusFilter;
    }

    this.paymentService.getMyPayments(params).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.payments = response.data || [];
          this.total = response.total || 0;
          this.filteredPayments = this.payments;
          this.calculateStats();
        } else {
          this.errorMessage = response.EM || 'Có lỗi xảy ra khi tải lịch sử thanh toán';
          this.payments = [];
          this.filteredPayments = [];
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading payments:', error);
        this.errorMessage = 'Không thể tải lịch sử thanh toán. Vui lòng thử lại sau.';
        this.payments = [];
        this.filteredPayments = [];
        this.isLoading = false;
      }
    });
  }

  onStatusFilterChange(): void {
    this.currentPage = 1;
    this.loadPayments();
  }

  calculateStats(): void {
    this.stats.total = this.payments.length;
    this.stats.pending = this.payments.filter(p => p.payment_status === 'pending').length;
    this.stats.completed = this.payments.filter(p => p.payment_status === 'completed').length;
    this.stats.failed = this.payments.filter(p => p.payment_status === 'failed').length;
    this.stats.totalAmount = this.payments
      .filter(p => p.payment_status === 'completed')
      .reduce((sum, p) => sum + p.amount, 0);
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'completed': 'bg-green-100 text-green-800',
      'failed': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  }

  getStatusText(status: string): string {
    const texts: { [key: string]: string } = {
      'pending': 'Chờ xử lý',
      'completed': 'Thành công',
      'failed': 'Thất bại'
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
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  getTotalPages(): number {
    return Math.ceil(this.total / this.pageSize);
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.getTotalPages()) {
      this.currentPage = page;
      this.loadPayments();
    }
  }

  refresh(): void {
    this.loadPayments();
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
}

