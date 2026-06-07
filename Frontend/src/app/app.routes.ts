import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';
import { HotelComponent } from './pages/hotel/hotel.component';
import { ProducDetailsComponent } from './pages/produc-details/produc-details.component';
import { BookingPagesComponent } from './pages/booking-pages/booking-pages.component';
import { PaymentComponent } from './pages/payment/payment.component';
import { LoginComponent } from './pages/auth/login/login.component';
import { RegisterComponent } from './pages/auth/register/register.component';
import { GoogleCallbackComponent } from './pages/auth/google-callback/google-callback.component';
import { ToursComponent } from './pages/tours/tours.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { MyBookingsComponent } from './pages/my-bookings/my-bookings.component';
import { MyPaymentsComponent } from './pages/my-payments/my-payments.component';
import { VnpayCallbackComponent } from './pages/payment/vnpay-callback.component';
import { PromotionsComponent } from './pages/promotions/promotions.component';
import { MyFavoritesComponent } from './pages/my-favorites/my-favorites.component';
import { authGuard } from './guards/auth.guard';
import { guestGuard } from './guards/guest.guard';

export const routes: Routes = [
  {
    path: '', redirectTo: '/home', pathMatch: 'full'
  },
  {
    path: 'admin',
    canActivate: [authGuard],
    loadChildren: () => import('./pages/admin/admin.routes').then(m => m.ADMIN_ROUTES)
  },
  {
    path: 'home', component: HomeComponent
  },
  {
    path: 'hotel', component: HotelComponent
  },
  {
    path: 'hotel/detail', component: ProducDetailsComponent
  },
  {
    path: 'tours', component: ToursComponent
  },
  {
    path: 'tour-details/:id', component: ProducDetailsComponent
  },
  {
    path: 'booking/:id', component: BookingPagesComponent, canActivate: [authGuard]
  },
  {
    path: 'payment', component: PaymentComponent, canActivate: [authGuard]
  },
  {
    path: 'login', component: LoginComponent, canActivate: [guestGuard]
  },
  {
    path: 'register', component: RegisterComponent, canActivate: [guestGuard]
  },
  {
    path: 'auth/google/callback', component: GoogleCallbackComponent
  },
  {
    path: 'profile', component: ProfileComponent, canActivate: [authGuard]
  },
  {
    path: 'my-bookings', component: MyBookingsComponent, canActivate: [authGuard]
  },
  {
    path: 'my-payments', component: MyPaymentsComponent, canActivate: [authGuard]
  },
  {
    path: 'my-favorites', component: MyFavoritesComponent, canActivate: [authGuard]
  },
  {
    path: 'chat-room',
    canActivate: [authGuard],
    loadComponent: () => import('./components/ai-chatbot/ai-chatbot.component').then(m => m.AiChatbotComponent)
  },
  {
    path: 'chat-room/:roomId',
    canActivate: [authGuard],
    loadComponent: () => import('./components/ai-chatbot/ai-chatbot.component').then(m => m.AiChatbotComponent)
  },
  {
    path: 'payment/vnpay/callback', component: VnpayCallbackComponent
  },
  {
    path: 'payment/success', component: VnpayCallbackComponent
  },
  {
    path: 'payment/failed', component: VnpayCallbackComponent
  },
  {
    path: 'promotions', component: PromotionsComponent
  },
  {
    path: 'travel-news',
    loadComponent: () => import('./pages/travel-news/travel-news.component').then(m => m.TravelNewsComponent)
  },
  {
    path: 'reviews',
    loadComponent: () => import('./pages/reviews/reviews.component').then(m => m.ReviewsComponent),
    canActivate: [authGuard]
  },
];
