import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, Subscription, from, of } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, map, catchError, tap } from 'rxjs/operators';
import { TourService } from '../../services/tour.service';
import { Tour, TourPackageSearchRequest } from '../../shared/models/tour.model';

@Component({
  selector: 'app-hero',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './hero.component.html',
  styleUrl: './hero.component.scss'
})
export class HeroComponent implements OnInit, OnDestroy {
  // Search inputs
  searchQuery: string = '';

  // Autocomplete
  searchResults: Tour[] = [];
  isLoading: boolean = false;
  showResults: boolean = false;
  private searchSubject = new Subject<string>();
  private searchSubscription: Subscription | undefined;

  menuItems: Menu[] = [
    {
      label: 'Khách sạn', url: '', path: 'icon/hotel.png',
      isActive: true
    },
    {
      label: 'Vé máy bay', url: '', path: 'icon/air-plane.png',
      isActive: false
    },
    {
      label: 'Vé tàu hỏa', url: '', path: 'icon/train.png',
      isActive: false
    },
    {
      label: 'Vé xe khách & Du lịch', url: '', path: 'icon/train.png',
      isActive: false
    },
    {
      label: 'Đưa đón sân bay', url: '', path: 'icon/car.png',
      isActive: false
    },
    {
      label: 'Thuê xe', url: '', path: 'icon/car.png',
      isActive: false
    },
    {
      label: 'Giải trí và hoạt động', url: '', path: 'icon/car.png',
      isActive: false
    },
    {
      label: 'Khác', url: '', path: 'icon/car.png',
      isActive: false
    },
  ]

  constructor(
    private router: Router,
    private tourService: TourService
  ) { }

  ngOnInit() {
    this.searchSubscription = this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => {
        if (!query || !query.trim()) {
          this.searchResults = [];
          this.showResults = false;
          return of([]);
        }
        
        this.isLoading = true;
        this.showResults = true; // Show dropdown with loader
        
        const request: TourPackageSearchRequest = {
          q: query,
          limit: 5 // Limit autocomplete results
        };

        return from(this.tourService.searchTourPackages(request)).pipe(
          map(res => res.packages),
          catchError(err => {
             console.error('Search error:', err);
             return of([]);
          }),
          tap(() => this.isLoading = false)
        );
      })
    ).subscribe(tours => {
      this.searchResults = tours;
    });
  }

  ngOnDestroy() {
    this.searchSubscription?.unsubscribe();
  }

  onSearchChange() {
    this.searchSubject.next(this.searchQuery);
  }

  onFocus() {
    if (this.searchQuery && this.searchQuery.trim()) {
      this.showResults = true;
      if (this.searchResults.length === 0 && !this.isLoading) {
        this.onSearchChange(); // Trigger search if focused and has text but no results yet
      }
    }
  }

  onBlur() {
    // Delay hiding to allow click event on result
    setTimeout(() => {
      this.showResults = false;
    }, 200);
  }

  selectTour(tour: Tour) {
    this.router.navigate(['/tour-details', tour.package_id]);
    this.showResults = false;
  }

  onSearch() {
    const queryParams: any = {};
    if (this.searchQuery) queryParams.q = this.searchQuery;
    
    this.router.navigate(['/tours'], { queryParams });
  }

  formatPrice(price: number): string {
    if (price === undefined || price === null) return 'Liên hệ';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }
}

interface Menu {
  label: string;
  url: string;
  path: string;
  isActive: boolean;
}
