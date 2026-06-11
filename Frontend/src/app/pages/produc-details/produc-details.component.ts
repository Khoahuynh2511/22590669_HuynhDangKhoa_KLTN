import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { HotelService } from '../../services/hotel.service';
import { TourService } from '../../services/tour.service';
import { ActivatedRoute, Router } from '@angular/router';
import { Tour } from '../../shared/models/tour.model';
import { TourCardComponent } from '../../components/tour-card/tour-card.component';
import {
  formatDescriptionHtml,
  splitDescriptionByDays as splitDescriptionByDaysUtil,
  truncateDescription
} from '../../shared/utils/text-format.util';
import {
  calculateTourSubtotal,
  clampTourPeopleCount,
  getTourUnitPrice
} from '../../shared/utils/tour-price.util';
import { firstValueFrom } from 'rxjs';

interface Hotel {
  hotel_id?: string;
  name: string;
  rating: number;
  reviews: number;
  location: string;
  images: string[];
  price: number;
  description: string;
  address: string;
  amenities: any[];
  available_rooms?: number;
  discount?: number;
  original_price?: number;
  star_rating?: number;
}

interface RoomOption {
  id: number,
  name: string;
  description: string;
  guests: number;
  price: number;
  originalPrice: number;
  breakfastIncluded: boolean;
}

interface Room {
  name: string;
  imageUrl: string;
  size: string;
  options: RoomOption[];
}

@Component({
  selector: 'app-produc-details',
  imports: [CommonModule, FormsModule, TourCardComponent],
  templateUrl: './produc-details.component.html',
  styleUrl: './produc-details.component.scss'
})
export class ProducDetailsComponent implements OnInit {
  tour: Tour | null = null;
  relatedTours: Tour[] = [];
  isLoadingTour = true;
  isLoadingRelatedTours = false;
  isTourMode = false;
  errorMessage: string | null = null;
  currentTourId: string | null = null;
  isDescriptionExpanded = false;
  descriptionMaxLength = 500;
  bookingPeople = 1;

  hotel: Hotel = {
    name: 'Bukit Vipassana Hotel',
    location: 'Lembang, Bandung',
    rating: 8.4,
    reviews: 1160,
    price: 368569,
    images: [
      'img/hotel.jpeg',
      'img/hotel.jpeg',
      'img/hotel.jpeg',
      'img/hotel.jpeg',
      'img/hotel.jpeg',
      'img/hotel.jpeg',
      'img/hotel.jpeg',
    ],
    description: 'Khách sạn này mang đến sự thoải mái và tiện ích tốt nhất cho bạn.',
    address: 'JL. Kolonel Masturi No. 99, Lembang, Bandung, Jawa Barat, Indonesia, 40391',
    amenities: ['Nhà hàng', 'Hồ bơi', 'Lễ tân 24 giờ', 'WiFi', 'Bãi đỗ xe'],

  };


  room: Room = {
    name: 'Superior Twin Bed',
    imageUrl: 'img/hotel.jpeg',
    size: '24.0 m²',
    options: [
      {
        id: 1,
        name: 'Không bao gồm bữa sáng',
        description: '1 giường đôi',
        guests: 2,
        price: 368569,
        originalPrice: 491125,
        breakfastIncluded: false,
      },
      {
        id: 2,
        name: 'Bao gồm bữa sáng cho 1 người',
        description: '1 giường đôi',
        guests: 1,
        price: 417709,
        originalPrice: 556945,
        breakfastIncluded: true,
      },
    ],
  };


  constructor(
    private hotelService: HotelService,
    private tourService: TourService,
    private route: ActivatedRoute,
    private router: Router,
    private sanitizer: DomSanitizer
  ) { }

  async ngOnInit(): Promise<void> {
    this.route.params.subscribe(async params => {
      const id = params['id'];

      if (id) {
        this.isTourMode = true;
        this.currentTourId = id;
        await this.loadTourDetails(id);
      } else {
        this.isTourMode = false;
        this.currentTourId = null;
        // Check for hotel_id query param first
        this.route.queryParams.subscribe(async res => {
          const hotelId = res['id'];
          if (hotelId) {
            await this.loadHotelDetails(hotelId);
          } else {
            // Fallback to name search
            const hotelName = res['param'];
            if (hotelName) {
              let result = this.hotelService.filterHotels(hotelName);
              if (result.length > 0) {
                this.hotel.name = result[0].hotel_name;
                this.hotel.location = result[0].location;
              }
            }
          }
        });
      }
    });
  }

