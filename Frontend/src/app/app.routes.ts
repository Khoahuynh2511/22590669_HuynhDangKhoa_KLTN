import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';
import { HotelComponent } from './pages/hotel/hotel.component';
import { ProducDetailsComponent } from './pages/produc-details/produc-details.component';
import { BookingPagesComponent } from './pages/booking-pages/booking-pages.component';
import { PaymentComponent } from './pages/payment/payment.component';
import { LoginComponent } from './pages/auth/login/login.component';
import { RegisterComponent } from './pages/auth/register/register.component';
import { ForgotPasswordComponent } from './pages/auth/forgot-password/forgot-password.component';
import { GoogleCallbackComponent } from './pages/auth/google-callback/google-callback.component';
import { ToursComponent } from './pages/tours/tours.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { MyBookingsComponent } from './pages/my-bookings/my-bookings.component';
import { MyPaymentsComponent } from './pages/my-payments/my-payments.component';
import { VnpayCallbackComponent } from './pages/payment/vnpay-callback.component';
import { PromotionsComponent } from './pages/promotions/promotions.component';
import { MyFavoritesComponent } from './pages/my-favorites/my-favorites.component';
import { ExploreMapComponent } from './pages/explore-map/explore-map.component';
import { LeaderboardComponent } from './pages/leaderboard/leaderboard.component';
import { authGuard } from './guards/auth.guard';
import { guestGuard } from './guards/guest.guard';
import { FlightsComponent } from './pages/flights/flights.component';
import { TrainsComponent } from './pages/trains/trains.component';
import { CarRentalComponent } from './pages/car-rental/car-rental.component';
import { AirportTransferComponent } from './pages/airport-transfer/airport-transfer.component';
import { ActivitiesComponent } from './pages/activities/activities.component';
import { BusesComponent } from './pages/buses/buses.component';

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
    path: 'flights', component: FlightsComponent
  },
  {
    path: 'trains', component: TrainsComponent
  },
  {
    path: 'car-rental', component: CarRentalComponent
  },
  {
    path: 'airport-transfer', component: AirportTransferComponent
  },
  {
    path: 'activities', component: ActivitiesComponent
  },
  {
    path: 'buses', component: BusesComponent
  },
  {
    path: 'flight-booking/:id',
    loadComponent: () => import('./pages/flights/flight-booking/flight-booking.component').then(m => m.FlightBookingComponent),
    canActivate: [authGuard]
  },
  {
    path: 'train-booking/:id',
    loadComponent: () => import('./pages/trains/train-booking/train-booking.component').then(m => m.TrainBookingComponent),
    canActivate: [authGuard]
  },
  {
    path: 'bus-booking/:id',
    loadComponent: () => import('./pages/buses/bus-booking/bus-booking.component').then(m => m.BusBookingComponent),
    canActivate: [authGuard]
  },
  {
    path: 'hotel/detail/:id',
    loadComponent: () => import('./pages/hotel/hotel-detail/hotel-detail.component').then(m => m.HotelDetailComponent)
  },
  {
    path: 'hotel-booking/:id',
    loadComponent: () => import('./pages/hotel/hotel-booking/hotel-booking.component').then(m => m.HotelBookingComponent),
    canActivate: [authGuard]
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
    path: 'forgot-password', component: ForgotPasswordComponent, canActivate: [guestGuard]
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
    path: 'explore-map', component: ExploreMapComponent, canActivate: [authGuard]
  },
  {
    path: 'leaderboard', component: LeaderboardComponent, canActivate: [authGuard]
  },
  {
    path: 'itinerary/:shareId',
    loadComponent: () => import('./pages/shared-itinerary/shared-itinerary.component').then(m => m.SharedItineraryComponent)
  },
  {
    path: 'festivals',
    loadComponent: () => import('./pages/festivals/festivals.component').then(m => m.FestivalsComponent)
  },
  {
    path: 'festival-details/:name',
    loadComponent: () => import('./pages/festival-details/festival-details.component').then(m => m.FestivalDetailsComponent)
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
