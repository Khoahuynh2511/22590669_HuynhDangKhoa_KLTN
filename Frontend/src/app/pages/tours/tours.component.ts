import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { TourCardComponent } from '../../components/tour-card/tour-card.component';
import { SearchBarComponent } from '../../components/search-bar/search-bar.component';
import { TourService } from '../../services/tour.service';
import { FavoriteService } from '../../services/favorite.service';
import { AuthStateService } from '../../services/auth-state.service';
import { Tour, TourSearchParams, TourPackageSearchRequest } from '../../shared/models/tour.model';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';

@Component({
  selector: 'app-tours',
  imports: [CommonModule, FormsModule, TourCardComponent, SearchBarComponent, ToastModule],
  providers: [MessageService],
  templateUrl: './tours.component.html',
  styleUrl: './tours.component.scss'
})
export class ToursComponent implements OnInit {
  tours: Tour[] = [];
  filteredTours: Tour[] = [];
  isLoading = false;
  searchParams: TourSearchParams = {};
  queryText: string = '';
  maxPrice: number | undefined;
  duration: number | undefined;
  totalFound: number = 0;
  errorMessage: string | null = null;
  isAuthenticated = false;

  sortBy: 'price_asc' | 'price_desc' | 'popular' = 'popular';

  constructor(
    private tourService: TourService,
    private favoriteService: FavoriteService,
    private authStateService: AuthStateService,
    private route: ActivatedRoute,
    private messageService: MessageService
  ) { }

  async ngOnInit() {
    this.isAuthenticated = this.authStateService.getIsAuthenticated();

    this.authStateService.isAuthenticated$.subscribe(isAuth => {
      this.isAuthenticated = isAuth;
      if (isAuth && this.tours.length > 0) {
        this.loadFavoriteStatuses();
      }
    });

    const snapshotParams = this.route.snapshot.queryParams;
    this.searchParams = snapshotParams as TourSearchParams;
    this.queryText = snapshotParams['q'] || '';
    this.maxPrice = snapshotParams['max_price'] ? Number(snapshotParams['max_price']) : undefined;
    this.duration = snapshotParams['duration'] ? Number(snapshotParams['duration']) : undefined;

    await this.loadTours();

    this.route.queryParams.subscribe(params => {
      this.searchParams = params as TourSearchParams;
      this.queryText = params['q'] || '';
      this.maxPrice = params['max_price'] ? Number(params['max_price']) : undefined;
      this.duration = params['duration'] ? Number(params['duration']) : undefined;
      this.loadTours();
    });
  }

  async loadTours() {
    this.isLoading = true;
    this.errorMessage = null;
    try {
      if (this.queryText || this.maxPrice || this.duration || this.searchParams.destination) {
        const searchRequest: TourPackageSearchRequest = {
          q: this.queryText || undefined,
          max_price: this.maxPrice,
          duration: this.duration,
          destination: this.searchParams.destination,
          limit: 50
        };

        const response = await this.tourService.searchTourPackages(searchRequest);
        this.tours = response.packages || [];
        this.totalFound = response.found || 0;
      } else if (this.searchParams.destination || this.searchParams.departure_location ||
        this.searchParams.price_min || this.searchParams.price_max ||
        this.searchParams.duration_min || this.searchParams.duration_max) {
        const searchRequest: TourPackageSearchRequest = {
          q: undefined,
          max_price: this.searchParams.price_max,
          duration: this.searchParams.duration_min,
          destination: this.searchParams.destination,
          limit: 50
        };

        const response = await this.tourService.searchTourPackages(searchRequest);
        this.tours = response.packages || [];
        this.totalFound = response.found || 0;
      } else {
        const response = await this.tourService.getTourPackages({
          is_active: true,
          limit: 100,
          offset: 0
        });
        this.tours = response.packages || [];
        this.totalFound = response.total || this.tours.length;
        console.log('Loaded all tour packages:', {
          total: response.total,
          packages: this.tours.length,
          sample: this.tours[0]
        });
      }
      this.applyFilters();

      // Load favorite statuses if authenticated
      if (this.isAuthenticated && this.tours.length > 0) {
        this.loadFavoriteStatuses();
      }
    } catch (error: any) {
      console.error('Error loading tours:', error);
      this.errorMessage = error?.message || 'Lỗi khi tải danh sách tour. Vui lòng thử lại sau.';
      this.tours = [];
      this.filteredTours = [];
    } finally {
      this.isLoading = false;
    }
  }

  async loadFavoriteStatuses(): Promise<void> {
    // This logic is now handled globally by FavoriteService
  }

  isFavorite(packageId: string): boolean {
    return false; // Handled internally by TourCard
  }

  isLoadingFavorite(packageId: string): boolean {
    return false; // Handled internally by TourCard
  }

  async onToggleFavorite(packageId: string): Promise<void> {
    // Logic handles in TourCard, but we listen for potential side effects if needed
    console.log('ToursComponent: Favorite toggled for', packageId);
  }

  onSearch(params: any) {
    // Chỉ dùng queryText để search
    this.queryText = params.queryText || params.q || '';
    this.searchParams = {}; // Clear các params riêng lẻ
    this.loadTours();
  }

  changeSortBy(sortBy: 'price_asc' | 'price_desc' | 'popular') {
    this.sortBy = sortBy;
    this.applyFilters();
  }

  applyFilters() {
    let filtered = [...this.tours];

    switch (this.sortBy) {
      case 'price_asc':
        filtered.sort((a, b) => (a.price || 0) - (b.price || 0));
        break;
      case 'price_desc':
        filtered.sort((a, b) => (b.price || 0) - (a.price || 0));
        break;
      case 'popular':
        filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));
        break;
    }

    this.filteredTours = filtered;
  }
}