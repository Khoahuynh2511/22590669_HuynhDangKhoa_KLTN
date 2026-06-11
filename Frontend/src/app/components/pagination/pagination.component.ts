import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  getDisplayRange,
  getTotalPages,
  getVisiblePageNumbers
} from '../../shared/utils/pagination.util';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pagination.component.html',
  styleUrl: './pagination.component.scss'
})
export class PaginationComponent {
  @Input() currentPage = 1;
  @Input() total = 0;
  @Input() pageSize = 10;
  @Input() showSummary = true;
  @Output() pageChange = new EventEmitter<number>();

  get totalPages(): number {
    return getTotalPages(this.total, this.pageSize);
  }

  get pageNumbers(): number[] {
    return getVisiblePageNumbers(this.currentPage, this.totalPages);
  }

  get displayRange(): string {
    return getDisplayRange(this.currentPage, this.pageSize, this.total);
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.currentPage) {
      return;
    }
    this.pageChange.emit(page);
  }
}
