import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DecimalPipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { StateHotel } from '../../shared/models/hotelState.model';

@Component({
  selector: 'app-hotel-card',
  imports: [CommonModule],
  templateUrl: './hotel-card.component.html',
  styleUrl: './hotel-card.component.scss',
  providers: [DecimalPipe]
})
export class HotelCardComponent {

  @Input('hotel') public hotel!: StateHotel;

  constructor(
    private router: Router,
    private decimalPipe: DecimalPipe,
    private route: ActivatedRoute
  ) { }

  get nights(): number {
    const qp = this.route.snapshot.queryParams;
    const checkIn = qp['check_in'];
    const checkOut = qp['check_out'];
    if (!checkIn || !checkOut) return 1;
    const diff = new Date(checkOut).getTime() - new Date(checkIn).getTime();
    return Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)));
  }

  toDetail(_param?: string): void {
    const qp = this.route.snapshot.queryParams;
    this.router.navigate(['hotel/detail', this.hotel.hotel_id], {
      queryParams: {
        check_in: qp['check_in'] || null,
        check_out: qp['check_out'] || null,
        rooms: qp['rooms'] || null,
        guests: qp['guests'] || null
      }
    });
  }

  onSelectClick(event: Event): void {
    event.stopPropagation();
    this.toDetail();
  }

  getReviewLabel(): string {
    const score = this.hotel?.review_score ?? 0;
    if (score >= 9) return 'Tuyệt vời';
    if (score >= 8) return 'Rất tốt';
    if (score >= 7) return 'Tốt';
    return 'Bình thường';
  }

  getReviewClass(): string {
    const score = this.hotel?.review_score ?? 0;
    if (score >= 9) return 'review-excellent';
    if (score >= 8) return 'review-very-good';
    if (score >= 7) return 'review-good';
    return 'review-normal';
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN').format(price);
  }

  formatReviews(count: number): string {
    if (count >= 1000) {
      return (count / 1000).toFixed(1).replace('.0', '') + 'k';
    }
    return count.toString();
  }

  getMainImage(): string {
    if (this.hotel?.image_urls) {
      const urls = this.hotel.image_urls.split('|');
      return urls[0] || 'img/hotel.jpeg';
    }
    return 'img/hotel.jpeg';
  }

  /** Get up to 3 gallery images (excluding main) */
  getGalleryImages(): string[] {
    if (this.hotel?.image_urls) {
      const urls = this.hotel.image_urls.split('|').filter(u => u.trim());
      return urls.slice(1, 4);
    }
    return [];
  }

  /** Get placeholder count to fill 3 thumbnail slots */
  getPlaceholders(): number[] {
    const galleryCount = this.getGalleryImages().length;
    const remaining = 3 - galleryCount;
    return remaining > 0 ? Array(remaining).fill(0) : [];
  }

  /** Get star array [1,2,3,4,5] */
  getStarArray(): number[] {
    return [1, 2, 3, 4, 5];
  }

  /** Get first 3 amenities for display */
  getDisplayAmenities(): string[] {
    if (!this.hotel?.amenities) return [];
    return this.hotel.amenities.slice(0, 3);
  }

}
