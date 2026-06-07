import { Component, OnInit } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { HeaderComponent } from './layouts/header/header.component';
import { FooterComponent } from './layouts/footer/footer.component';
import { AuthStateService } from './services/auth-state.service';
import { filter } from 'rxjs/operators';

import { PrimeNG } from 'primeng/config';
import Aura from '@primeng/themes/aura';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent, FooterComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'traveloka-clone';
  isChatPage = false;
  isAdminPage = false;

  constructor(
    private primeng: PrimeNG,
    private authStateService: AuthStateService,
    private router: Router
  ) {
    this.primeng.theme.set({
      preset: Aura,
      options: {
        cssLayer: {
          name: 'primeng',
          order: 'tailwind-base, primeng, tailwind-utilities'
        }
      }
    })
  }

  ngOnInit(): void {
    this.authStateService.checkAuthState();
    this.checkRoute();
    
    // Check payment return URL sau khi thanh toán
    this.checkPaymentReturn();
    
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.checkRoute();
        // Check payment return URL mỗi khi route change
        this.checkPaymentReturn();
      });
  }

  private checkPaymentReturn(): void {
    const returnUrl = sessionStorage.getItem('payment_return_url');
    if (returnUrl && returnUrl.includes('/chat-room/')) {
      // Clear sessionStorage
      sessionStorage.removeItem('payment_return_url');
      // Redirect về chat room
      const currentUrl = this.router.url;
      // Chỉ redirect nếu không đang ở chat room
      if (!currentUrl.includes('/chat-room/')) {
        // Extract path từ full URL
        try {
          const url = new URL(returnUrl);
          this.router.navigateByUrl(url.pathname + url.search);
        } catch {
          // Fallback: extract path manually
          const pathMatch = returnUrl.match(/\/chat-room\/[^?#]+/);
          if (pathMatch) {
            this.router.navigateByUrl(pathMatch[0]);
          }
        }
      }
    }
  }

  private checkRoute(): void {
    this.isChatPage = this.router.url.startsWith('/chat-room/');
    this.isAdminPage = this.router.url.startsWith('/admin');
  }
}
