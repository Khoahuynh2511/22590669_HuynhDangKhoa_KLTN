import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Festival } from '../../services/place.service';

@Component({
  selector: 'app-festival-card',
  imports: [CommonModule, RouterLink],
  templateUrl: './festival-card.component.html',
  styleUrl: './festival-card.component.scss'
})
export class FestivalCardComponent {
  @Input() festival!: Festival;
  @Input() showDetails = true;

  readonly fallbackImage = 'img/hotel.jpeg';

  monthLabel(m?: number | null): string {
    return m ? 'Tháng ' + m : '';
  }

  regionLabel(r?: string | null): string {
    const map: Record<string, string> = { north: 'Miền Bắc', central: 'Miền Trung', south: 'Miền Nam' };
    return r ? (map[r] || r) : '';
  }

  shortDescription(): string {
    const d = this.festival.description || '';
    const max = 120;
    return d.length <= max ? d : d.substring(0, max) + '…';
  }

  onImageError(event: Event): void {
    const img = event.target as HTMLImageElement;
    if (img.src.endsWith(this.fallbackImage)) return;
    img.src = this.fallbackImage;
  }
}
