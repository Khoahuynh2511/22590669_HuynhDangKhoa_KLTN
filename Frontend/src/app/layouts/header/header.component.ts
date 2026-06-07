import { CommonModule } from '@angular/common';
import { Component, HostListener, OnInit, OnDestroy } from '@angular/core';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { AuthStateService } from '../../services/auth-state.service';
import { ChatbotService } from '../../services/chatbot.service';
import { NotificationBellComponent } from '../../components/notification-bell/notification-bell.component';
import { Subscription } from 'rxjs';
import { ClickOutsideDirective } from '../../directives/click-outside.directive';

@Component({
  selector: 'app-header',
  imports: [RouterLink, CommonModule, ClickOutsideDirective, NotificationBellComponent],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent implements OnInit, OnDestroy {
  isScrolled = false;
  isHomePage = false;
  isAuthenticated = false;
  currentUser: any = null;
  showDropdown = false;
  private chatbotSubscription?: Subscription;


  topMenuPublic: Menu[] = [
    { label: 'Trang chủ', url: '/home' },
    { label: 'Tour du lịch', url: '/tours' },
    { label: 'Tin tức & Cẩm nang', url: '/travel-news' },
    { label: 'Đánh giá', url: '/reviews' },
  ]

  get topMenu(): Menu[] {
    if (this.isAuthenticated) {
      return [
        ...this.topMenuPublic,
        { label: 'Đơn hàng', url: '/my-bookings' }
      ];
    }
    return this.topMenuPublic;
  }

  constructor(
    private router: Router,
    private authStateService: AuthStateService,
    private chatbotService: ChatbotService
  ) { }

  ngOnInit(): void {
    this.checkIfHomePage();
    this.checkAuthState();

    this.router.events.subscribe((ev) => {
      if (ev instanceof NavigationEnd) {
        this.checkIfHomePage();
      }
    });

    this.authStateService.isAuthenticated$.subscribe(isAuth => {
      this.isAuthenticated = isAuth;
    });

    this.authStateService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });

    this.chatbotSubscription = this.chatbotService.openChatbot$.subscribe(() => {
      this.openChatbot();
    });
  }

  ngOnDestroy() {
    if (this.chatbotSubscription) {
      this.chatbotSubscription.unsubscribe();
    }
  }

  checkAuthState(): void {
    this.isAuthenticated = this.authStateService.getIsAuthenticated();
    this.currentUser = this.authStateService.getCurrentUser();
  }

  onLogout(): void {
    this.authStateService.logout();
    this.router.navigate(['/home']);
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
}

interface Menu {
  label: string;
  url: string;
}
