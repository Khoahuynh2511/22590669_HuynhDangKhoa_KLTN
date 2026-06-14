import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FlightBookingService, FlightBookingCreateRequest } from '../../../services/flight-booking.service';
import { Flight } from '../../../services/flight.service';
import { OtpPopupComponent } from '../../../shared/otp-popup/otp-popup.component';
import { SeatSelectionComponent } from '../../../components/seat-selection/seat-selection.component';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-flight-booking',
  standalone: true,
  imports: [CommonModule, FormsModule, OtpPopupComponent, SeatSelectionComponent],
  templateUrl: './flight-booking.component.html',
  styleUrl: './flight-booking.component.scss'
})
export class FlightBookingComponent implements OnInit {
  flight: Flight | null = null;
  flightId: string = '';

  // Form
  seatClass: string = 'economy';
  numPassengers: number = 0; // starts at 0, updated by seat selection
  selectedSeats: string[] = [];
  passengerName: string = '';
  passengerEmail: string = '';
  passengerPhone: string = '';
  specialRequests: string = '';

  // State
  isLoadingFlight = false;
  isSubmitting = false;
  errorMessage: string = '';
  currentStep: number = 1;

  // OTP
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

  // Price
  unitPrice: number = 0;
  totalPrice: number = 0;

  seatClassOptions = [
    { value: 'economy', label: 'Phổ thông', desc: 'Ghế tiêu chuẩn, đầy đủ tiện nghi' },
    { value: 'business', label: 'Thương gia', desc: 'Ghế rộng hơn, ưu tiên lên máy bay' },
    { value: 'first_class', label: 'Hạng nhất', desc: 'Không gian riêng, dịch vụ cao cấp' }
  ];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private flightBookingService: FlightBookingService
  ) {}

  async ngOnInit() {
    this.flightId = this.route.snapshot.paramMap.get('id') || '';
    const nav = this.router.getCurrentNavigation();
    const state = nav?.extras?.state || history.state;
    if (state && state['flight']) {
      this.flight = state['flight'] as Flight;
      this.updatePrice();
    } else {
      this.errorMessage = 'Không tìm thấy thông tin chuyến bay. Vui lòng tìm kiếm lại.';
    }
  }

  updatePrice() {
    if (!this.flight) return;
    this.unitPrice = this.getPriceByClass(this.seatClass);
    this.totalPrice = this.unitPrice * (this.selectedSeats.length || 1);
  }

  onSeatsSelected(seats: string[]) {
    this.selectedSeats = seats;
    this.numPassengers = seats.length;
    this.updatePrice();
  }

  getPriceByClass(cls: string): number {
    if (!this.flight) return 0;
    const prices: Record<string, number> = {
      economy: this.flight.price.economy,
      business: this.flight.price.business,
      first_class: this.flight.price.first_class
    };
    return Number(prices[cls]) || 0;
  }

  onSeatClassChange() { 
    this.selectedSeats = [];
    this.numPassengers = 0;
    this.updatePrice(); 
  }
  onPassengersChange() { this.updatePrice(); }

  getSeatClassDesc(cls: string): string {
    const found = this.seatClassOptions.find(o => o.value === cls);
    return found?.desc || '';
  }

  getSeatClassLabel(cls: string): string {
    const found = this.seatClassOptions.find(o => o.value === cls);
    return found ? found.label : cls;
  }

  getDepartureDate(): string {
    if (!this.flight?.departure?.date) return '';
    const d = new Date(this.flight.departure.date);
    return d.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  startCountdown() {
    this.otpCountdown = 300;
    if (this.countdownInterval) clearInterval(this.countdownInterval);
    this.countdownInterval = setInterval(() => {
      this.otpCountdown--;
      if (this.otpCountdown <= 0) {
        clearInterval(this.countdownInterval);
        this.otpError = 'Mã OTP đã hết hạn. Vui lòng gửi lại.';
      }
    }, 1000);
  }

  formatCountdown(): string {
    const m = Math.floor(this.otpCountdown / 60);
    const s = this.otpCountdown % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  async submitBooking() {
    if (this.selectedSeats.length === 0) {
      this.errorMessage = 'Vui lòng chọn ít nhất một ghế trên sơ đồ';
      return;
    }
    if (!this.passengerName || !this.passengerEmail || !this.passengerPhone) {
      this.errorMessage = 'Vui lòng điền đầy đủ thông tin liên hệ';
      return;
    }
    if (!this.passengerEmail.includes('@')) {
      this.errorMessage = 'Email không hợp lệ';
      return;
    }
    if (this.passengerPhone.length < 10) {
      this.errorMessage = 'Số điện thoại không hợp lệ';
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';
    try {
      const data: FlightBookingCreateRequest = {
        flight_id: this.flightId,
        seat_class: this.seatClass,
        num_passengers: this.numPassengers,
        passenger_name: this.passengerName,
        passenger_email: this.passengerEmail,
        passenger_phone: this.passengerPhone,
        selected_seats: this.selectedSeats.join(',')
      };
      const response = await firstValueFrom(this.flightBookingService.createBooking(data));
      if (response.EC === 0 && response.data) {
        this.bookingId = response.data.booking_id;
        this.otpEmail = response.data.contact_email || this.passengerEmail;
        this.returnedOtpCode = response.data.otp_code || '';
        this.showOTPForm = true;
        this.currentStep = 2;
        this.startCountdown();
      } else {
        this.errorMessage = response.EM || 'Không thể tạo đặt vé';
      }
    } catch (error: any) {
      this.errorMessage = error?.error?.detail || error?.message || 'Lỗi khi đặt vé';
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
      const response = await firstValueFrom(this.flightBookingService.verifyOTP(this.bookingId, code));
      if (response.EC === 0) {
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        this.router.navigate(['/my-bookings'], { queryParams: { tab: 'flight' } });
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
      const response = await firstValueFrom(this.flightBookingService.resendOTP(this.bookingId));
      this.returnedOtpCode = response?.data?.otp_code || '';
      this.otpError = 'Mã OTP mới đã được gửi!';
      this.startCountdown();
    } catch (error) {
      this.otpError = 'Không thể gửi lại OTP';
    } finally {
      this.isResendingOTP = false;
    }
  }

  goBack() { this.router.navigate(['/flights']); }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }
}
