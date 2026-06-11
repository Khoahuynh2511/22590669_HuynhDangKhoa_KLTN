import { Component, OnInit } from '@angular/core';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card.component';
import { AccordionFilterComponent, FilterOptions } from '../../components/accordion-filter/accordion-filter.component';
import { SearchBarComponent, HotelSearchData } from '../../components/search-bar/search-bar.component';
import { PaginationComponent } from '../../components/pagination/pagination.component';
import { HotelService } from '../../services/hotel.service';
import { StateHotel } from '../../shared/models/hotelState.model';
import { paginateSlice } from '../../shared/utils/pagination.util';

@Component({
  selector: 'app-hotel',
  imports: [
    HotelCardComponent,
    AccordionFilterComponent,
    SearchBarComponent,
    PaginationComponent
  ],
  templateUrl: './hotel.component.html',
  styleUrl: './hotel.component.scss'
})
export class HotelComponent implements OnInit {

  hotels: StateHotel[] = [];
  allHotels: StateHotel[] = [];
  filteredHotels: StateHotel[] = [];
  paginatedHotels: StateHotel[] = [];
  isLoading = true;
  currentPage = 1;
  pageSize = 6;
  totalFiltered = 0;
  activeFilters: FilterOptions | null = null;
  currentSearchTerm = '';

  constructor(private hotelService: HotelService) { }

  ngOnInit(): void {
    this.loadHotels();
    this.hotelService.hotelState.subscribe(res => {
      this.allHotels = [...res];
      this.applyFiltersAndPagination();
      this.isLoading = false;
    });
  }

  loadHotels(search?: string): void {
    this.isLoading = true;
    this.currentSearchTerm = search?.trim() || '';
    this.hotelService.loadHotels(undefined, this.currentSearchTerm || undefined);
  }

  getSearchVal(event: HotelSearchData | unknown): void {
    const searchEvent = event as HotelSearchData;
    this.currentPage = 1;
    const searchTerm = searchEvent?.name?.trim() || '';
    this.loadHotels(searchTerm);
  }

  onFilterChange(filters: FilterOptions): void {
    this.activeFilters = filters;
    this.currentPage = 1;
    this.applyFiltersAndPagination();
  }

  onPageChange(page: number): void {
    this.currentPage = page;
    this.applyFiltersAndPagination();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  resetAllFilters(): void {
    this.currentPage = 1;
    this.currentSearchTerm = '';
    this.activeFilters = null;
    this.loadHotels();
  }

  private applyFiltersAndPagination(): void {
    this.filteredHotels = this.filterHotels(this.allHotels, this.activeFilters);
    this.totalFiltered = this.filteredHotels.length;
    this.paginatedHotels = paginateSlice(this.filteredHotels, this.currentPage, this.pageSize);
    this.hotels = this.paginatedHotels;
  }

  private filterHotels(hotels: StateHotel[], filters: FilterOptions | null): StateHotel[] {
    if (!filters) {
      return [...hotels];
    }

    return hotels.filter(hotel => {
      if (filters.minRating !== undefined && hotel.review_score !== undefined) {
        if (hotel.review_score < filters.minRating) {
          return false;
        }
      }

      if (filters.minPrice !== undefined && hotel.price !== undefined) {
        if (hotel.price < filters.minPrice) {
          return false;
        }
      }

      if (filters.maxPrice !== undefined && hotel.price !== undefined) {
        if (hotel.price > filters.maxPrice) {
          return false;
        }
      }

      if (filters.hotelTypes && filters.hotelTypes.length > 0) {
        const hotelName = (hotel.hotel_name || '').toLowerCase();
        const hasMatch = filters.hotelTypes.some(type => {
          switch (type) {
            case 'hotel': return hotelName.includes('khách sạn') || hotelName.includes('hotel');
            case 'villa': return hotelName.includes('biệt thự') || hotelName.includes('villa');
            case 'resort': return hotelName.includes('nghỉ dưỡng') || hotelName.includes('resort') || hotelName.includes('khu nghỉ');
            case 'impressive': return (hotel.review_score ?? 0) >= 9;
            default: return true;
          }
        });
        if (!hasMatch) {
          return false;
        }
      }

      return true;
    });
  }
}
