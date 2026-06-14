import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HotelService } from '../../../services/hotel.service';
import { firstValueFrom } from 'rxjs';

interface HotelDetail {
  hotel_id: string;
  hotel_name: string;
  location: string;
  description: string;
  address: string;
  star_rating: number;
  review_score: number;
  review_count: number;
  price: number;
  original_price: number;
  discount: number;
  amenities: string[];
  image_urls: string[];
  available_rooms: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

@Component({
  selector: 'app-hotel-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './hotel-detail.component.html',
  styleUrl: './hotel-detail.component.scss'
})
export class HotelDetailComponent implements OnInit {
  hotel: HotelDetail | null = null;
  isLoading = true;
  errorMessage: string | null = null;

  // Image gallery
  images: string[] = [];
  selectedImage: string = '';
  selectedImageIndex: number = 0;

  // Lightbox
  isLightboxOpen = false;
  activeLightboxImageIndex = 0;

  // Booking sidebar
  checkIn: string = '';
  checkOut: string = '';
  numRooms: number = 1;
  numGuests: number = 2;
  showBookingSidebar = true;

  get minDate(): string {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  get minCheckOutDate(): string {
    return this.checkIn || this.minDate;
  }

  onCheckInChange(): void {
    if (this.checkIn && this.checkOut) {
      if (new Date(this.checkOut) < new Date(this.checkIn)) {
        this.checkOut = this.checkIn;
      }
    }
  }

  // Description
  isDescriptionExpanded = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private hotelService: HotelService
  ) {
    // Default dates: tomorrow + 2 days
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const checkout = new Date(tomorrow);
    checkout.setDate(tomorrow.getDate() + 2);
    this.checkIn = tomorrow.toISOString().split('T')[0];
    this.checkOut = checkout.toISOString().split('T')[0];
  }

  async ngOnInit() {
    const hotelId = this.route.snapshot.paramMap.get('id');
    if (!hotelId) {
      this.errorMessage = 'Không tìm thấy ID khách sạn';
      this.isLoading = false;
      return;
    }

    // Prefill dates, rooms, and guests from query params if available
    this.route.queryParams.subscribe(params => {
      if (params['check_in']) this.checkIn = params['check_in'];
      if (params['check_out']) this.checkOut = params['check_out'];
      if (params['rooms']) this.numRooms = parseInt(params['rooms']) || 1;
      if (params['guests']) this.numGuests = parseInt(params['guests']) || 2;
    });

    await this.loadHotel(hotelId);
  }

  async loadHotel(hotelId: string) {
    try {
      this.isLoading = true;
      this.errorMessage = null;
      const response = await firstValueFrom(this.hotelService.getHotelById(hotelId));

      if (response && response.EC === 0 && response.hotel) {
        const h = response.hotel;
        this.images = h.image_urls ? h.image_urls.split('|').filter((u: string) => u.trim()) : [];
        this.selectedImage = this.images[0] || '';
        this.hotel = {
          hotel_id: h.hotel_id,
          hotel_name: h.hotel_name || '',
          location: h.location || '',
          description: h.description || '',
          address: h.address || '',
          star_rating: h.star_rating || 0,
          review_score: h.review_score || 0,
          review_count: h.review_count || 0,
          price: h.price || 0,
          original_price: h.original_price || h.price || 0,
          discount: h.discount || 0,
          amenities: Array.isArray(h.amenities) ? h.amenities : (h.amenities ? String(h.amenities).split(',').map((a: string) => a.trim()) : []),
          image_urls: this.images,
          available_rooms: h.available_rooms || 0,
          is_active: h.is_active,
          created_at: h.created_at,
          updated_at: h.updated_at
        };
      } else {
        this.errorMessage = 'Không tìm thấy khách sạn.';
      }
    } catch (error: any) {
      console.error('Error loading hotel:', error);
      this.errorMessage = 'Lỗi khi tải thông tin khách sạn. Vui lòng thử lại.';
    } finally {
      this.isLoading = false;
    }
  }

  // Image gallery
  selectImage(index: number) {
    this.selectedImageIndex = index;
    this.selectedImage = this.images[index];
  }

