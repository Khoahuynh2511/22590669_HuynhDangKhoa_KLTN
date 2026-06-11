import { Component, EventEmitter, Input, Output, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

export interface HotelSearchData {
  name: string;
  checkIn: string;
  checkOut: string;
  guests: number;
  rooms: number;
}

export interface TourSearchData {
  queryText: string;
}

@Component({
  selector: 'app-search-bar',
  imports: [
    CommonModule,
    FormsModule
  ],
  templateUrl: './search-bar.component.html',
  styleUrl: './search-bar.component.scss'
})
export class SearchBarComponent implements OnChanges {
  @Input() searchType: 'hotel' | 'tour' = 'hotel';
  @Input() showTabs = true;
  @Input() initialQueryText = '';
  @Input() navigateOnSearch = true;
  @Output() onSearch = new EventEmitter<HotelSearchData | TourSearchData>();

  hotelSearchObj: HotelSearchData = {
    name: '',
    checkIn: '',
    checkOut: '',
    guests: 2,
    rooms: 1
  };

  queryText = '';

  constructor(private router: Router) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['initialQueryText'] && this.initialQueryText !== undefined) {
      this.queryText = this.initialQueryText;
    }
  }

  openAIChatbot(): void {
    this.router.navigate(['/chat-room', 'new']);
  }

  bindSearch(): void {
    if (this.searchType === 'hotel') {
      this.onSearch.emit({ ...this.hotelSearchObj });
      return;
    }

    const searchData: TourSearchData = {
      queryText: this.queryText.trim()
    };
    this.onSearch.emit(searchData);

    if (this.navigateOnSearch) {
      this.router.navigate(['/tours'], {
        queryParams: { q: searchData.queryText || null }
      });
    }
  }

  switchSearchType(type: 'hotel' | 'tour'): void {
    this.searchType = type;
  }
}
