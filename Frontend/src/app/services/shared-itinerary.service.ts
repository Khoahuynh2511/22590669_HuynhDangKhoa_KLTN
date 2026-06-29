import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';

/** Payload lịch trình do FE build (tự do — chỉ là JSON lưu xuống DB để share). */
export interface ItineraryPayload {
    destination?: string;
    travel_date?: string;
    duration_days?: number;
    group_size?: number;
    total_price?: number;
    days?: Array<{
        day: number;
        [slot: string]: any;
    }>;
    [key: string]: any;
}

export interface CreateShareResult {
    EC: number;
    EM: string;
    share_id: string | null;
    url: string | null;
}

export interface SharedItineraryResult {
    EC: number;
    EM: string;
    title: string;
    itinerary: ItineraryPayload;
    view_count: number;
    created_at?: string | null;
}

@Injectable({ providedIn: 'root' })
export class SharedItineraryService {
    constructor(
        private configService: ConfigService,
        private authService: AuthService
    ) {}

    private get apiBaseUrl(): string {
        return this.configService.getApiUrl();
    }

    private getHeaders(): HeadersInit {
        const token = this.authService.getToken();
        return {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        };
    }

    /** Tạo link chia sẻ lịch trình công khai (cần login). */
    async createShare(payload: ItineraryPayload, title?: string): Promise<CreateShareResult> {
        const response = await fetch(`${this.apiBaseUrl}/itineraries/share`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ payload, title })
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Không tạo được link chia sẻ');
        return data as CreateShareResult;
    }

    /** Lấy lịch trình chia sẻ công khai (không cần login). */
    async getShare(shareId: string): Promise<SharedItineraryResult> {
        const response = await fetch(`${this.apiBaseUrl}/itineraries/${shareId}`, {
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Không tải được lịch trình');
        return data as SharedItineraryResult;
    }
}
