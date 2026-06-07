import { NgFor } from '@angular/common';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CarouselModule, OwlOptions } from 'ngx-owl-carousel-o';
import { PromotionService, Promotion } from '../../services/promotion.service';

@Component({
  selector: 'app-coupon-list',
  imports: [NgFor, CarouselModule],
  templateUrl: './coupon-list.component.html',
  styleUrl: './coupon-list.component.scss',
  encapsulation: ViewEncapsulation.None
})
export class CouponListComponent implements OnInit {

  pathImg = {
    left: 'icon/left.png',
    next: 'icon/next.png'
  }

  coupons: Coupon[] = [];
  isLoading = false;
  errorMessage = '';
  copiedCode: string | null = null;

  constructor(private promotionService: PromotionService) {}

  ngOnInit() {
    this.loadPromotions();
  }

  loadPromotions() {
    this.isLoading = true;
    this.errorMessage = '';
    
    this.promotionService.getAvailablePromotions().subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.coupons = response.promotions.map(promo => ({
            code: promo.code,
            description: promo.name,
            discount: this.formatDiscount(promo)
          }));
        } else {
          this.errorMessage = response.EM || 'Không thể tải danh sách mã khuyến mãi';
        }
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Lỗi khi tải danh sách mã khuyến mãi';
        console.error('Load promotions error:', error);
        this.isLoading = false;
      }
    });
  }

  formatDiscount(promo: Promotion): string {
    if (promo.discount_type === 'PERCENTAGE') {
      return `Giảm ${promo.discount_value}% - ${promo.description}`;
    } else {
      return `Giảm ${this.formatPrice(promo.discount_value)} - ${promo.description}`;
    }
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  customOptions: OwlOptions = {
    loop: true,
    mouseDrag: false,
    touchDrag: false,
    pullDrag: false,
    dots: false,
    margin: 15,
    navSpeed: 700,
    navText: [
      // `<span class="font-semibold text-blue rounded-md block" > < </span>`,
      // `<span class="font-semibold text-blue rounded-md block" > > </span>`
      `<div>
        <span class="font-semibold text-blue block icon-img" >
          <img src="${this.pathImg.left}" alt="">
        </span>
      </div>
      `,
      `
      <div>
        <span class="font-semibold text-blue block icon-img" >
          <img src="${this.pathImg.next}" alt="">
        </span>
      </div>
      `
    ],
    responsive: {
      0: {
        items: 1
      },
      400: {
        items: 2
      },
      740: {
        items: 3
      },
      940: {
        items: 3
      }
    },
    nav: true
  }

  copyToClipboard(code: string) {
    navigator.clipboard.writeText(code).then(() => {
      this.copiedCode = code;
      setTimeout(() => {
        this.copiedCode = null;
      }, 2000);
    }).catch(err => {
      console.error('Lỗi khi sao chép:', err);
      // Fallback method
      const textArea = document.createElement('textarea');
      textArea.value = code;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        this.copiedCode = code;
        setTimeout(() => {
          this.copiedCode = null;
        }, 2000);
      } catch (err) {
        console.error('Không thể sao chép');
      }
      document.body.removeChild(textArea);
    });
  }
}

interface Coupon {
  code: string;
  description: string;
  discount: string;
}
