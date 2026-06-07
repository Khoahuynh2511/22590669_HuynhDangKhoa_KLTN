import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('../../layouts/admin-layout/admin-layout.component').then(m => m.AdminLayoutComponent),
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'tours',
        loadComponent: () => import('./tours/tour-list.component').then(m => m.TourListComponent)
      },
      {
        path: 'bookings',
        loadComponent: () => import('./bookings/booking-list.component').then(m => m.BookingListComponent)
      },
      {
        path: 'payments',
        loadComponent: () => import('./payments/payment-management.component').then(m => m.PaymentManagementComponent)
      },
      {
        path: 'customers',
        loadComponent: () => import('./customers/customer-list.component').then(m => m.CustomerListComponent)
      },
      {
        path: 'promotions',
        loadComponent: () => import('./promotions/promotion-list.component').then(m => m.PromotionListComponent)
      },
      {
        path: 'reviews',
        loadComponent: () => import('./reviews/review-list.component').then(m => m.ReviewListComponent)
      },
      {
        path: 'reports',
        loadComponent: () => import('./reports/reports.component').then(m => m.ReportsComponent)
      },
      {
        path: 'cancellations',
        loadComponent: () => import('./cancellations/cancellation-management.component').then(m => m.CancellationManagementComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('./admin-profile/admin-profile.component').then(m => m.AdminProfileComponent)
      },
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      }
    ]
  }
];
