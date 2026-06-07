import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-booking-card',
  imports: [CommonModule],
  templateUrl: './booking-card.component.html',
  styleUrl: './booking-card.component.scss'
})
export class BookingCardComponent {
  @Input() tourPackage: any = null;
  @Input() numberOfPeople: number = 1;

  formatDate(dateString: string): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }).format(date);
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }
}
