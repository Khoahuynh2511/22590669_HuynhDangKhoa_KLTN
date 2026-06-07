import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { trigger, state, style, transition, animate } from '@angular/animations';
import { TravelNewsService } from '../../services/travel-news.service';
import { TravelNews } from '../../shared/models/travel-news.model';
import { TravelNewsCardComponent } from '../../components/travel-news-card/travel-news-card.component';
import { AiChatPanelComponent } from '../../components/ai-chat-panel/ai-chat-panel.component';
import { AuthStateService } from '../../services/auth-state.service';
import { take } from 'rxjs/operators';

@Component({
  selector: 'app-travel-news',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TravelNewsCardComponent,
    AiChatPanelComponent
  ],
  templateUrl: './travel-news.component.html',
  styleUrl: './travel-news.component.scss',
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ transform: 'translateX(100%)' }),
        animate('300ms ease-out', style({ transform: 'translateX(0)' }))
      ]),
      transition(':leave', [
        animate('300ms ease-in', style({ transform: 'translateX(100%)' }))
      ])
    ])
  ]
})
export class TravelNewsComponent implements OnInit {
  searchKeywords: string = '';
  selectedSourceType: 'all' | 'news' | 'guide' = 'all';
  currentPage: number = 1;
  pageSize: number = 20;
  totalPages: number = 0;
  totalResults: number = 0;
  searchResults: TravelNews[] = [];
  isSearching: boolean = false;
  hasSearched: boolean = false;
  errorMessage: string | null = null;
  isAIChatOpen: boolean = false;

  constructor(
    private travelNewsService: TravelNewsService,
    private authStateService: AuthStateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Load initial data khi component khởi tạo
    this.loadInitialData();
  }

  onSearch(): void {
    if (!this.searchKeywords.trim()) {
      return;
    }

    this.currentPage = 1;
    this.loadSearchResults();
  }

  onSourceTypeChange(type: 'all' | 'news' | 'guide'): void {
    this.selectedSourceType = type;
    this.currentPage = 1;
    
    // Nếu có keywords thì search, không thì load list
    if (this.searchKeywords.trim()) {
      this.loadSearchResults();
    } else {
      this.loadInitialData();
    }
  }

  onPageChange(page: number): void {
    if (page < 1 || page > this.totalPages) {
      return;
    }
    
    this.currentPage = page;
    
    // Nếu có keywords thì search, không thì load list
    if (this.searchKeywords.trim()) {
      this.loadSearchResults();
    } else {
      this.loadInitialData();
    }
    
    // Scroll to top khi change page
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async loadSearchResults(): Promise<void> {
    this.isSearching = true;
    this.errorMessage = null;
    
    try {
      const sourceType = this.selectedSourceType === 'all' ? undefined : this.selectedSourceType;
      
      const response = await this.travelNewsService.searchTravelNews(
        this.searchKeywords.trim(),
        sourceType,
        this.currentPage,
        this.pageSize
      );
      
      this.searchResults = response.data || [];
      this.totalResults = response.total || 0;
      this.totalPages = response.total_pages || 0;
      this.hasSearched = true;
      
      console.log('Search results loaded:', {
        results: this.searchResults.length,
        total: this.totalResults,
        pages: this.totalPages,
        currentPage: this.currentPage
      });
    } catch (error: any) {
      console.error('Error loading search results:', error);
      this.searchResults = [];
      this.totalResults = 0;
      this.totalPages = 0;
      this.errorMessage = error?.message || 'Lỗi khi tìm kiếm tin tức du lịch.';
    } finally {
      this.isSearching = false;
    }
  }

  async loadInitialData(): Promise<void> {
    this.isSearching = true;
    this.errorMessage = null;
    
    try {
      const sourceType = this.selectedSourceType === 'all' ? undefined : this.selectedSourceType;
      
      const response = await this.travelNewsService.getPaginatedTravelNews(
        sourceType,
        this.currentPage,
        this.pageSize
      );
      
      this.searchResults = response.data || [];
      this.totalResults = response.total || 0;
      this.totalPages = response.total_pages || 0;
      this.hasSearched = false; // Đây là initial load, không phải search
      
      console.log('Initial data loaded:', {
        results: this.searchResults.length,
        total: this.totalResults,
        pages: this.totalPages,
        currentPage: this.currentPage
      });
    } catch (error: any) {
      console.error('Error loading initial data:', error);
      this.searchResults = [];
      this.totalResults = 0;
      this.totalPages = 0;
      this.errorMessage = error?.message || 'Lỗi khi tải danh sách tin tức du lịch.';
    } finally {
      this.isSearching = false;
    }
  }

  clearSearch(): void {
    this.searchKeywords = '';
    this.selectedSourceType = 'all';
    this.currentPage = 1;
    this.hasSearched = false;
    this.errorMessage = null;
    // Load lại initial data sau khi clear search
    this.loadInitialData();
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    
    if (this.totalPages <= maxVisible) {
      // Show all pages if total pages <= maxVisible
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Show pages with ellipsis logic
      if (this.currentPage <= 3) {
        // Show first 3 pages + ... + last page
        for (let i = 1; i <= 3; i++) {
          pages.push(i);
        }
        pages.push(-1); // -1 represents ellipsis
        pages.push(this.totalPages);
      } else if (this.currentPage >= this.totalPages - 2) {
        // Show first page + ... + last 3 pages
        pages.push(1);
        pages.push(-1);
        for (let i = this.totalPages - 2; i <= this.totalPages; i++) {
          pages.push(i);
        }
      } else {
        // Show first page + ... + current-1, current, current+1 + ... + last page
        pages.push(1);
        pages.push(-1);
        for (let i = this.currentPage - 1; i <= this.currentPage + 1; i++) {
          pages.push(i);
        }
        pages.push(-1);
        pages.push(this.totalPages);
      }
    }
    
    return pages;
  }

  toggleAIChat(): void {
    // Check authentication
    this.authStateService.isAuthenticated$.pipe(take(1)).subscribe(isAuth => {
      if (!isAuth) {
        this.router.navigate(['/login']);
        return;
      }
      
      this.isAIChatOpen = !this.isAIChatOpen;
    });
  }

  closeAIChat(): void {
    this.isAIChatOpen = false;
  }
}
