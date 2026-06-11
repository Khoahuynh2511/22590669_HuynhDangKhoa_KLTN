import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DecimalPipe } from '@angular/common';
import { Router } from '@angular/router';
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

  constructor(private router: Router, private decimalPipe: DecimalPipe) { }

  toDetail(param: any) {
    this.router.navigate(['hotel/detail', this.hotel.hotel_id])
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
