import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { PlaceService, Festival } from '../../services/place.service';

@Component({
  selector: 'app-festival-details',
  imports: [CommonModule, RouterLink],
  templateUrl: './festival-details.component.html',
  styleUrl: './festival-details.component.scss'
})
export class FestivalDetailsComponent implements OnInit {
  festival: Festival | null = null;
  loading = true;
  notFound = false;

  readonly fallbackImage = 'img/hotel.jpeg';

  constructor(private route: ActivatedRoute, private placeService: PlaceService) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(async (params) => {
      const name = params.get('name') || ''; // paramMap đã decode
      this.loading = true;
      this.notFound = false;
      try {
        this.festival = await this.placeService.festivalByName(name);
        this.notFound = !this.festival;
      } catch {
        this.festival = null;
        this.notFound = true;
      } finally {
        this.loading = false;
      }
    });
  }

  monthLabel(m?: number | null): string {
    return m ? 'Tháng ' + m : '';
  }

  regionLabel(r?: string | null): string {
    const map: Record<string, string> = { north: 'Miền Bắc', central: 'Miền Trung', south: 'Miền Nam' };
    return r ? (map[r] || r) : '';
  }

  formatDate(d?: string | null): string {
    if (!d) return '';
    try {
      return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(d));
    } catch {
      return d;
    }
  }

  dateRange(): string {
    const f = this.festival;
    if (!f) return '';
    const s = this.formatDate(f.start_date);
    const e = this.formatDate(f.end_date);
    if (s && e) return `${s} → ${e}`;
    return s || e;
  }

  onImageError(event: Event): void {
    const img = event.target as HTMLImageElement;
    if (img.src.endsWith(this.fallbackImage)) return;
    img.src = this.fallbackImage;
  }
}
