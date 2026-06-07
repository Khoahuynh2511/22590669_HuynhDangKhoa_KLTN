import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { TourItineraryDay } from '../../shared/models/tour.model';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-tour-day-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tour-day-detail.component.html',
  styleUrl: './tour-day-detail.component.scss',
  animations: [
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate('0.5s ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
export class TourDayDetailComponent {
  @Input() dayData: TourItineraryDay | null = null;
  @Input() dayNumber: number = 1;

  hasScheduleContent(): boolean {
    if (!this.dayData) return false;
    return !!(
      this.dayData.morning ||
      this.dayData.afternoon ||
      this.dayData.evening ||
      this.dayData.late_afternoon
    );
  }

  getScheduleSections(): Array<{time: string, content: string, icon: string}> {
    if (!this.dayData) return [];

    const sections: Array<{time: string, content: string, icon: string}> = [];

    if (this.dayData.morning) {
      sections.push({
        time: 'Buổi sáng',
        content: this.dayData.morning,
        icon: 'fa-sun'
      });
    }

    if (this.dayData.afternoon) {
      sections.push({
        time: 'Buổi chiều',
        content: this.dayData.afternoon,
        icon: 'fa-cloud-sun'
      });
    }

    if (this.dayData.late_afternoon) {
      sections.push({
        time: 'Chiều muộn',
        content: this.dayData.late_afternoon,
        icon: 'fa-cloud-sun'
      });
    }

    if (this.dayData.evening) {
      sections.push({
        time: 'Buổi tối',
        content: this.dayData.evening,
        icon: 'fa-moon'
      });
    }

    return sections;
  }

  getDayColor(): string {
    const colors = ['#60a5fa', '#a78bfa', '#f472b6', '#fbbf24', '#34d399'];
    return colors[(this.dayNumber - 1) % colors.length];
  }
}
