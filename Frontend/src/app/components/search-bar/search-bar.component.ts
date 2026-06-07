import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TourSearchParams } from '../../shared/models/tour.model';

@Component({
  selector: 'app-search-bar',
  imports: [
    CommonModule,
    FormsModule
  ],
  templateUrl: './search-bar.component.html',
  styleUrl: './search-bar.component.scss'
})
export class SearchBarComponent {
  @Input() searchType: 'hotel' | 'tour' = 'hotel';
  @Output() onSearch: EventEmitter<any> = new EventEmitter<any>();

  searchVal: string = '';

  hotelSearchObj = {
    name: '',
    date: '',
    capacity: ''
  };

  tourSearchObj: TourSearchParams = {
    destination: '',
    departure_location: '',
    date_from: '',
    date_to: ''
  };

  queryText: string = '';

  constructor(private router: Router) {}

  openAIChatbot(): void {
    // Navigate to chat room để mở chatbot AI
    this.router.navigate(['/chat-room', 'new']);
  }

  bindSearch() {
    if (this.searchType === 'hotel') {
      this.onSearch.emit(this.hotelSearchObj);
    } else {
      // Chỉ dùng queryText để search, không cần các fields riêng lẻ nữa
      const searchData = {
        queryText: this.queryText
      };
      this.onSearch.emit(searchData);
      this.router.navigate(['/tours'], { 
        queryParams: {
          q: this.queryText
        }
      });
    }
  }

  switchSearchType(type: 'hotel' | 'tour') {
    this.searchType = type;
  }
}
