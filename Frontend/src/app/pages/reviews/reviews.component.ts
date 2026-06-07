import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ReviewService } from '../../services/review.service';
import { BookingService } from '../../services/booking.service';

interface Booking {
  booking_id: string;
  package_id: string | null;
  package_name: string;
  departure_date: string;
  status: string;
  total_price: number;
  has_review?: boolean;
}

interface Review {
  review_id?: string;
  booking_id: string;
  package_id: string;
  package_name?: string;
  rating: number;
  comment: string;
  images?: string[];
  is_approved?: boolean;
  created_at?: string;
}

@Component({
  selector: 'app-reviews',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reviews.component.html',
  styleUrls: ['./reviews.component.scss']
})
export class ReviewsComponent implements OnInit {
  activeTab: 'create' | 'my-reviews' = 'create';

  // Create Review Tab
  availableBookings: Booking[] = [];
  selectedBooking: Booking | null = null;
  newReview = {
    rating: 5,
    comment: '',
    images: [] as string[]
  };

  // My Reviews Tab
  myReviews: Review[] = [];

  // Edit Review State
  editingReview: Review | null = null;
  editForm = {
    rating: 5,
    comment: ''
  };

  // Delete Confirmation
  deletingReviewId: string | null = null;

  // Loading states
  loading = {
    bookings: false,
    reviews: false,
    submitting: false,
    editing: false,
    deleting: false
  };

  error: string | null = null;
  successMessage: string | null = null;

  constructor(
    private reviewService: ReviewService,
    private bookingService: BookingService,
    public router: Router
  ) { }

  ngOnInit(): void {
    this.loadData();
  }

  async loadData(): Promise<void> {
    await Promise.all([
      this.loadAvailableBookings(),
      this.loadMyReviews()
    ]);
  }

  async loadAvailableBookings(): Promise<void> {
    this.loading.bookings = true;
    this.error = null;
    this.availableBookings = []; // Reset to empty array first

    try {
      const response = await this.bookingService.getMyBookings({ status: 'completed' }).toPromise();

      console.log('Bookings response:', response);

      if (response?.EC === 0 && response.data && Array.isArray(response.data) && response.data.length > 0) {
        // Map từ MyBooking interface
        const filteredBookings = response.data.map((b: any) => ({
          booking_id: b.booking_id,
          package_id: null, // Sẽ fetch khi submit
          package_name: b.tour_name,
          departure_date: b.start_date,
          status: b.status,
          total_price: b.total_amount,
          has_review: false
        }));

        console.log('Filtered bookings:', filteredBookings);
        console.log('Assigning to availableBookings, length:', filteredBookings.length);
        this.availableBookings = filteredBookings;
        console.log('After assignment, availableBookings.length:', this.availableBookings.length);

        // Check which bookings already have reviews (only if there are bookings)
        if (this.availableBookings.length > 0) {
          await this.checkExistingReviews();
        }
      }
    } catch (error: any) {
      console.error('Error loading bookings:', error);
      this.error = 'Không thể tải danh sách booking. Vui lòng thử lại.';
      this.availableBookings = [];
    } finally {
      this.loading.bookings = false;
    }
  }

  async checkExistingReviews(): Promise<void> {
    try {
      const response = await this.reviewService.getMyReviews().toPromise();

      if (response?.EC === 0 && response.data) {
        const reviewedBookingIds = new Set(
          response.data.map((r: any) => r.booking_id)
        );

        this.availableBookings.forEach(booking => {
          booking.has_review = reviewedBookingIds.has(booking.booking_id);
        });
      }
    } catch (error) {
      console.error('Error checking existing reviews:', error);
    }
  }

  async loadMyReviews(): Promise<void> {
    this.loading.reviews = true;

    try {
      const response = await this.reviewService.getMyReviews().toPromise();

      if (response?.EC === 0 && response.data) {
        this.myReviews = response.data.map((r: any) => ({
          review_id: r.review_id,
          booking_id: r.booking_id,
          package_id: r.package_id,
          package_name: r.package?.title || 'Unknown Tour',
          rating: r.rating,
          comment: r.comment,
          images: r.images || [],
          is_approved: r.is_approved,
          created_at: r.created_at
        }));
      }
    } catch (error: any) {
      console.error('Error loading reviews:', error);
    } finally {
      this.loading.reviews = false;
    }
  }

  selectBooking(booking: Booking): void {
    if (booking.has_review) return;

    this.selectedBooking = booking;
    this.newReview = {
      rating: 5,
      comment: '',
      images: []
    };
    this.error = null;
    this.successMessage = null;
  }

  onTabChange(tab: 'create' | 'my-reviews'): void {
    this.activeTab = tab;
    // Refresh data when switching to create tab to ensure bookings list is up-to-date
    if (tab === 'create') {
      this.loadAvailableBookings();
    } else if (tab === 'my-reviews') {
      this.loadMyReviews();
    }
  }

  setRating(rating: number): void {
    this.newReview.rating = rating;
  }

