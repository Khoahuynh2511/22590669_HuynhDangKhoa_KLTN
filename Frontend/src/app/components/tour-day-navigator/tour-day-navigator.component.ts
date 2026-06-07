import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

export interface DayNavigationItem {
  dayNumber: number;
  label: string;
  isCompleted: boolean;
  isActive: boolean;
}

@Component({
  selector: 'app-tour-day-navigator',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tour-day-navigator.component.html',
  styleUrl: './tour-day-navigator.component.scss'
})
export class TourDayNavigatorComponent {
  @Input() totalDays: number = 0;
  @Input() currentDay: number = 1;
  @Output() dayChanged = new EventEmitter<number>();

  getDayNavigationItems(): DayNavigationItem[] {
    return Array.from({ length: this.totalDays }, (_, i) => ({
      dayNumber: i + 1,
      label: `Ngày ${i + 1}`,
      isCompleted: i + 1 < this.currentDay,
      isActive: i + 1 === this.currentDay
    }));
  }

  selectDay(day: number): void {
    if (day >= 1 && day <= this.totalDays) {
      this.dayChanged.emit(day);
    }
  }

  goToPreviousDay(): void {
    if (this.currentDay > 1) {
      this.dayChanged.emit(this.currentDay - 1);
    }
  }

  goToNextDay(): void {
    if (this.currentDay < this.totalDays) {
      this.dayChanged.emit(this.currentDay + 1);
    }
  }

  hasPrevious(): boolean {
    return this.currentDay > 1;
  }

  hasNext(): boolean {
    return this.currentDay < this.totalDays;
  }

  getProgressPercentage(): number {
    return this.totalDays > 0 ? (this.currentDay / this.totalDays) * 100 : 0;
  }
}
