import { Component, OnInit } from '@angular/core';
import { PaymentMethodComponent } from '../../components/payment-method/payment-method.component';
import { HotelDetailsComponent } from '../../components/hotel-details/hotel-details.component';
import { FormsModule } from '@angular/forms';
import { CommonModule, NgFor } from '@angular/common';
import { PromotionService, Promotion } from '../../services/promotion.service';

@Component({
  selector: 'app-payment',
  imports: [
    PaymentMethodComponent,
    HotelDetailsComponent,
    NgFor,
    FormsModule,
    CommonModule
  ],
  templateUrl: './payment.component.html',
  styleUrl: './payment.component.scss'
})
export class PaymentComponent implements OnInit {

  paymentOptions: PaymentOption[] = [
    { name: 'Tài khoản ảo', description: 'BCA, Mandiri, BRIVA, BNI', isNew: true },
    { name: 'Chuyển khoản ngân hàng', description: '', isNew: false },
    { name: 'Thẻ tín dụng/Ghi nợ', description: '', isNew: false },
    { name: 'Cửa hàng tiện lợi', description: '', isNew: false },
  ];

  totalPrice: number = 660000;
  originalPrice: number = 660000;
  couponCode: string = '';
  appliedPromotion: Promotion | null = null;
  discountAmount: number = 0;
  errorMessage: string = '';
  successMessage: string = '';
  isLoadingPromotion: boolean = false;

  constructor(private promotionService: PromotionService) {}

  ngOnInit() {
    this.originalPrice = this.totalPrice;
  }

  applyCoupon() {
    if (!this.couponCode.trim()) {
      this.errorMessage = 'Vui lòng nhập mã khuyến mãi';
      this.successMessage = '';
      return;
    }

    this.isLoadingPromotion = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.promotionService.getPromotionById(this.couponCode.trim()).subscribe({
      next: (response) => {
        this.isLoadingPromotion = false;
        if (response.EC === 0 && response.promotion) {
          const promo = response.promotion;
          
          if (!promo.is_active) {
            this.errorMessage = 'Mã khuyến mãi không còn hoạt động';
            return;
          }

          const now = new Date();
          const startDate = new Date(promo.start_date);
          const endDate = new Date(promo.end_date);

          if (now < startDate) {
            this.errorMessage = 'Mã khuyến mãi chưa có hiệu lực';
            return;
          }

          if (now > endDate) {
            this.errorMessage = 'Mã khuyến mãi đã hết hạn';
            return;
          }

          if (promo.used_count >= promo.quantity) {
            this.errorMessage = 'Mã khuyến mãi đã hết số lượng';
            return;
          }

          this.appliedPromotion = promo;
          this.calculateDiscount();
          this.successMessage = 'Áp dụng mã khuyến mãi thành công';
        } else {
          this.errorMessage = response.EM || 'Mã khuyến mãi không hợp lệ';
        }
      },
      error: (error) => {
        this.isLoadingPromotion = false;
        this.errorMessage = 'Mã khuyến mãi không hợp lệ hoặc không tồn tại';
        console.error('Apply promotion error:', error);
      }
    });
  }

  removeCoupon() {
    this.couponCode = '';
    this.appliedPromotion = null;
    this.discountAmount = 0;
    this.totalPrice = this.originalPrice;
    this.errorMessage = '';
    this.successMessage = '';
  }

  calculateDiscount() {
    if (!this.appliedPromotion) {
      return;
    }

    if (this.appliedPromotion.discount_type === 'PERCENTAGE') {
      this.discountAmount = (this.originalPrice * this.appliedPromotion.discount_value) / 100;
    } else {
      this.discountAmount = this.appliedPromotion.discount_value;
    }

    this.totalPrice = Math.max(0, this.originalPrice - this.discountAmount);
  }

  proceedToPayment() {
    console.log('Proceeding to payment...');
    if (this.appliedPromotion) {
      console.log('Applied promotion:', this.appliedPromotion.promotion_id);
    }
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

}

interface PaymentOption {
  name: string;
  description: string;
  isNew: boolean;
}
