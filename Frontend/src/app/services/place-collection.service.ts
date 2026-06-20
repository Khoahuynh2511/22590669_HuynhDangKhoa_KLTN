import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';
import { BehaviorSubject } from 'rxjs';

export interface SavedPlace {
    save_id: string;
    user_id: string;
    place_name: string;
    place_display_name: string;
    latitude: number;
    longitude: number;
    category: string;
    image_url?: string | null;
    description?: string | null;
    wikipedia_url?: string | null;
    osm_id: number;
    source: string;
    created_at?: string;
}

export interface VisitedProvinceItem {
    visit_id: string;
    province_id: string;
    province_name: string;
    province_name_en?: string;
    region: string;
    latitude?: number;
    longitude?: number;
    visited_at?: string;
    visit_source?: string;
    [k: string]: any;
}

export interface CombinedCollection {
    EC: number;
    EM: string;
    total_wishlist: number;
    total_visited: number;
    wishlist: SavedPlace[];
    visited_provinces: VisitedProvinceItem[];
}

/** Payload để lưu 1 place vào wishlist (POST /place-collections/). */
export interface SavePlacePayload {
    place_name: string;
    place_display_name: string;
    latitude: number;
    longitude: number;
    category: string;
    image_url?: string | null;
    description?: string | null;
    wikipedia_url?: string | null;
    osm_id: number;
}

/**
 * Service quản lý "Bộ sưu tập" của user:
 * - wishlist (user_place_saves): điểm muốn đến.
 * - visited (visited_provinces): nơi đã đến (reuse).
 */
@Injectable({ providedIn: 'root' })
export class PlaceCollectionService {
    /** osm_id -> đã lưu (cache để đánh dấu nút "Lưu" nhanh) */
    private savedSubject = new BehaviorSubject<Set<number>>(new Set());
    public saved$ = this.savedSubject.asObservable();

    constructor(
        private configService: ConfigService,
        private authService: AuthService
    ) {
        if (this.authService.getToken()) {
            this.refreshSavedIds().catch(() => {});
        }
    }

    private get apiBaseUrl(): string {
        return this.configService.getApiUrl();
    }

    private getHeaders(): HeadersInit {
        const token = this.authService.getToken();
        return {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        };
    }

    isSaved(osmId: number): boolean {
        return this.savedSubject.value.has(osmId);
    }

    /** Tải lại tập osm_id đã lưu (để annotate danh sách gợi ý). */
    async refreshSavedIds(): Promise<Set<number>> {
        try {
            const list = await this.list();
            const ids = new Set<number>((list.wishlist || []).map(p => p.osm_id));
            this.savedSubject.next(ids);
            return ids;
        } catch {
            return this.savedSubject.value;
        }
    }

    async list(): Promise<{ EC: number; EM: string; total: number; wishlist: SavedPlace[] }> {
        const response = await fetch(`${this.apiBaseUrl}/place-collections/`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Không tải được bộ sưu tập');
        return data;
    }

    async getCombined(): Promise<CombinedCollection> {
        const response = await fetch(`${this.apiBaseUrl}/place-collections/combined`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Không tải được bộ sưu tập');
        return data as CombinedCollection;
    }

    async save(place: SavePlacePayload): Promise<boolean> {
        const response = await fetch(`${this.apiBaseUrl}/place-collections/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(place)
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Lưu thất bại');
        // cập nhật cache optimistic
        const next = new Set(this.savedSubject.value);
        next.add(place.osm_id);
        this.savedSubject.next(next);
        return true;
    }

    async remove(saveId: string, osmId?: number): Promise<boolean> {
        const response = await fetch(`${this.apiBaseUrl}/place-collections/${saveId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Bỏ lưu thất bại');
        if (osmId !== undefined) {
            const next = new Set(this.savedSubject.value);
            next.delete(osmId);
            this.savedSubject.next(next);
        }
        return false;
    }
}
