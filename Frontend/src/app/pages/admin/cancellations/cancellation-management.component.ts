import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
    AdminBookingService,
    BookingCancellationItem,
    CancellationListParams
} from '../../../services/admin/admin-booking.service';
import { AdminDialogService } from '../../../services/admin/admin-dialog.service';

@Component({
    selector: 'app-cancellation-management',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './cancellation-management.component.html',
    styleUrl: './cancellation-management.component.scss'
})
export class CancellationManagementComponent implements OnInit {
    cancellations: BookingCancellationItem[] = [];
    filteredCancellations: BookingCancellationItem[] = [];

    // Filters
    searchTerm = '';
    cancelledByFilter: string = '';

    // Loading state
    isLoading = false;
    errorMessage = '';

    // Stats
    totalCancellations = 0;

    // Detail modal
    showDetailModal = false;
    selectedCancellation: BookingCancellationItem | null = null;

    constructor(
        private bookingService: AdminBookingService,
        private dialogService: AdminDialogService
    ) { }

    ngOnInit(): void {
        this.loadCancellations();
    }

    async loadCancellations() {
        this.isLoading = true;
        this.errorMessage = '';

        const params: CancellationListParams = {
            limit: 100,
            offset: 0
        };

        if (this.cancelledByFilter) {
            params.cancelled_by = this.cancelledByFilter;
        }

        try {
            const response = await this.bookingService.getCancellationsAdmin(params).toPromise();

            if (response && response.EC === 0) {
                this.cancellations = response.data || [];
                this.totalCancellations = response.total || 0;
                this.applyFilters();
            } else {
                this.errorMessage = response?.EM || 'Không thể tải danh sách hủy booking';
            }
        } catch (error: any) {
            console.error('Error loading cancellations:', error);
            this.errorMessage = error?.error?.detail || 'Lỗi khi tải dữ liệu';
        } finally {
            this.isLoading = false;
        }
    }

    applyFilters() {
        this.filteredCancellations = this.cancellations.filter(cancel => {
            const matchesSearch = !this.searchTerm ||
                cancel.tour_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
                cancel.user_email?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
                cancel.user_full_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
                cancel.contact_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
                cancel.reason?.toLowerCase().includes(this.searchTerm.toLowerCase());

            return matchesSearch;
        });
    }

    onFilterChange() {
        this.loadCancellations();
    }

    onSearchChange() {
        this.applyFilters();
    }

    // Detail modal
    openDetailModal(cancel: BookingCancellationItem) {
        this.selectedCancellation = cancel;
        this.showDetailModal = true;
    }

    closeDetailModal() {
        this.showDetailModal = false;
        this.selectedCancellation = null;
    }

    // Stats
    getCancelledByUser(): number {
        return this.cancellations.filter(c => c.cancelled_by === 'user').length;
    }

    getCancelledByAdmin(): number {
        return this.cancellations.filter(c => c.cancelled_by === 'admin').length;
    }

    getCancelledBySystem(): number {
        return this.cancellations.filter(c => c.cancelled_by === 'system').length;
    }

    getTotalRefundAmount(): string {
        const total = this.cancellations.reduce((sum, c) => sum + (c.total_amount || 0), 0);
        return new Intl.NumberFormat('vi-VN').format(total) + ' VNĐ';
    }

    // Utilities
    formatPrice(price: number): string {
        if (!price) return '0 VNĐ';
        return new Intl.NumberFormat('vi-VN').format(price) + ' VNĐ';
    }

    formatDate(dateString: string): string {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('vi-VN');
    }

    formatDateTime(dateString: string): string {
        if (!dateString) return 'N/A';
        return new Intl.DateTimeFormat('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(dateString));
    }

    getCancelledByLabel(cancelledBy: string): string {
        switch (cancelledBy) {
            case 'user': return 'Khách hàng';
            case 'admin': return 'Admin';
            case 'system': return 'Hệ thống';
            default: return cancelledBy;
        }
    }

    getCancelledByClass(cancelledBy: string): string {
        switch (cancelledBy) {
            case 'user': return 'bg-blue-100 text-blue-700';
            case 'admin': return 'bg-orange-100 text-orange-700';
            case 'system': return 'bg-purple-100 text-purple-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    }

    getPreviousStatusLabel(status: string): string {
        switch (status) {
            case 'pending': return 'Chờ xử lý';
            case 'confirmed': return 'Đã xác nhận';
            case 'otp_sent': return 'Đã gửi OTP';
            default: return status;
        }
    }
}