  async loadTourDetails(tourId: string): Promise<void> {
    try {
      this.isLoadingTour = true;
      this.errorMessage = null;
      console.log('Loading tour details for ID:', tourId);

      this.tour = await this.tourService.getTourById(tourId);

      if (!this.tour) {
        this.errorMessage = 'Không tìm thấy tour với ID này. Tour có thể đã bị xóa hoặc không tồn tại.';
        console.error('Tour not found with ID:', tourId);
        return;
      }

      this.bookingPeople = clampTourPeopleCount(this.bookingPeople, this.tour.available_slots);

      await this.loadRelatedTours();
    } catch (error: any) {
      console.error('Error loading tour:', error);
      const errorMsg = error?.message || 'Lỗi khi tải thông tin tour. Vui lòng thử lại sau.';

      if (errorMsg.includes('500') || errorMsg.includes('máy chủ')) {
        this.errorMessage = 'Lỗi máy chủ. Hệ thống đang gặp sự cố. Vui lòng thử lại sau vài phút hoặc liên hệ hỗ trợ nếu vấn đề vẫn tiếp tục.';
      } else {
        this.errorMessage = errorMsg;
      }

      this.tour = null;
    } finally {
      this.isLoadingTour = false;
    }
  }

  async loadHotelDetails(hotelId: string): Promise<void> {
    try {
      this.isLoadingTour = true;
      this.errorMessage = null;
      console.log('Loading hotel details for ID:', hotelId);

      const response = await firstValueFrom(this.hotelService.getHotelById(hotelId));

      if (response && response.EC === 0 && response.hotel) {
        const apiHotel = response.hotel;
        // Map API response to hotel interface
        this.hotel = {
          hotel_id: apiHotel.hotel_id,
          name: apiHotel.hotel_name || '',
          rating: apiHotel.review_score || 0,
          reviews: apiHotel.review_count || 0,
          location: apiHotel.location || '',
          images: apiHotel.image_urls ? apiHotel.image_urls.split('|').filter((url: string) => url.trim()) : [],
          price: apiHotel.price || 0,
          description: apiHotel.description || '',
          address: apiHotel.address || '',
          amenities: apiHotel.amenities ? (Array.isArray(apiHotel.amenities) ? apiHotel.amenities : String(apiHotel.amenities).split(',').map((a: string) => a.trim())) : [],
          available_rooms: apiHotel.available_rooms,
          discount: apiHotel.discount || 0,
          original_price: apiHotel.original_price || apiHotel.price || 0,
          star_rating: apiHotel.star_rating || 0
        };
      } else {
        this.errorMessage = 'Không tìm thấy khách sạn với ID này.';
        console.error('Hotel not found with ID:', hotelId);
      }
    } catch (error: any) {
      console.error('Error loading hotel:', error);
      this.errorMessage = 'Lỗi khi tải thông tin khách sạn. Vui lòng thử lại sau.';
    } finally {
      this.isLoadingTour = false;
    }
  }

  async retryLoadTour(): Promise<void> {
    if (this.currentTourId) {
      await this.loadTourDetails(this.currentTourId);
    } else {
      const tourId = this.route.snapshot.params['id'];
      if (tourId) {
        this.currentTourId = tourId;
        await this.loadTourDetails(tourId);
      }
    }
  }

