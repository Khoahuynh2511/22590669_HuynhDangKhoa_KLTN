import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PromotionService, Promotion } from '../../services/promotion.service';

@Component({
  selector: 'app-promotions',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './promotions.component.html',
  styleUrl: './promotions.component.scss'
})
export class PromotionsComponent implements OnInit {
  promotions: Promotion[] = [];
  filteredPromotions: Promotion[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  filterType: 'all' | 'active' | 'expired' = 'active';

  constructor(private promotionService: PromotionService) {}

  ngOnInit() {
    this.loadPromotions();
  }

  loadPromotions() {
    this.isLoading = true;
    this.errorMessage = null;

    this.promotionService.getAvailablePromotions().subscribe({
      next: (response) => {
        if (response.EC === 0) {
          this.promotions = response.promotions || [];
          this.applyFilter();
        } else {
          this.errorMessage = response.EM || 'Không thể tải danh sách khuyến mãi';
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading promotions:', error);
        this.errorMessage = 'Lỗi khi tải danh sách khuyến mãi. Vui lòng thử lại sau.';
        this.isLoading = false;
      }
    });
  }

  applyFilter() {
    const now = new Date();
    
    switch (this.filterType) {
      case 'active':
        this.filteredPromotions = this.promotions.filter(promo => {
          const startDate = new Date(promo.start_date);
          const endDate = new Date(promo.end_date);
          return promo.is_active && now >= startDate && now <= endDate && promo.used_count < promo.quantity;
        });
        break;
      case 'expired':
        this.filteredPromotions = this.promotions.filter(promo => {
          const endDate = new Date(promo.end_date);
          return !promo.is_active || now > endDate || promo.used_count >= promo.quantity;
        });
        break;
      default:
        this.filteredPromotions = [...this.promotions];
    }
  }

  changeFilter(type: 'all' | 'active' | 'expired') {
    this.filterType = type;
    this.applyFilter();
  }

  formatDiscount(promo: Promotion): string {
    if (promo.discount_type === 'PERCENTAGE') {
      return `Giảm ${promo.discount_value}%`;
    } else {
      return `Giảm ${this.formatPrice(promo.discount_value)}`;
    }
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  }

  isExpired(promo: Promotion): boolean {
    const now = new Date();
    const endDate = new Date(promo.end_date);
    return !promo.is_active || now > endDate || promo.used_count >= promo.quantity;
  }

  copyToClipboard(code: string) {
    navigator.clipboard.writeText(code).then(() => {
      // Code copied successfully
    }).catch(() => {
      // Failed to copy
    });
  }

  getRemainingQuantity(promo: Promotion): number {
    return Math.max(0, promo.quantity - promo.used_count);
  }
}

