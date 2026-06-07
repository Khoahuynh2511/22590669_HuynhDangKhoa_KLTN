import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Tour } from '../../shared/models/tour.model';
import { FavoriteService } from '../../services/favorite.service';
import { AuthStateService } from '../../services/auth-state.service';
import { Subscription } from 'rxjs';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-tour-card',
  imports: [CommonModule, RouterLink],
  providers: [MessageService],
  templateUrl: './tour-card.component.html',
  styleUrl: './tour-card.component.scss'
})
export class TourCardComponent implements OnInit, OnDestroy {
  @Input() tour!: Tour;
  @Input() showDetails: boolean = true;

  // These are now handled internally but kept as inputs for override if needed
  @Input() isAuthenticated: boolean = false;
  @Input() isFavorite: boolean = false;
  @Input() isLoadingFavorite: boolean = false;

  @Output() viewDetails = new EventEmitter<string>();
  @Output() toggleFavorite = new EventEmitter<string>();

  private favoriteSub?: Subscription;
  private readonly fallbackImage = 'img/hotel.jpeg';

  constructor(
    private favoriteService: FavoriteService,
    private authStateService: AuthStateService,
    private messageService: MessageService
  ) { }

  ngOnInit() {
    this.isAuthenticated = this.authStateService.getIsAuthenticated();

    // Subscribe to auth state
    this.authStateService.isAuthenticated$.subscribe(isAuth => {
      this.isAuthenticated = isAuth;
    });

    // Subscribe to global favorite state
    this.favoriteSub = this.favoriteService.favoriteStatus$.subscribe(statusMap => {
      if (this.tour && this.tour.package_id) {
        this.isFavorite = statusMap.get(this.tour.package_id) || false;
      }
    });
  }

  ngOnDestroy() {
    this.favoriteSub?.unsubscribe();
  }

  // Parse image_urls (pipe-separated) into array
  getImageUrls(): string[] {
    if (this.tour.image_urls) {
      const urls = this.tour.image_urls
        .split('|')
        .map(url => url.trim())
        .filter(url => this.isDisplayableImageUrl(url));
      // Reverse to get last image as featured (as per user requirement)
      return urls.reverse();
    }
    const imageUrl = this.tour.image_url?.trim();
    return imageUrl && this.isDisplayableImageUrl(imageUrl) ? [imageUrl] : [];
  }

  // Get featured image (last image in reversed list)
  getFeaturedImage(): string {
    const urls = this.getImageUrls();
    return urls.length > 0 ? urls[0] : this.fallbackImage;
  }

  // Get gallery images (next 3 images after featured)
  getGalleryImages(): string[] {
    const urls = this.getImageUrls();
    return urls.length > 1 ? urls.slice(1, 4) : []; // Get 3 images after featured
  }

  onImageError(event: Event): void {
    const image = event.target as HTMLImageElement;
    if (image.src.endsWith(this.fallbackImage)) return;
    image.src = this.fallbackImage;
  }

  private isDisplayableImageUrl(url: string): boolean {
    return !!url && !url.includes('/_next/static/media/');
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  getDiscountedPrice(): number {
    if (this.tour.discount && this.tour.original_price) {
      return this.tour.original_price * (1 - this.tour.discount / 100);
    }
    return this.tour.price;
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }).format(date);
    } catch (error) {
      console.warn('Date format error:', error);
      return dateString;
    }
  }

  getShortDescription(): string {
    if (!this.tour.description) return '';
    const maxLength = 120;
    if (this.tour.description.length <= maxLength) {
      return this.tour.description;
    }
    return this.tour.description.substring(0, maxLength) + '...';
  }

  isNewTour(): boolean {
    if (!this.tour.created_at) return false;
    const createdDate = new Date(this.tour.created_at);
    const now = new Date();
    const daysDiff = Math.floor((now.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
    return daysDiff <= 30;
  }

  getCategoryName(category: string): string {
    const categoryMap: { [key: string]: string } = {
      'beach': 'Biển',
      'mountain': 'Núi',
      'city': 'Thành phố',
      'cultural': 'Văn hóa',
      'adventure': 'Phiêu lưu',
      'relax': 'Nghỉ dưỡng'
    };
    return categoryMap[category] || category;
  }

  openImage(url: string): void {
    window.open(url, '_blank');
  }

  onViewDetailsClick(event: Event): void {
    // Emit event để parent component (chatbot) xử lý navigate và đóng chatbot
    if (this.viewDetails.observers.length > 0) {
      event.preventDefault();
      this.viewDetails.emit(this.tour.package_id);
    }
    // Nếu không có listener, để RouterLink hoạt động bình thường
  }

  async onFavoriteClick(event: Event): Promise<void> {
    console.log('=== Favorite button clicked! ===', this.tour.package_id);

    // Prevent all default behaviors and stop propagation
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    if (!this.isAuthenticated) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Cần đăng nhập',
        detail: 'Vui lòng đăng nhập để thêm tour vào yêu thích',
        life: 3000
      });
      return;
    }

    try {
      const newState = await this.favoriteService.toggleFavorite(this.tour.package_id);

      // Emit event as well for components that might want to react (like MyFavorites list removal)
      this.toggleFavorite.emit(this.tour.package_id);

      this.messageService.add({
        severity: 'success',
        summary: newState ? 'Đã thêm' : 'Đã xóa',
        detail: newState ? 'Đã thêm vào yêu thích' : 'Đã xóa khỏi yêu thích',
        life: 2000
      });
    } catch (error: any) {
      console.error('Error toggling favorite:', error);
      this.messageService.add({
        severity: 'error',
        summary: 'Lỗi',
        detail: error?.message || 'Không thể cập nhật trạng thái yêu thích',
        life: 3000
      });
    }
  }
}