  async submitReview(): Promise<void> {
    if (!this.selectedBooking) {
      this.error = 'Vui lòng chọn booking để đánh giá';
      return;
    }

    if (!this.newReview.comment.trim()) {
      this.error = 'Vui lòng nhập nội dung đánh giá';
      return;
    }

    this.loading.submitting = true;
    this.error = null;
    this.successMessage = null;

    try {
      // Fetch package_id nếu chưa có
      let packageId = this.selectedBooking.package_id;
      if (!packageId) {
        const bookingDetail = await this.bookingService.getMyBookingDetail(this.selectedBooking.booking_id).toPromise();
        packageId = bookingDetail?.data?.tour_package?.package_id ?? null;
      }

      if (!packageId) {
        this.error = 'Không tìm thấy thông tin tour. Vui lòng thử lại.';
        this.loading.submitting = false;
        return;
      }

      const response = await this.reviewService.createReview({
        booking_id: this.selectedBooking.booking_id,
        package_id: packageId,
        rating: this.newReview.rating,
        comment: this.newReview.comment,
        images: this.newReview.images
      }).toPromise();

      if (response?.EC === 0) {
        this.successMessage = 'Đánh giá của bạn đã được gửi thành công!';

        // Reset form
        this.selectedBooking = null;
        this.newReview = {
          rating: 5,
          comment: '',
          images: []
        };

        // Reload data
        await this.loadData();

        // Auto switch to my reviews tab after 2 seconds
        setTimeout(() => {
          this.activeTab = 'my-reviews';
        }, 2000);
      } else {
        this.error = response?.EM || 'Không thể gửi đánh giá. Vui lòng thử lại.';
      }
    } catch (error: any) {
      console.error('Error submitting review:', error);
      this.error = error.error?.EM || 'Đã xảy ra lỗi khi gửi đánh giá. Vui lòng thử lại.';
    } finally {
      this.loading.submitting = false;
    }
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  getStars(rating: number): number[] {
    return Array(5).fill(0).map((_, i) => i < rating ? 1 : 0);
  }

  getReviewStatusText(isApproved: boolean | undefined): string {
    if (isApproved === undefined || isApproved === null) {
      return 'Chờ duyệt';
    }
    return isApproved ? 'Đã duyệt' : 'Chờ duyệt';
  }

  getReviewStatusClass(isApproved: boolean | undefined): string {
    if (isApproved === undefined || isApproved === null) {
      return 'pending';
    }
    return isApproved ? 'approved' : 'pending';
  }

  // ========== Edit Review Methods ==========
  editReview(review: Review): void {
    this.editingReview = review;
    this.editForm = {
      rating: review.rating,
      comment: review.comment
    };
    this.error = null;
    this.successMessage = null;
  }

  cancelEdit(): void {
    this.editingReview = null;
    this.editForm = { rating: 5, comment: '' };
  }

  async saveEditReview(): Promise<void> {
    if (!this.editingReview?.review_id) return;
    if (this.editForm.comment.length < 10) {
      this.error = 'Nội dung đánh giá phải có ít nhất 10 ký tự';
      return;
    }

    this.loading.editing = true;
    this.error = null;

    try {
      const response = await this.reviewService.updateReview(
        this.editingReview.review_id,
        {
          rating: this.editForm.rating,
          comment: this.editForm.comment
        }
      ).toPromise();

      if (response?.EC === 0) {
        this.successMessage = 'Đánh giá đã được cập nhật thành công!';
        this.cancelEdit();
        await this.loadMyReviews();
      } else {
        this.error = response?.EM || 'Không thể cập nhật đánh giá. Vui lòng thử lại.';
      }
    } catch (error: any) {
      console.error('Error updating review:', error);
      this.error = error.error?.EM || 'Đã xảy ra lỗi khi cập nhật đánh giá.';
    } finally {
      this.loading.editing = false;
    }
  }

  setEditRating(star: number): void {
    this.editForm.rating = star;
  }

  // ========== Delete Review Methods ==========
  confirmDelete(reviewId: string): void {
    this.deletingReviewId = reviewId;
    this.error = null;
    this.successMessage = null;
  }

  cancelDelete(): void {
    this.deletingReviewId = null;
  }

  async deleteReview(): Promise<void> {
    if (!this.deletingReviewId) return;

    this.loading.deleting = true;
    this.error = null;

    try {
      const response = await this.reviewService.deleteReview(this.deletingReviewId).toPromise();

      if (response?.EC === 0) {
        this.successMessage = 'Đánh giá đã được xóa thành công!';
        this.cancelDelete();
        // Refresh both tabs to ensure data consistency
        await this.loadData();
      } else {
        this.error = response?.EM || 'Không thể xóa đánh giá. Vui lòng thử lại.';
      }
    } catch (error: any) {
      console.error('Error deleting review:', error);
      this.error = error.error?.EM || 'Đã xảy ra lỗi khi xóa đánh giá.';
    } finally {
      this.loading.deleting = false;
    }
  }
}