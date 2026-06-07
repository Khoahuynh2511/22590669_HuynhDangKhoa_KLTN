import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TravelNews } from '../../shared/models/travel-news.model';

@Component({
  selector: 'app-travel-news-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './travel-news-card.component.html',
  styleUrl: './travel-news-card.component.scss'
})
export class TravelNewsCardComponent {
  @Input() news!: TravelNews;

  get sourceTypeLabel(): string {
    return this.news.source_type === 'news' ? 'Tin tức' : 'Cẩm nang';
  }

  get sourceTypeClass(): string {
    return this.news.source_type === 'news' ? 'badge-news' : 'badge-guide';
  }

  openLink(): void {
    if (this.news.url) {
      window.open(this.news.url, '_blank', 'noopener,noreferrer');
    }
  }

  formatDate(dateString?: string): string {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  }

  truncateSnippet(snippet?: string, maxLength: number = 150): string {
    if (!snippet) return '';
    if (snippet.length <= maxLength) return snippet;
    return snippet.substring(0, maxLength).trim() + '...';
  }
}
