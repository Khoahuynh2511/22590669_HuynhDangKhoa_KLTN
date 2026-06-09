import { Component, OnInit } from '@angular/core';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card.component';
import { AccordionFilterComponent, FilterOptions } from '../../components/accordion-filter/accordion-filter.component';
import { SearchBarComponent } from '../../components/search-bar/search-bar.component';
import { HotelService } from '../../services/hotel.service';
import { StateHotel } from '../../shared/models/hotelState.model';

@Component({
  selector: 'app-hotel',
  imports: [
    HotelCardComponent,
    AccordionFilterComponent,
    SearchBarComponent
  ],
  templateUrl: './hotel.component.html',
  styleUrl: './hotel.component.scss'
})
export class HotelComponent implements OnInit {

  hotels: StateHotel[] = [];
  allHotels: StateHotel[] = [];
  filteredHotels: StateHotel[] = [];
  isLoading = true;

  constructor(private hotelService: HotelService) { }

  ngOnInit(): void {
    this.hotelService.loadHotels();
    this.hotelService.hotelState.subscribe(res => {
      this.hotels = res;
      this.allHotels = [...res];
      this.filteredHotels = [...res];
      this.isLoading = false;
    });
  }

  getSearchVal(event: any) {
    if (event) {
      const searchTerm = event.name || event.queryText || '';
      if (searchTerm.trim()) {
        this.isLoading = true;
        this.hotelService.loadHotels(undefined, searchTerm);
      }
    }
  }

  onFilterChange(filters: FilterOptions): void {
    this.filteredHotels = this.allHotels.filter(hotel => {
      // Filter by rating
      if (filters.minRating !== undefined && hotel.review_score !== undefined) {
        if (hotel.review_score < filters.minRating) {
          return false;
        }
      }

      // Filter by price range
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

      // Filter by hotel types
      if (filters.hotelTypes && filters.hotelTypes.length > 0) {
        const hotelName = (hotel.hotel_name || '').toLowerCase();
        const hasMatch = filters.hotelTypes.some(type => {
          switch (type) {
            case 'hotel': return hotelName.includes('khách sạn') || hotelName.includes('hotel');
            case 'villa': return hotelName.includes('biệt thự') || hotelName.includes('villa');
            case 'resort': return hotelName.includes('nghỉ dưỡng') || hotelName.includes('resort') || hotelName.includes('khu nghỉ');
            case 'impressive': return hotel.review_score >= 9;
            default: return true;
          }
        });
        if (!hasMatch) return false;
      }

      return true;
    });

    this.hotels = this.filteredHotels;
  }

  resetAllFilters(): void {
    this.hotelService.loadHotels();
  }

}
