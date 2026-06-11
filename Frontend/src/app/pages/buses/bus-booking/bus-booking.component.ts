import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { BusBookingService, BusBookingCreateRequest } from '../../../services/bus-booking.service';
import { Bus } from '../../../services/bus.service';
import { OtpPopupComponent } from '../../../shared/otp-popup/otp-popup.component';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-bus-booking',
  standalone: true,
  imports: [CommonModule, FormsModule, OtpPopupComponent],
  templateUrl: './bus-booking.component.html',
  styleUrl: './bus-booking.component.scss'
})
export class BusBookingComponent implements OnInit {
  bus: Bus | null = null;
  busId: string = '';

  selectedSeatType: string = '';
  numPassengers: number = 1;
  passengerName: string = '';
  passengerEmail: string = '';
  passengerPhone: string = '';
  specialRequests: string = '';

  isSubmitting = false;
  errorMessage: string = '';
  currentStep: number = 1;

  showOTPForm = false;
  bookingId: string = '';
  otpCode: string = '';
  otpEmail: string = '';
  isVerifyingOTP = false;
  isResendingOTP = false;
  otpError: string = '';
  otpCountdown: number = 300;
  countdownInterval: any;
  returnedOtpCode: string = '';  // OTP code returned from API (for demo)

  unitPrice: number = 0;
  totalPrice: number = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private busBookingService: BusBookingService
  ) {}

  async ngOnInit() {
    this.busId = this.route.snapshot.paramMap.get('id') || '';
    const nav = this.router.getCurrentNavigation();
    const state = nav?.extras?.state || history.state;
    if (state && state['bus']) {
      this.bus = state['bus'] as Bus;
      if (this.bus.seats) {
        const keys = Object.keys(this.bus.seats);
        if (keys.length > 0) {
          this.selectedSeatType = keys[0];
          this.updatePrice();
        }
      }
    } else {
      this.errorMessage = 'Không tìm thấy thông tin chuyến xe. Vui lòng tìm kiếm lại.';
    }
  }

  updatePrice() {
    if (!this.bus || !this.selectedSeatType) return;
    this.unitPrice = this.bus.seats[this.selectedSeatType]?.price || 0;
    this.totalPrice = this.unitPrice * this.numPassengers;
  }

  getSeatTypeEntries(): { key: string; name: string; price: number; available: number; desc: string }[] {
    if (!this.bus?.seats) return [];
    return Object.entries(this.bus.seats).map(([key, val]) => ({
      key, name: val.name, price: val.price,
      available: this.bus?.availability?.[key] || 0,
      desc: val.description || ''
    }));
  }

  getDepartureDate(): string {
    if (!this.bus?.departure?.date) return '';
    const d = new Date(this.bus.departure.date);
    return d.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  startCountdown() {
    this.otpCountdown = 300;
    if (this.countdownInterval) clearInterval(this.countdownInterval);
    this.countdownInterval = setInterval(() => {
      this.otpCountdown--;
      if (this.otpCountdown <= 0) { clearInterval(this.countdownInterval); this.otpError = 'Mã OTP đã hết hạn. Vui lòng gửi lại.'; }
    }, 1000);
  }

  formatCountdown(): string {
    const m = Math.floor(this.otpCountdown / 60);
    const s = this.otpCountdown % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  async submitBooking() {
    if (!this.selectedSeatType) { this.errorMessage = 'Vui lòng chọn loại ghế'; return; }
    if (!this.passengerName || !this.passengerEmail || !this.passengerPhone) {
      this.errorMessage = 'Vui lòng điền đầy đủ thông tin liên hệ'; return;
    }
    if (!this.passengerEmail.includes('@')) { this.errorMessage = 'Email không hợp lệ'; return; }
    if (this.passengerPhone.length < 10) { this.errorMessage = 'Số điện thoại không hợp lệ'; return; }

    this.isSubmitting = true; this.errorMessage = '';
    try {
      const data: BusBookingCreateRequest = {
        bus_id: this.busId, seat_type_id: this.selectedSeatType,
        num_passengers: this.numPassengers, passenger_name: this.passengerName,
        passenger_email: this.passengerEmail, passenger_phone: this.passengerPhone
      };
      const response = await firstValueFrom(this.busBookingService.createBooking(data));
      if (response.EC === 0 && response.data) {
        this.bookingId = response.data.booking_id;
        this.otpEmail = response.data.contact_email || this.passengerEmail;
        this.returnedOtpCode = response.data.otp_code || '';
        this.showOTPForm = true;
        this.currentStep = 2;
        this.startCountdown();
      } else { this.errorMessage = response.EM || 'Không thể tạo đặt vé'; }
    } catch (error: any) { this.errorMessage = error?.error?.detail || error?.message || 'Lỗi khi đặt vé'; }
    finally { this.isSubmitting = false; }
  }

  async verifyOTP(code: string) {
    if (!code || code.length !== 6) { this.otpError = 'Vui lòng nhập đủ 6 số OTP'; return; }
    this.isVerifyingOTP = true; this.otpError = '';
    try {
      const response = await firstValueFrom(this.busBookingService.verifyOTP(this.bookingId, code));
      if (response.EC === 0) {
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        this.router.navigate(['/my-bookings'], { queryParams: { tab: 'bus' } });
      } else { this.otpError = response.EM || 'Mã OTP không đúng'; }
    } catch (error: any) { this.otpError = error?.error?.detail || 'Xác thực thất bại'; }
    finally { this.isVerifyingOTP = false; }
  }

  async resendOTP() {
    this.isResendingOTP = true;
    try {
      const response = await firstValueFrom(this.busBookingService.resendOTP(this.bookingId));
      this.returnedOtpCode = response?.data?.otp_code || '';
      this.otpError = 'Mã OTP mới đã được gửi!'; this.startCountdown();
    } catch (error) { this.otpError = 'Không thể gửi lại OTP'; }
    finally { this.isResendingOTP = false; }
  }

  goBack() { this.router.navigate(['/buses']); }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }
}
