import { Component, OnInit, AfterViewInit, OnDestroy, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { HeroComponent } from '../../components/hero/hero.component';
import { CouponListComponent } from '../../components/coupon-list/coupon-list.component';
import { TourCardComponent } from '../../components/tour-card/tour-card.component';
import { TravelNewsCardComponent } from '../../components/travel-news-card/travel-news-card.component';
import { ReviewCardComponent } from '../../components/review-card/review-card.component';
import { TourService } from '../../services/tour.service';
import { TravelNewsService } from '../../services/travel-news.service';
import { ReviewService, Review } from '../../services/review.service';
import { Tour } from '../../shared/models/tour.model';
import { TravelNews } from '../../shared/models/travel-news.model';
import { AuthStateService } from '../../services/auth-state.service';
import { AuthService } from '../../services/auth.service';
import { take } from 'rxjs/operators';

@Component({
  selector: 'app-home',
  imports: [
    CommonModule,
    RouterLink,
    HeroComponent,
    CouponListComponent,
    TourCardComponent,
    TravelNewsCardComponent,
    ReviewCardComponent
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit, AfterViewInit, OnDestroy {
  featuredTours: Tour[] = [];
  recommendedTours: Tour[] = [];
  latestTours: Tour[] = [];
  travelNews: TravelNews[] = [];
  approvedReviews: Review[] = [];
  isLoadingFeaturedTours = false;
  isLoadingTours = false;
  isLoadingLatestTours = false;
  isLoadingTravelNews = false;
  isLoadingReviews = false;
  errorMessageFeatured: string | null = null;
  errorMessageRecommended: string | null = null;
  errorMessageLatest: string | null = null;
  errorMessageTravelNews: string | null = null;

  private observer?: IntersectionObserver;

  constructor(
    private tourService: TourService,
    private travelNewsService: TravelNewsService,
    private reviewService: ReviewService,
    private authStateService: AuthStateService,
    private authService: AuthService,
    private route: ActivatedRoute,
    private router: Router,
    private elementRef: ElementRef
  ) { }

  async ngOnInit() {
    // Check for Google OAuth token in query params - only process once
    this.route.queryParams.pipe(take(1)).subscribe(params => {
      const token = params['token'];
      if (token) {
        this.handleGoogleAuthToken(token);
      }
    });

    await Promise.all([
      this.loadFeaturedTours(),
      this.loadRecommendedTours(),
      this.loadLatestTours(),
      this.loadTravelNews(),
      this.loadApprovedReviews()
    ]);
  }

  private handleGoogleAuthToken(token: string): void {
    console.log('Processing Google auth token...');

    // Store token first
    localStorage.setItem('access_token', token);

    // Remove token from URL immediately (before processing)
    this.router.navigate(['/home'], {
      replaceUrl: true,
      queryParams: {}
    });

    // Verify token and login
    this.authService.verifyToken(token).subscribe({
      next: (response) => {
        console.log('Token verification response:', response);

        if (response.EC === 0 && response.data) {
          // Create user object from token data
          const user = {
            full_name: response.data.full_name || response.data.email || '',
            email: response.data.email || '',
            user_id: response.data.user_id || response.data.email || '',
            role: response.data.role || 'user'
          };

          console.log('User object created:', user);

          // Store user in localStorage
          localStorage.setItem('user', JSON.stringify(user));

          // Update auth state service to trigger UI update
          this.authStateService.login(token, user);

          console.log('User logged in successfully:', user.full_name);
        } else {
          console.error('Token verification failed:', response.EM);
          localStorage.removeItem('access_token');
        }
      },
      error: (error) => {
        console.error('Token verification error:', error);
        localStorage.removeItem('access_token');
      }
    });
  }

  ngAfterViewInit() {
    this.setupScrollAnimations();
  }

  ngOnDestroy() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  private setupScrollAnimations() {
    const sections = this.elementRef.nativeElement.querySelectorAll('.section-animate');

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    sections.forEach((section: Element) => {
      this.observer?.observe(section);
    });
  }

  getDisplayedFeaturedTours(): Tour[] {
    return this.featuredTours.slice(0, 12);
  }

  getDisplayedRecommendedTours(): Tour[] {
    return this.recommendedTours.slice(0, 12);
  }

  getDisplayedLatestTours(): Tour[] {
    return this.latestTours.slice(0, 8);
  }

  async loadFeaturedTours() {
    this.isLoadingFeaturedTours = true;
    this.errorMessageFeatured = null;
    try {
      const response = await this.tourService.getTourPackages({
        is_active: true,
        limit: 50
      });

      if (!response || !response.packages || !Array.isArray(response.packages)) {
        console.warn('Invalid response format:', response);
        this.featuredTours = [];
        return;
      }

      if (response.packages.length === 0) {
        this.featuredTours = [];
        return;
      }

      const featuredTours = response.packages
        .filter(tour => tour.rating && tour.rating >= 4.0)
        .sort((a, b) => {
          const ratingA = a.rating || 0;
          const ratingB = b.rating || 0;
          const reviewsA = a.reviews || 0;
          const reviewsB = b.reviews || 0;

          if (ratingB !== ratingA) {
            return ratingB - ratingA;
          }

          return reviewsB - reviewsA;
        })
        .slice(0, 12);

      this.featuredTours = featuredTours.length > 0
        ? featuredTours
        : response.packages.slice(0, 12);
    } catch (error: any) {
      console.error('Error loading featured tours:', error);
      this.featuredTours = [];
      this.errorMessageFeatured = error?.message || 'Lỗi khi tải tour nổi bật.';
    } finally {
      this.isLoadingFeaturedTours = false;
    }
  }

  async loadRecommendedTours() {
    this.isLoadingTours = true;
    this.errorMessageRecommended = null;
    try {
      const isAuthenticated = this.authStateService.getIsAuthenticated();
      const currentUser = this.authStateService.getCurrentUser();
      const userId = currentUser?.user_id || currentUser?.id || 'anonymous';

      console.log('Loading recommended tours:', { isAuthenticated, userId, currentUser });

      try {
        const response = await this.tourService.recommendTourPackages({
          user_id: userId,
          k: 10
        });

        console.log('Recommended tours API response:', response);

        if (response && response.packages && Array.isArray(response.packages) && response.packages.length > 0) {
          this.recommendedTours = response.packages;
          console.log('Recommended tours loaded:', this.recommendedTours.length);
          return;
        }
      } catch (error: any) {
        console.warn('Recommendation API failed, falling back to random tours:', error);
        if (error.status) {
          console.warn('Error status:', error.status);
          console.warn('Error details:', error.message);
        }
      }

      const response = await this.tourService.getTourPackages({
        is_active: true,
        limit: 50
      });

      if (!response || !response.packages || !Array.isArray(response.packages)) {
        this.recommendedTours = [];
        this.errorMessageRecommended = 'Định dạng dữ liệu không hợp lệ.';
        return;
      }

      if (response.packages.length === 0) {
        this.recommendedTours = [];
        return;
      }

      const shuffledTours = this.shuffleArray([...response.packages]);
      this.recommendedTours = shuffledTours.slice(0, 12);
      console.log('Fallback recommended tours loaded:', this.recommendedTours.length);
    } catch (error: any) {
      console.error('Error loading recommended tours:', error);
      this.recommendedTours = [];
      this.errorMessageRecommended = error?.message || 'Lỗi khi tải tour đề xuất.';
    } finally {
      this.isLoadingTours = false;
    }
  }

  private shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  async loadLatestTours() {
    this.isLoadingLatestTours = true;
    this.errorMessageLatest = null;
    try {
      const response = await this.tourService.getTourPackages({
        is_active: true,
        limit: 50
      });

      if (!response || !response.packages || !Array.isArray(response.packages)) {
        this.latestTours = [];
        this.errorMessageLatest = 'Định dạng dữ liệu không hợp lệ.';
        return;
      }

      const toursWithDate = response.packages.filter(tour => tour.created_at);

      if (toursWithDate.length === 0) {
        this.latestTours = response.packages.slice(0, 8);
        return;
      }

      this.latestTours = toursWithDate
        .sort((a, b) => {
          const dateA = new Date(a.created_at!).getTime();
          const dateB = new Date(b.created_at!).getTime();
          return dateB - dateA;
        })
        .slice(0, 8);
    } catch (error: any) {
      console.error('Error loading latest tours:', error);
      this.latestTours = [];
      this.errorMessageLatest = error?.message || 'Lỗi khi tải tour mới nhất.';
    } finally {
      this.isLoadingLatestTours = false;
    }
  }

  async loadTravelNews() {
    this.isLoadingTravelNews = true;
    this.errorMessageTravelNews = null;
    try {
      const response = await this.travelNewsService.getTravelNews(6);

      if (!response || !response.data || !Array.isArray(response.data)) {
        console.warn('Invalid travel news response format:', response);
        this.travelNews = [];
        return;
      }

      if (response.data.length === 0) {
        this.travelNews = [];
        return;
      }

      this.travelNews = response.data;
      console.log('Travel news loaded:', this.travelNews.length);
    } catch (error: any) {
      console.error('Error loading travel news:', error);
      this.travelNews = [];
      this.errorMessageTravelNews = error?.message || 'Lỗi khi tải tin tức du lịch.';
    } finally {
      this.isLoadingTravelNews = false;
    }
  }

  async loadApprovedReviews() {
    this.isLoadingReviews = true;
    try {
      this.reviewService.getReviews({ is_approved: true, limit: 5 }).subscribe({
        next: (response) => {
          if (response.EC === 0 && response.data) {
            this.approvedReviews = response.data;
            console.log('Approved reviews loaded:', this.approvedReviews.length);
          } else {
            this.approvedReviews = [];
          }
          this.isLoadingReviews = false;
        },
        error: (error) => {
          console.error('Error loading reviews:', error);
          this.approvedReviews = [];
          this.isLoadingReviews = false;
        }
      });
    } catch (error) {
      console.error('Error loading reviews:', error);
      this.approvedReviews = [];
      this.isLoadingReviews = false;
    }
  }
}