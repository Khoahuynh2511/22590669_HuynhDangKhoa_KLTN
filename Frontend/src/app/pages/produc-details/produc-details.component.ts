import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { SearchBarComponent } from '../../components/search-bar/search-bar.component';
import { HotelService } from '../../services/hotel.service';
import { TourService } from '../../services/tour.service';
import { ActivatedRoute, Router } from '@angular/router';
import { Tour } from '../../shared/models/tour.model';
import { TourCardComponent } from '../../components/tour-card/tour-card.component';

interface Hotel {
  name: string;
  rating: number;
  reviews: number;
  location: string;
  images: string[];
  price: number;
  description: string;
  address: string;
  amenities: any[]
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
  imports: [CommonModule, TourCardComponent],
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
    private router: Router
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
        this.route.queryParams.subscribe(res => {
          let result = this.hotelService.filterHotels(res['param']);
          if (result.length > 0) {
            this.hotel.name = result[0].name;
            this.hotel.location = result[0].location;
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
    if (tour.discount && tour.original_price) {
      return tour.original_price * (1 - tour.discount / 100);
    }
    return tour.price;
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
    if (this.tour.description.length <= this.descriptionMaxLength) {
      return this.tour.description;
    }
    return this.tour.description.substring(0, this.descriptionMaxLength) + '...';
  }

  getFullDescription(): string {
    return this.tour?.description || '';
  }

  shouldShowReadMore(): boolean {
    return (this.tour?.description?.length || 0) > this.descriptionMaxLength;
  }

  toggleDescription(): void {
    this.isDescriptionExpanded = !this.isDescriptionExpanded;
  }

  formatDescriptionText(text: string): string {
    if (!text) return '';
    
    let formatted = text;
    
    formatted = formatted.replace(/Ngày \d+:/g, '<strong class="day-header">$&</strong> ');
    formatted = formatted.replace(/\*\*\*(.*?)\*\*\*/g, '<div class="note-box">$1</div>');
    formatted = formatted.replace(/\*\*\*/g, '');
    formatted = formatted.replace(/\*\*/g, '');
    formatted = formatted.replace(/\*/g, '');
    formatted = formatted.replace(/-{10,}o0o0o0o0o-{10,}/gi, '');
    formatted = formatted.replace(/-{5,}[o0o0o0o0o]+-{5,}/gi, '');
    formatted = formatted.replace(/[-]{10,}/g, '');
    formatted = formatted.replace(/Quý khách/g, '<span class="highlight-text">Quý khách</span>');
    formatted = formatted.replace(/Đà Lạt/g, '<span class="location-text">Đà Lạt</span>');
    
    return formatted;
  }

  splitDescriptionByDays(): Array<{day: string, content: string}> {
    if (!this.tour?.description) {
      return [];
    }
    
    const days: Array<{day: string, content: string}> = [];
    const text = this.tour.description;
    const dayRegex = /Ngày \d+:[^\n]*/g;
    const matches = [...text.matchAll(dayRegex)];
    
    if (matches.length === 0) {
      return [{ day: '', content: text }];
    }
    
    for (let i = 0; i < matches.length; i++) {
      const start = matches[i].index!;
      const end = i < matches.length - 1 ? matches[i + 1].index! : text.length;
      const day = matches[i][0];
      const content = text.substring(start + day.length, end).trim();
      
      days.push({ day: day.trim(), content });
    }
    
    return days;
  }

  onBookTour(): void {
    if (this.tour) {
      this.router.navigate(['/booking', this.tour.package_id]);
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

}