  // Price calculation
  get nights(): number {
    if (!this.checkIn || !this.checkOut) return 1;
    const diff = new Date(this.checkOut).getTime() - new Date(this.checkIn).getTime();
    return Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)));
  }

  get totalPrice(): number {
    if (!this.hotel) return 0;
    return this.hotel.price * this.nights * this.numRooms;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  getReviewLabelObject(score: number): { text: string; color: string } {
    if (score >= 9) return { text: 'Tuyệt vời', color: 'text-green-700 bg-green-100' };
    if (score >= 8) return { text: 'Rất tốt', color: 'text-green-600 bg-green-50' };
    if (score >= 7) return { text: 'Tốt', color: 'text-blue-600 bg-blue-50' };
    return { text: 'Bình thường', color: 'text-gray-600 bg-gray-100' };
  }

  getStars(): number[] {
    return [1, 2, 3, 4, 5];
  }

  // Description
  getShortDescription(): string {
    if (!this.hotel?.description) return '';
    if (this.hotel.description.length <= 300) return this.hotel.description;
    return this.hotel.description.substring(0, 300) + '...';
  }

  get shouldShowReadMore(): boolean {
    return (this.hotel?.description?.length || 0) > 300;
  }

  // Actions
  goBack() {
    this.router.navigate(['/hotel']);
  }

  onBookNow() {
    if (!this.hotel) return;
    this.router.navigate(['/hotel-booking', this.hotel.hotel_id], {
      queryParams: {
        check_in: this.checkIn,
        check_out: this.checkOut,
        rooms: this.numRooms,
        guests: this.numGuests
      }
    });
  }

  async retryLoad() {
    const hotelId = this.route.snapshot.paramMap.get('id');
    if (hotelId) await this.loadHotel(hotelId);
  }

  // Lightbox actions
  openLightbox(index: number = 0) {
    this.activeLightboxImageIndex = index;
    this.isLightboxOpen = true;
    document.body.style.overflow = 'hidden'; // Lock background scrolling
  }

  closeLightbox() {
    this.isLightboxOpen = false;
    document.body.style.overflow = ''; // Unlock scrolling
  }

  nextLightboxImage(event?: MouseEvent) {
    if (event) event.stopPropagation();
    if (this.images.length === 0) return;
    this.activeLightboxImageIndex = (this.activeLightboxImageIndex + 1) % this.images.length;
  }

  prevLightboxImage(event?: MouseEvent) {
    if (event) event.stopPropagation();
    if (this.images.length === 0) return;
    this.activeLightboxImageIndex = (this.activeLightboxImageIndex - 1 + this.images.length) % this.images.length;
  }

  // Amenity icon mapper
  getAmenityIcon(amenity: string): string {
    const a = amenity.toLowerCase();
    if (a.includes('wifi') || a.includes('internet') || a.includes('mạng')) return 'fa-wifi';
    if (a.includes('hồ bơi') || a.includes('bể bơi') || a.includes('pool')) return 'fa-person-swimming';
    if (a.includes('gym') || a.includes('thể hình') || a.includes('fitness') || a.includes('tập thể dục')) return 'fa-dumbbell';
    if (a.includes('spa') || a.includes('massage') || a.includes('làm đẹp') || a.includes('trị liệu')) return 'fa-spa';
    if (a.includes('nhà hàng') || a.includes('restaurant') || a.includes('ăn uống') || a.includes('ẩm thực')) return 'fa-utensils';
    if (a.includes('bar') || a.includes('lounge') || a.includes('rượu')) return 'fa-glass-martini-alt';
    if (a.includes('bãi đỗ') || a.includes('đỗ xe') || a.includes('parking') || a.includes('gửi xe')) return 'fa-car';
    if (a.includes('điều hòa') || a.includes('máy lạnh') || a.includes('air cond')) return 'fa-snowflake';
    if (a.includes('bữa sáng') || a.includes('breakfast') || a.includes('ăn sáng')) return 'fa-mug-saucer';
    if (a.includes('thang máy') || a.includes('elevator')) return 'fa-elevator';
    if (a.includes('lễ tân') || a.includes('reception') || a.includes('front desk') || a.includes('hỗ trợ')) return 'fa-bell-concierge';
    if (a.includes('giặt') || a.includes('laundry') || a.includes('ủi')) return 'fa-jug-detergent';
    if (a.includes('thú cưng') || a.includes('pet') || a.includes('động vật')) return 'fa-paw';
    if (a.includes('tivi') || a.includes('tv') || a.includes('truyền hình')) return 'fa-tv';
    if (a.includes('tủ lạnh') || a.includes('mini bar') || a.includes('fridge')) return 'fa-box';
    if (a.includes('an ninh') || a.includes('bảo vệ') || a.includes('security')) return 'fa-shield-halved';
    return 'fa-circle-check'; // default
  }
}
