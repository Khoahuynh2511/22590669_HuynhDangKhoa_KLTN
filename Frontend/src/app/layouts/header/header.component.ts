import { CommonModule } from '@angular/common';
import { Component, HostListener, OnInit, OnDestroy } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStateService } from '../../services/auth-state.service';
import { ChatbotService } from '../../services/chatbot.service';
import { NotificationBellComponent } from '../../components/notification-bell/notification-bell.component';
import { Subscription, forkJoin, of, interval } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ClickOutsideDirective } from '../../directives/click-outside.directive';
import { BookingService } from '../../services/booking.service';
import { TrainBookingService } from '../../services/train-booking.service';
import { BusBookingService } from '../../services/bus-booking.service';
import { FlightBookingService } from '../../services/flight-booking.service';
import { HotelBookingService } from '../../services/hotel-booking.service';

@Component({
  selector: 'app-header',
  imports: [RouterLink, RouterLinkActive, CommonModule, ClickOutsideDirective, NotificationBellComponent],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent implements OnInit, OnDestroy {
  isScrolled = false;
  isHomePage = false;
  isAuthenticated = false;
  currentUser: any = null;
  showDropdown = false;
  showActivitiesMenu = false;
  pendingPaymentCount = 0;
  private chatbotSubscription?: Subscription;
  private pendingCountSubscription?: Subscription;


  topMenuPublic: Menu[] = [
    { label: 'Trang chủ', url: '/home' },
    { label: 'Tour du lịch', url: '/tours' },
    { label: 'Tin tức & Cẩm nang', url: '/travel-news' },
    { label: 'Đánh giá', url: '/reviews' },
  ]

  serviceMenu: ServiceMenu[] = [
    { label: 'Kh\u00e1ch s\u1ea1n', url: '/hotel', icon: 'icon/hotel.png' },
    { label: 'V\u00e9 m\u00e1y bay', url: '/flights', icon: 'icon/air-plane.png' },
    { label: 'V\u00e9 t\u00e0u h\u1ecfa', url: '/trains', icon: 'icon/train.png' },
    { label: 'V\u00e9 xe kh\u00e1ch', url: '/buses', icon: 'icon/car.png' },
    { label: 'Ho\u1ea1t \u0111\u1ed9ng', url: '/activities', icon: 'icon/car.png' },
  ];

  get topMenu(): Menu[] {
    if (this.isAuthenticated) {
      return [
        ...this.topMenuPublic,
        { label: 'Đơn hàng', url: '/my-bookings' }
      ];
    }
    return this.topMenuPublic;
  }

  /** Mục con của dropdown "Hoạt động" (service-nav). */
  activitiesMenuItems: Menu[] = [
    { label: '🗺️ Bản đồ khám phá', url: '/explore-map' },
    { label: '🏆 Bảng xếp hạng', url: '/leaderboard' },
    { label: '🎟️ Lễ hội & sự kiện', url: '/festivals' },
    { label: '📋 Lập kế hoạch chuyến đi', url: '/activities' }
  ];

  get isActivitiesAreaActive(): boolean {
    const url = this.router.url?.split('?')[0] || '';
    return url === '/activities' || url.startsWith('/explore-map')
      || url.startsWith('/leaderboard') || url.startsWith('/festivals');
  }

  constructor(
    private router: Router,
    private authStateService: AuthStateService,
    private chatbotService: ChatbotService,
    private bookingService: BookingService,
    private trainBookingService: TrainBookingService,
    private busBookingService: BusBookingService,
    private flightBookingService: FlightBookingService,
    private hotelBookingService: HotelBookingService
  ) { }

  ngOnInit(): void {
    this.checkIfHomePage();
    this.checkAuthState();

    this.router.events.subscribe((ev) => {
      if (ev instanceof NavigationEnd) {
        this.checkIfHomePage();
        this.closeActivitiesMenu();
        this.closeDropdown();
        if (this.isAuthenticated) {
          this.loadPendingPaymentCount();
        }
      }
    });

    this.authStateService.isAuthenticated$.subscribe(isAuth => {
      this.isAuthenticated = isAuth;
      if (isAuth) {
        this.loadPendingPaymentCount();
      } else {
        this.pendingPaymentCount = 0;
      }
    });

    this.authStateService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });

    this.chatbotSubscription = this.chatbotService.openChatbot$.subscribe(() => {
      this.openChatbot();
    });

    // Poll pending payment count every 30 seconds when authenticated
    const pollSub = interval(30000).subscribe(() => {
      if (this.isAuthenticated) {
        this.loadPendingPaymentCount();
      }
    });
    this.pendingCountSubscription = pollSub;
  }

  ngOnDestroy() {
    if (this.chatbotSubscription) {
      this.chatbotSubscription.unsubscribe();
    }
    if (this.pendingCountSubscription) {
      this.pendingCountSubscription.unsubscribe();
    }
  }

  checkAuthState(): void {
    this.isAuthenticated = this.authStateService.getIsAuthenticated();
    this.currentUser = this.authStateService.getCurrentUser();
    if (this.isAuthenticated) {
      this.loadPendingPaymentCount();
    }
  }

  onLogout(): void {
    this.authStateService.logout();
    this.pendingPaymentCount = 0;
    this.router.navigate(['/home']);
  }

  loadPendingPaymentCount(): void {
    if (!this.isAuthenticated) {
      this.pendingPaymentCount = 0;
      return;
    }

    forkJoin({
      tours: this.bookingService.getMyBookings({ limit: 100 }).pipe(catchError(() => of({ data: [] }))),
      trains: this.trainBookingService.getMyBookings().pipe(catchError(() => of({ data: [] }))),
      buses: this.busBookingService.getMyBookings().pipe(catchError(() => of({ data: [] }))),
      flights: this.flightBookingService.getMyBookings().pipe(catchError(() => of({ data: [] }))),
      hotels: this.hotelBookingService.getMyBookings().pipe(catchError(() => of({ data: [] })))
    }).subscribe({
      next: (results: any) => {
        let count = 0;

        if (results.tours && results.tours.data) {
          count += results.tours.data.filter((b: any) => b.status === 'pending' || b.status === 'otp_sent').length;
        }

        if (results.trains && results.trains.data) {
          count += results.trains.data.filter((b: any) => (b.status === 'pending' && b.payment_status !== 'paid') || b.status === 'otp_sent').length;
        }

        if (results.buses && results.buses.data) {
          count += results.buses.data.filter((b: any) => (b.status === 'pending' && b.payment_status !== 'paid') || b.status === 'otp_sent').length;
        }

        if (results.flights && results.flights.data) {
          count += results.flights.data.filter((b: any) => (b.status === 'pending' && b.payment_status !== 'paid') || b.status === 'otp_sent').length;
        }

        if (results.hotels && results.hotels.data) {
          count += results.hotels.data.filter((b: any) => (b.status === 'pending' && b.payment_status !== 'paid') || b.status === 'otp_sent').length;
        }

        this.pendingPaymentCount = count;
      },
      error: () => {
        // Silent fail
      }
    });
  }

  checkIfHomePage(): void {
    const url = this.router.url;
    this.isHomePage = url === '/' || url.startsWith('/home');

    if (this.isHomePage) {
      const offset = window.pageYOffset || document.documentElement.scrollTop;
      this.isScrolled = offset > 50;
    }
  }

  @HostListener('window:scroll', [])
  onWindowScroll() {

    if (this.isHomePage) {
      const offset = window.pageYOffset || document.documentElement.scrollTop;
      this.isScrolled = offset > 50;
      // console.log("Home", this.isHomePage)
      // console.log(this.isScrolled)
    }

  }

  openChatbot(): void {
    if (!this.isAuthenticated) {
      this.router.navigate(['/login']);
      return;
    }
    this.router.navigate(['/chat-room']);
  }

  toggleDropdown(): void {
    this.showDropdown = !this.showDropdown;
  }

  closeDropdown(): void {
    this.showDropdown = false;
  }

  toggleActivitiesMenu(): void {
    this.showActivitiesMenu = !this.showActivitiesMenu;
  }

  closeActivitiesMenu(): void {
    this.showActivitiesMenu = false;
  }
}

interface Menu {
  label: string;
  url: string;
  queryParams?: Record<string, string>;
}

interface ServiceMenu extends Menu {
  icon: string;
}
