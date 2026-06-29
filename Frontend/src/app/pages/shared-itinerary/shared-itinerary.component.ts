import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { SharedItineraryService, ItineraryPayload } from '../../services/shared-itinerary.service';

interface SharedDay {
    day: number;
    morning: string[];
    afternoon: string[];
    evening: string[];
}

@Component({
    selector: 'app-shared-itinerary',
    imports: [CommonModule, RouterLink],
    templateUrl: './shared-itinerary.component.html',
    styleUrl: './shared-itinerary.component.scss'
})
export class SharedItineraryComponent implements OnInit {
    title = '';
    itinerary: ItineraryPayload | null = null;
    viewCount = 0;
    loading = true;
    errorMsg: string | null = null;

    readonly slots = [
        { key: 'morning', label: 'Sáng', icon: 'fa-sun' },
        { key: 'afternoon', label: 'Chiều', icon: 'fa-cloud-sun' },
        { key: 'evening', label: 'Tối', icon: 'fa-moon' },
    ];

    constructor(
        private route: ActivatedRoute,
        private sharedItineraryService: SharedItineraryService
    ) {}

    ngOnInit(): void {
        const shareId = this.route.snapshot.paramMap.get('shareId') || '';
        if (!shareId) {
            this.errorMsg = 'Link chia sẻ không hợp lệ.';
            this.loading = false;
            return;
        }
        this.load(shareId);
    }

    async load(shareId: string): Promise<void> {
        this.loading = true;
        try {
            const res = await this.sharedItineraryService.getShare(shareId);
            this.title = res.title || '';
            this.itinerary = res.itinerary || null;
            this.viewCount = res.view_count || 0;
        } catch (e: any) {
            this.errorMsg = e?.message || 'Không tải được lịch trình.';
        } finally {
            this.loading = false;
        }
    }

    days(): SharedDay[] {
        return (this.itinerary?.days || []) as SharedDay[];
    }

    slotItems(d: SharedDay, key: string): string[] {
        return (d as any)[key] || [];
    }
}
