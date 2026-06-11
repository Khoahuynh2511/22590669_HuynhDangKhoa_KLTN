import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HotelBookingService, HotelBookingCreateRequest } from '../../../services/hotel-booking.service';
import { HotelService } from '../../../services/hotel.service';
import { OtpPopupComponent } from '../../../shared/otp-popup/otp-popup.component';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-hotel-booking',
  standalone: true,
  imports: [CommonModule, FormsModule, OtpPopupComponent],
  templateUrl: './hotel-booking.component.html',
  styleUrl: './hotel-booking.component.scss'
})
export class HotelBookingComponent implements OnInit {
  // Hotel data
  hotelId: string = '';
  hotelName: string = '';
  hotelLocation: string = '';
  hotelImage: string = '';
  hotelPrice: number = 0;
  hotelStarRating: number = 0;

  // Form
  checkIn: string = '';
  checkOut: string = '';
  numRooms: number = 1;
  numGuests: number = 2;
  guestName: string = '';
  guestEmail: string = '';
  guestPhone: string = '';
  specialRequests: string = '';

  // State
  isLoadingHotel = true;
  isSubmitting = false;
  errorMessage: string = '';

  // OTP
  showOTPForm = false;
  bookingId: string = '';
  otpCode: string = '';
  otpEmail: string = '';
  isVerifyingOTP = false;
  isResendingOTP = false;
  otpError: string = '';
  returnedOtpCode: string = '';  // OTP code returned from API (for demo)

  // Price
  nights: number = 1;
  totalPrice: number = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private hotelBookingService: HotelBookingService,
    private hotelService: HotelService
  ) {}

  async ngOnInit() {
    this.hotelId = this.route.snapshot.paramMap.get('id') || '';

    // Get pre-filled dates from query params
    this.route.queryParams.subscribe(params => {
      this.checkIn = params['check_in'] || '';
      this.checkOut = params['check_out'] || '';
      this.numRooms = parseInt(params['rooms']) || 1;
      this.numGuests = parseInt(params['guests']) || 2;
    });

    if (this.checkIn && this.checkOut) {
      const diff = new Date(this.checkOut).getTime() - new Date(this.checkIn).getTime();
      this.nights = Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)));
    }

    await this.loadHotel();
  }

  async loadHotel() {
    try {
      this.isLoadingHotel = true;
      const response = await firstValueFrom(this.hotelService.getHotelById(this.hotelId));
      if (response && response.EC === 0 && response.hotel) {
        const h = response.hotel;
        this.hotelName = h.hotel_name || '';
        this.hotelLocation = h.location || '';
        this.hotelPrice = h.price || 0;
        this.hotelStarRating = h.star_rating || 0;
        this.hotelImage = h.image_urls ? h.image_urls.split('|')[0] : '';
        this.totalPrice = this.hotelPrice * this.nights * this.numRooms;
      } else {
        this.errorMessage = 'Không tìm thấy khách sạn';
      }
    } catch (error) {
      this.errorMessage = 'Lỗi khi tải thông tin khách sạn';
    } finally {
      this.isLoadingHotel = false;
    }
  }

  async submitBooking() {
    // Validate
    if (!this.guestName || !this.guestEmail || !this.guestPhone) {
      this.errorMessage = 'Vui lòng điền đầy đủ thông tin liên hệ';
      return;
    }
    if (!this.guestEmail.includes('@')) {
      this.errorMessage = 'Email không hợp lệ';
      return;
    }
    if (this.guestPhone.length < 10) {
      this.errorMessage = 'Số điện thoại không hợp lệ';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    try {
      const userId = localStorage.getItem('user_id') || '';
      if (!userId) {
        this.errorMessage = 'Vui lòng đăng nhập để đặt phòng';
        return;
      }

      const data: HotelBookingCreateRequest = {
        hotel_id: this.hotelId,
        user_id: userId,
        check_in: this.checkIn,
        check_out: this.checkOut,
        num_rooms: this.numRooms,
        num_guests: this.numGuests,
        guest_name: this.guestName,
        guest_email: this.guestEmail,
        guest_phone: this.guestPhone,
        special_requests: this.specialRequests
      };

      const response = await firstValueFrom(this.hotelBookingService.createBooking(data));

      if (response.EC === 0 && response.data) {
        this.bookingId = response.data.booking_id;
        this.otpEmail = response.data.contact_email || this.guestEmail;
        this.returnedOtpCode = response.data.otp_code || '';
        this.showOTPForm = true;
      } else {
        this.errorMessage = response.EM || 'Không thể tạo đặt phòng';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.detail || error?.message || 'Lỗi khi đặt phòng';
    } finally {
      this.isSubmitting = false;
    }
  }

  async verifyOTP(code: string) {
    if (!code || code.length !== 6) {
      this.otpError = 'Vui lòng nhập đủ 6 số OTP';
      return;
    }

    this.isVerifyingOTP = true;
    this.otpError = '';

    try {
      const response = await firstValueFrom(
        this.hotelBookingService.verifyOTP(this.bookingId, code)
      );

      if (response.EC === 0) {
        this.router.navigate(['/my-bookings'], { queryParams: { tab: 'hotel' } });
      } else {
        this.otpError = response.EM || 'Mã OTP không đúng';
      }
    } catch (error: any) {
      this.otpError = error?.error?.detail || 'Xác thực thất bại';
    } finally {
      this.isVerifyingOTP = false;
    }
  }

  async resendOTP() {
    this.isResendingOTP = true;
    try {
      const response = await firstValueFrom(this.hotelBookingService.resendOTP(this.bookingId));
      this.returnedOtpCode = response?.data?.otp_code || '';
      this.otpError = 'Mã OTP mới đã được gửi!';
    } catch (error) {
      this.otpError = 'Không thể gửi lại OTP';
    } finally {
      this.isResendingOTP = false;
    }
  }

  goBack() {
    this.router.navigate(['/hotel/detail', this.hotelId]);
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  getStars(): number[] { return [1, 2, 3, 4, 5]; }
}
