import { Component, ViewEncapsulation, Output, EventEmitter } from '@angular/core';
import { AccordionModule } from 'primeng/accordion';
import { CheckboxModule } from 'primeng/checkbox';
import { ButtonModule } from 'primeng/button';
import { FormsModule } from '@angular/forms';

export interface FilterOptions {
  minRating?: number;
  minPrice?: number;
  maxPrice?: number;
  hotelTypes?: string[];
}

@Component({
  selector: 'app-accordion-filter',
  imports: [
    AccordionModule,
    CheckboxModule,
    ButtonModule,
    FormsModule
  ],
  templateUrl: './accordion-filter.component.html',
  styleUrl: './accordion-filter.component.scss',
  encapsulation: ViewEncapsulation.None
})
export class AccordionFilterComponent {
  @Output() filterChange = new EventEmitter<FilterOptions>();

  checkboxs: any[] = [
    { label: 'Ấn tượng', value: 'impressive' },
    { label: 'Khách sạn', value: 'hotel' },
    { label: 'Biệt thự', value: 'villa' },
    { label: 'Khu nghỉ dưỡng', value: 'resort' },
  ];

  hotelTypes = [
    { label: 'Khách sạn', value: 'hotel', checked: false },
    { label: 'Biệt thự', value: 'villa', checked: false },
    { label: 'Khu nghỉ dưỡng', value: 'resort', checked: false },
    { label: 'Ấn tượng', value: 'impressive', checked: false }
  ];

  ratingOptions = [
    { label: '9 trở lên', value: 9, checked: false },
    { label: '8 trở lên', value: 8, checked: false },
    { label: '7 trở lên', value: 7, checked: false },
    { label: '6 trở lên', value: 6, checked: false }
  ];

  priceRange = {
    min: 0,
    max: 10000000
  };

  selectedMinRating: number | null = null;
  selectedMinPrice: number | null = null;
  selectedMaxPrice: number | null = null;

  toggleType(type: any): void {
    type.checked = !type.checked;
    this.emitFilters();
  }

  setMinRating(rating: number): void {
    // Uncheck other ratings
    this.ratingOptions.forEach(r => {
      r.checked = (r.value === rating);
    });
    this.selectedMinRating = rating;
    this.emitFilters();
  }

  onPriceChange(): void {
    this.selectedMinPrice = this.priceRange.min > 0 ? this.priceRange.min : null;
    this.selectedMaxPrice = this.priceRange.max < 10000000 ? this.priceRange.max : null;
    this.emitFilters();
  }

  emitFilters(): void {
    const filters: FilterOptions = {};

    if (this.selectedMinRating !== null) {
      filters.minRating = this.selectedMinRating;
    }

    if (this.selectedMinPrice !== null) {
      filters.minPrice = this.selectedMinPrice;
    }

    if (this.selectedMaxPrice !== null) {
      filters.maxPrice = this.selectedMaxPrice;
    }

    const checkedTypes = this.hotelTypes.filter(t => t.checked).map(t => t.value);
    if (checkedTypes.length > 0) {
      filters.hotelTypes = checkedTypes;
    }

    this.filterChange.emit(filters);
  }

  resetFilters(): void {
    this.hotelTypes.forEach(t => t.checked = false);
    this.ratingOptions.forEach(r => r.checked = false);
    this.priceRange = { min: 0, max: 10000000 };
    this.selectedMinRating = null;
    this.selectedMinPrice = null;
    this.selectedMaxPrice = null;
    this.emitFilters();
  }
}
