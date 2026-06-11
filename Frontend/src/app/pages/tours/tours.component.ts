import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TourCardComponent } from '../../components/tour-card/tour-card.component';
import { SearchBarComponent, TourSearchData } from '../../components/search-bar/search-bar.component';
import { PaginationComponent } from '../../components/pagination/pagination.component';
import { TourService } from '../../services/tour.service';
import { AuthStateService } from '../../services/auth-state.service';
import { Tour, TourSearchParams, TourPackageSearchRequest } from '../../shared/models/tour.model';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { paginateSlice } from '../../shared/utils/pagination.util';

@Component({
  selector: 'app-tours',
  imports: [CommonModule, FormsModule, TourCardComponent, SearchBarComponent, PaginationComponent, ToastModule],
  providers: [MessageService],
  templateUrl: './tours.component.html',
  styleUrl: './tours.component.scss'
})
export class ToursComponent implements OnInit {
  tours: Tour[] = [];
  filteredTours: Tour[] = [];
  paginatedTours: Tour[] = [];
  isLoading = false;
  searchParams: TourSearchParams = {};
  queryText = '';
  maxPrice: number | undefined;
  duration: number | undefined;
  totalFound = 0;
  errorMessage: string | null = null;
  isAuthenticated = false;
  isSearchMode = false;

  currentPage = 1;
  pageSize = 12;

  sortBy: 'price_asc' | 'price_desc' | 'popular' = 'popular';

  constructor(
    private tourService: TourService,
    private authStateService: AuthStateService,
    private route: ActivatedRoute,
    private router: Router,
    private messageService: MessageService
  ) { }

  async ngOnInit() {
    this.isAuthenticated = this.authStateService.getIsAuthenticated();

    this.authStateService.isAuthenticated$.subscribe(isAuth => {
      this.isAuthenticated = isAuth;
    });

    const snapshotParams = this.route.snapshot.queryParams;
    this.applyRouteParams(snapshotParams);
    await this.loadTours();

    this.route.queryParams.subscribe(params => {
      this.applyRouteParams(params);
      this.loadTours();
    });
  }

  private applyRouteParams(params: Record<string, any>): void {
    this.searchParams = {
      destination: params['destination'] || undefined,
      departure_location: params['departure_location'] || undefined,
      price_min: params['price_min'] ? Number(params['price_min']) : undefined,
      price_max: params['price_max'] ? Number(params['price_max']) : undefined,
      duration_min: params['duration_min'] ? Number(params['duration_min']) : undefined,
      duration_max: params['duration_max'] ? Number(params['duration_max']) : undefined,
      category: params['category'] || undefined,
    };
    this.queryText = params['q'] || '';
    this.maxPrice = params['max_price'] ? Number(params['max_price']) : undefined;
    this.duration = params['duration'] ? Number(params['duration']) : undefined;
    this.currentPage = params['page'] ? Number(params['page']) : 1;
  }

  async loadTours() {
    this.isLoading = true;
    this.errorMessage = null;

    try {
      const hasSearchCriteria = Boolean(
        this.queryText ||
        this.maxPrice ||
        this.duration ||
        this.searchParams.destination ||
        this.searchParams.departure_location ||
        this.searchParams.price_min ||
        this.searchParams.price_max ||
        this.searchParams.duration_min ||
        this.searchParams.duration_max
      );

      this.isSearchMode = hasSearchCriteria;

      if (hasSearchCriteria) {
        const searchQuery =
          this.queryText?.trim() ||
          this.searchParams.destination?.trim() ||
          'tour du lich';

        const searchRequest: TourPackageSearchRequest = {
          q: searchQuery,
          max_price: this.maxPrice ?? this.searchParams.price_max,
          duration: this.duration ?? this.searchParams.duration_min,
          destination: this.searchParams.destination,
          limit: 50
        };

        const response = await this.tourService.searchTourPackages(searchRequest);
        this.tours = response.packages || [];
        this.totalFound = response.found || this.tours.length;
      } else {
        const offset = (this.currentPage - 1) * this.pageSize;
        const response = await this.tourService.getTourPackages({
          is_active: true,
          limit: this.pageSize,
          offset
        });
        this.tours = response.packages || [];
        this.totalFound = response.total || this.tours.length;
      }

      this.applyFilters();
    } catch (error: any) {
      console.error('Error loading tours:', error);
      this.errorMessage = error?.message || 'Lỗi khi tải danh sách tour. Vui lòng thử lại sau.';
      this.tours = [];
      this.filteredTours = [];
      this.paginatedTours = [];
    } finally {
      this.isLoading = false;
    }
  }

  onSearch(params: TourSearchData | unknown) {
    const searchParams = params as TourSearchData;
    this.queryText = searchParams.queryText || '';
    this.searchParams = {};
    this.currentPage = 1;
    this.router.navigate(['/tours'], {
      queryParams: {
        q: this.queryText || null,
        page: null
      }
    });
  }

  changeSortBy(sortBy: 'price_asc' | 'price_desc' | 'popular') {
    this.sortBy = sortBy;
    this.currentPage = 1;
    this.applyFilters();
  }

  onPageChange(page: number): void {
    this.currentPage = page;

    if (this.isSearchMode) {
      this.applyFilters();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    this.router.navigate(['/tours'], {
      queryParams: {
        page: page > 1 ? page : null
      },
      queryParamsHandling: 'merge'
    });
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

    if (this.isSearchMode) {
      this.paginatedTours = paginateSlice(this.filteredTours, this.currentPage, this.pageSize);
    } else {
      this.paginatedTours = this.filteredTours;
    }
  }

  get displayTotal(): number {
    return this.isSearchMode ? this.filteredTours.length : this.totalFound;
  }
}