  async loadRelatedTours(): Promise<void> {
    if (!this.tour || !this.tour.destination) {
      return;
    }

    try {
      this.isLoadingRelatedTours = true;
      const response = await this.tourService.getTourPackages({
        destination: this.tour.destination,
        is_active: true,
        limit: 6
      });

      if (response && response.packages && Array.isArray(response.packages)) {
        this.relatedTours = response.packages
          .filter(t => t.package_id !== this.tour?.package_id)
          .slice(0, 6);
      }
    } catch (error) {
      console.error('Error loading related tours:', error);
      this.relatedTours = [];
    } finally {
      this.isLoadingRelatedTours = false;
    }
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  getDiscountedPrice(tour: Tour): number {
    return getTourUnitPrice(tour);
  }

  getBookingTotalPrice(): number {
    if (!this.tour) {
      return 0;
    }
    return calculateTourSubtotal(this.tour, this.bookingPeople);
  }

  onBookingPeopleChange(value: number): void {
    this.bookingPeople = clampTourPeopleCount(value, this.tour?.available_slots);
  }

  decreaseBookingPeople(): void {
    this.onBookingPeopleChange(this.bookingPeople - 1);
  }

  increaseBookingPeople(): void {
    this.onBookingPeopleChange(this.bookingPeople + 1);
  }

  canIncreaseBookingPeople(): boolean {
    if (!this.tour?.available_slots) {
      return true;
    }
    return this.bookingPeople < this.tour.available_slots;
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

  getImageUrls(): string[] {
    if (this.tour?.image_urls) {
      const urls = this.tour.image_urls.split('|').filter(url => url.trim());
      return urls.reverse();
    }
    return this.tour?.image_url ? [this.tour.image_url] : ['img/tour-default.jpg'];
  }

  getFeaturedImage(): string {
    const urls = this.getImageUrls();
    return urls.length > 0 ? urls[0] : (this.tour?.image_url || 'img/tour-default.jpg');
  }

  getGalleryImages(): string[] {
    const urls = this.getImageUrls();
    return urls.length > 1 ? urls.slice(1) : [];
  }

  openImage(url: string): void {
    window.open(url, '_blank');
  }

  getDescriptionParagraphs(): string[] {
    if (!this.tour?.description) {
      return [];
    }
    return this.tour.description
      .split('\n')
      .map(p => p.trim())
      .filter(p => p.length > 0);
  }

  getShortDescription(): string {
    if (!this.tour?.description) {
      return '';
    }
    return truncateDescription(this.tour.description, this.descriptionMaxLength);
  }

  getFullDescription(): string {
    return this.tour?.description || '';
  }

  shouldShowReadMore(): boolean {
    if (!this.tour?.description) {
      return false;
    }
    return truncateDescription(this.tour.description, this.descriptionMaxLength).endsWith('...');
  }

  toggleDescription(): void {
    this.isDescriptionExpanded = !this.isDescriptionExpanded;
  }

  formatDescriptionText(text: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(formatDescriptionHtml(text));
  }

  splitDescriptionByDays(): Array<{ day: string; content: string }> {
    if (!this.tour?.description) {
      return [];
    }
    return splitDescriptionByDaysUtil(this.tour.description);
  }

  hasMultiDayDescription(): boolean {
    return this.splitDescriptionByDays().some((block) => block.day.length > 0);
  }

  onBookTour(): void {
    if (this.tour) {
      this.router.navigate(['/booking', this.tour.package_id], {
        queryParams: { people: this.bookingPeople }
      });
    }
  }

  scrollToRoomDetails() {
    const element = document.getElementById('room-details');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  }

  onBook(id: number) {
    this.router.navigate([`booking/${id}`])
  }

  goBackToTours(): void {
    this.router.navigate(['/tours']);
  }

  goBackToHotels(): void {
    this.router.navigate(['/hotel']);
  }

  async retryLoadHotel(): Promise<void> {
    const hotelId = this.route.snapshot.queryParams['id'];
    if (hotelId) {
      await this.loadHotelDetails(hotelId);
    }
  }

  getInfoCards(): Array<{type: string, icon: string, label: string, value: string}> {
    if (!this.tour) return [];
    
    const cards: Array<{type: string, icon: string, label: string, value: string}> = [];
    
    cards.push({
      type: 'duration',
      icon: 'fas fa-clock',
      label: 'Thời lượng',
      value: `${this.tour.duration_days} ngày`
    });
    
    if (this.tour.departure_location) {
      cards.push({
        type: 'departure',
        icon: 'fas fa-plane-departure',
        label: 'Xuất phát',
        value: this.tour.departure_location
      });
    }
    
    if (this.tour.start_date || this.tour.end_date) {
      let dateValue = '';
      if (this.tour.start_date && this.tour.end_date) {
        dateValue = `${this.formatDate(this.tour.start_date)} - ${this.formatDate(this.tour.end_date)}`;
      } else if (this.tour.start_date) {
        dateValue = this.formatDate(this.tour.start_date);
      } else if (this.tour.end_date) {
        dateValue = this.formatDate(this.tour.end_date);
      }
      cards.push({
        type: 'date',
        icon: 'fas fa-calendar-alt',
        label: 'Ngày khởi hành',
        value: dateValue
      });
    }
    
    if (this.tour.available_slots) {
      cards.push({
        type: 'slots',
        icon: 'fas fa-users',
        label: 'Còn chỗ',
        value: `${this.tour.available_slots} chỗ`
      });
    }
    
    if (this.tour.discount) {
      cards.push({
        type: 'discount',
        icon: 'fas fa-tag',
        label: 'Giảm giá',
        value: `-${this.tour.discount}%`
      });
    }
    
    if (this.tour.cuisine) {
      cards.push({
        type: 'cuisine',
        icon: 'fas fa-utensils',
        label: 'Ẩm thực',
        value: this.tour.cuisine
      });
    }
    
    if (this.tour.suitable_for) {
      cards.push({
        type: 'suitable',
        icon: 'fas fa-user-check',
        label: 'Phù hợp',
        value: this.tour.suitable_for
      });
    }

    return cards;
  }

  getStarArray(): number[] {
    return [1, 2, 3, 4, 5];
  }

  isFilledStar(index: number): boolean {
    return index < Math.floor(this.hotel.star_rating || 0);
  }

}
