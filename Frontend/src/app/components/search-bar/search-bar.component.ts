import { Component, EventEmitter, Input, Output, OnChanges, SimpleChanges, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

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
export class SearchBarComponent implements OnChanges, OnInit {
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

  constructor(private router: Router, private route: ActivatedRoute) {}

  get minDate(): string {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  get minCheckOutDate(): string {
    return this.hotelSearchObj.checkIn || this.minDate;
  }

  onCheckInChange(): void {
    if (this.hotelSearchObj.checkIn && this.hotelSearchObj.checkOut) {
      if (new Date(this.hotelSearchObj.checkOut) < new Date(this.hotelSearchObj.checkIn)) {
        this.hotelSearchObj.checkOut = this.hotelSearchObj.checkIn;
      }
    }
  }

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (this.searchType === 'hotel') {
        if (params['check_in']) this.hotelSearchObj.checkIn = params['check_in'];
        if (params['check_out']) this.hotelSearchObj.checkOut = params['check_out'];
        if (params['rooms']) this.hotelSearchObj.rooms = parseInt(params['rooms']) || 1;
        if (params['guests']) this.hotelSearchObj.guests = parseInt(params['guests']) || 2;
        if (params['q']) this.hotelSearchObj.name = params['q'];
      } else {
        if (params['q']) this.queryText = params['q'];
      }
    });
  }

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
