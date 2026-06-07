import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { BookingCardComponent } from '../../components/booking-card/booking-card.component';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { BookingService } from '../../services/booking.service';
import { TourService } from '../../services/tour.service';
import { AuthStateService } from '../../services/auth-state.service';
import { PromotionService, Promotion } from '../../services/promotion.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-booking-pages',
  imports: [
    BookingCardComponent,
    FormsModule,
    CommonModule],
  templateUrl: './booking-pages.component.html',
  styleUrl: './booking-pages.component.scss'
})
export class BookingPagesComponent implements OnInit {
  packageId: string = '';
  tourPackage: any = null;
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  fullName: string = '';
  email: string = '';
  phoneNumber: string = '';
  numberOfPeople: number = 1;
  specialRequests: string = '';
  isSameAsBooker: boolean = true;

  currentUser: any = null;

  // OTP state
  showOTPForm = false;
  bookingIdForOTP: string = '';
  otpCode: string = '';
  isVerifyingOTP = false;
  isResendingOTP = false;
  otpErrorMessage = '';
  otpSuccessMessage = '';

  // Promotion state
  availablePromotions: Promotion[] = [];
  selectedPromotion: Promotion | null = null;
  isLoadingPromotions = false;
  discountAmount = 0;

  priceBreakdown: PriceBreakdown = {
    roomDescription: '',
    roomPrice: 0,
    taxAndFees: 0,
    totalPrice: 0,
  };

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private bookingService: BookingService,
    private tourService: TourService,
    private authStateService: AuthStateService,
    private promotionService: PromotionService,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.packageId = params['id'];
      if (this.packageId) {
        this.loadTourPackage();
      }
    });

    this.authStateService.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user) {
        this.fullName = user.full_name || '';
        this.email = user.email || '';
      }
    });

    // Load available promotions
    this.loadAvailablePromotions();
  }

  async loadTourPackage(): Promise<void> {
    try {
      this.isLoading = true;
      const response = await this.tourService.getTourPackageById(this.packageId);
      if (response.EC === 0 && response.package) {
        this.tourPackage = response.package;
        this.updatePriceBreakdown();
      } else {
        this.errorMessage = response.EM || 'Không thể tải thông tin tour';
      }
    } catch (error: any) {
      console.error('Error loading tour package:', error);
      this.errorMessage = error.message || 'Không thể tải thông tin tour';
    } finally {
      this.isLoading = false;
    }
  }

  updatePriceBreakdown(): void {
    if (this.tourPackage) {
      const basePrice = this.tourPackage.price || 0;
      const totalPrice = basePrice * this.numberOfPeople;

      // Calculate discount if promotion is applied
      let finalPrice = totalPrice;
      if (this.selectedPromotion) {
        if (this.selectedPromotion.discount_type === 'PERCENTAGE') {
          this.discountAmount = (totalPrice * this.selectedPromotion.discount_value) / 100;
        } else if (this.selectedPromotion.discount_type === 'FIXED_AMOUNT') {
          this.discountAmount = this.selectedPromotion.discount_value;
        }
        finalPrice = Math.max(0, totalPrice - this.discountAmount);
      } else {
        this.discountAmount = 0;
      }

      this.priceBreakdown = {
        roomDescription: `${this.tourPackage.package_name} - ${this.numberOfPeople} người`,
        roomPrice: totalPrice,
        taxAndFees: 0,
        totalPrice: finalPrice,
      };
    }
  }

  loadAvailablePromotions(): void {
    this.isLoadingPromotions = true;
    this.promotionService.getAvailablePromotions().subscribe({
      next: (response) => {
        if (response.EC === 0 && response.promotions) {
          this.availablePromotions = response.promotions;
        }
        this.isLoadingPromotions = false;
      },
      error: (error) => {
        console.error('Error loading promotions:', error);
        this.isLoadingPromotions = false;
      }
    });
  }

  applyPromotion(promotion: Promotion): void {
    this.selectedPromotion = promotion;
    this.updatePriceBreakdown();
  }

  removePromotion(): void {
    this.selectedPromotion = null;
    this.updatePriceBreakdown();
  }

  onNumberOfPeopleInput(event: any): void {
    let value = parseInt(event.target.value, 10);
    
    // Handle empty or invalid input
    if (isNaN(value) || value < 1) {
      value = 1;
    }
    
    // Enforce max value (available slots)
    if (this.tourPackage?.available_slots !== undefined && this.tourPackage.available_slots > 0) {
      if (value > this.tourPackage.available_slots) {
        value = this.tourPackage.available_slots;
      }
    }
    
    // Update the value immediately
    this.numberOfPeople = value;
    event.target.value = value;
    this.cdr.detectChanges();
    
    this.updatePriceBreakdown();
  }

  onNumberOfPeopleChange(): void {
    // Enforce min value (1)
    if (this.numberOfPeople < 1) {
      this.numberOfPeople = 1;
    }
    
    // Enforce max value (available slots)
    if (this.tourPackage?.available_slots !== undefined && this.tourPackage.available_slots > 0) {
      if (this.numberOfPeople > this.tourPackage.available_slots) {
        this.numberOfPeople = this.tourPackage.available_slots;
      }
    }
    
    this.updatePriceBreakdown();
  }

  onPhoneNumberInput(event: any): void {
    // Only allow digits
    let value = event.target.value.replace(/\D/g, '');
    
    // Limit to 10 digits
    if (value.length > 10) {
      value = value.substring(0, 10);
    }
    
    this.phoneNumber = value;
    event.target.value = value;
  }

  submitForm() {
    if (!this.validateForm()) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.currentUser || !this.currentUser.user_id) {
      this.errorMessage = 'Vui lòng đăng nhập để đặt tour';
      this.isLoading = false;
      return;
    }

    // Get email from user or form
    const contactEmail = this.email || this.currentUser?.email || '';

    if (!contactEmail) {
      this.errorMessage = 'Vui lòng nhập email để nhận mã OTP xác nhận.';
      this.isLoading = false;
      return;
    }

    const bookingData = {
      package_id: this.packageId,
      number_of_people: this.numberOfPeople,
      contact_name: this.fullName,
      contact_phone: this.phoneNumber,
      contact_email: contactEmail,
      user_id: this.currentUser.user_id,
      special_requests: this.specialRequests || undefined,
      promotion_code: this.selectedPromotion?.code || undefined
    };

    this.bookingService.createBooking(bookingData).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          // Backend returns BookingOTPResponse with data as dict
          // Handle both structured object and dict
          const data = response.data as any;
          const bookingId = data.booking_id || (typeof data === 'object' && 'booking_id' in data ? data.booking_id : null);

          // Always show OTP form for create-with-otp endpoint
          if (bookingId) {
            this.bookingIdForOTP = bookingId;
            this.showOTPForm = true;
            this.successMessage = response.EM || 'Mã OTP đã được gửi đến email của bạn. Vui lòng nhập mã OTP để xác nhận đặt tour.';
            this.errorMessage = '';
            this.isLoading = false;
            window.scrollTo({ top: 0, behavior: 'smooth' });
          } else {
            // Fallback: No booking_id, try to redirect
            this.successMessage = 'Đặt tour thành công! Đang chuyển đến trang đơn hàng của bạn...';
            this.errorMessage = '';
            this.isLoading = false;

            setTimeout(() => {
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }, 100);

            setTimeout(() => {
              this.router.navigate(['/my-bookings']);
            }, 3000);
          }
        } else {
          this.errorMessage = response.EM || 'Không thể tạo đơn đặt tour';
          this.successMessage = '';
          this.isLoading = false;
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      },
      error: (error) => {
        console.error('Error creating booking:', error);
        this.errorMessage = error.error?.detail || error.error?.EM || 'Có lỗi xảy ra khi tạo đơn đặt tour. Vui lòng thử lại sau.';
        this.successMessage = '';
        this.isLoading = false;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  }

  validateForm(): boolean {
    if (!this.fullName.trim()) {
      this.errorMessage = 'Vui lòng nhập họ và tên';
      return false;
    }
    if (!this.email.trim()) {
      this.errorMessage = 'Vui lòng nhập email';
      return false;
    }
    if (!this.phoneNumber.trim()) {
      this.errorMessage = 'Vui lòng nhập số điện thoại';
      return false;
    }
    // Validate phone number must be exactly 10 digits
    const phoneDigits = this.phoneNumber.replace(/\D/g, '');
    if (phoneDigits.length !== 10) {
      this.errorMessage = 'Số điện thoại phải có đúng 10 số';
      return false;
    }
    if (this.numberOfPeople < 1) {
      this.errorMessage = 'Số người phải lớn hơn 0';
      return false;
    }
    // Check available slots
    if (this.tourPackage?.available_slots !== undefined) {
      if (this.tourPackage.available_slots <= 0) {
        this.errorMessage = 'Tour đã hết chỗ trống. Vui lòng chọn tour khác.';
        return false;
      }
      if (this.numberOfPeople > this.tourPackage.available_slots) {
        this.errorMessage = `Số người (${this.numberOfPeople}) vượt quá số chỗ còn lại (${this.tourPackage.available_slots}). Vui lòng giảm số người.`;
        return false;
      }
    }
    return true;
  }

  proceedToPayment() {
    this.submitForm();
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  verifyOTP(): void {
    if (!this.otpCode || this.otpCode.length !== 6) {
      this.otpErrorMessage = 'Vui lòng nhập mã OTP 6 số.';
      return;
    }

    if (!this.bookingIdForOTP) {
      this.otpErrorMessage = 'Không tìm thấy thông tin booking.';
      return;
    }

    this.isVerifyingOTP = true;
    this.otpErrorMessage = '';
    this.otpSuccessMessage = '';

    this.bookingService.verifyOTP(this.bookingIdForOTP, this.otpCode).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.otpSuccessMessage = 'Xác nhận OTP thành công! Đặt tour của bạn đã được xác nhận.';
          this.otpErrorMessage = '';
          this.isVerifyingOTP = false;

          // Hide OTP form and show success
          setTimeout(() => {
            this.showOTPForm = false;
            this.successMessage = 'Đặt tour thành công! Đang chuyển đến trang đơn hàng của bạn...';
            setTimeout(() => {
              this.router.navigate(['/my-bookings']);
            }, 2000);
          }, 2000);
        } else {
          this.otpErrorMessage = response.EM || 'Mã OTP không đúng. Vui lòng thử lại.';
          this.otpSuccessMessage = '';
          this.isVerifyingOTP = false;
        }
      },
      error: (error) => {
        console.error('Error verifying OTP:', error);
        this.otpErrorMessage = error.error?.detail || error.error?.EM || 'Có lỗi xảy ra khi xác nhận OTP. Vui lòng thử lại.';
        this.otpSuccessMessage = '';
        this.isVerifyingOTP = false;
      }
    });
  }

  resendOTP(): void {
    if (!this.bookingIdForOTP) {
      this.otpErrorMessage = 'Không tìm thấy thông tin booking.';
      return;
    }

    this.isResendingOTP = true;
    this.otpErrorMessage = '';
    this.otpSuccessMessage = '';

    this.bookingService.resendOTP(this.bookingIdForOTP).subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.otpSuccessMessage = 'Mã OTP mới đã được gửi đến email của bạn.';
          this.otpErrorMessage = '';
          this.otpCode = ''; // Clear old OTP
          this.isResendingOTP = false;
        } else {
          this.otpErrorMessage = response.EM || 'Không thể gửi lại mã OTP. Vui lòng thử lại.';
          this.otpSuccessMessage = '';
          this.isResendingOTP = false;
        }
      },
      error: (error) => {
        console.error('Error resending OTP:', error);
        this.otpErrorMessage = error.error?.detail || error.error?.EM || 'Có lỗi xảy ra khi gửi lại OTP. Vui lòng thử lại.';
        this.otpSuccessMessage = '';
        this.isResendingOTP = false;
      }
    });
  }

  onOTPInput(event: any): void {
    // Only allow numbers and limit to 6 digits
    let value = event.target.value.replace(/\D/g, '');
    if (value.length > 6) {
      value = value.substring(0, 6);
    }
    this.otpCode = value;
    event.target.value = value;
  }

  onOTPEnter(): void {
    // Only verify if OTP is complete (6 digits) and not already verifying
    if (this.otpCode.length === 6 && !this.isVerifyingOTP) {
      this.verifyOTP();
    }
  }
}

interface PriceBreakdown {
  roomDescription: string;
  roomPrice: number;
  taxAndFees: number;
  totalPrice: number;
}
