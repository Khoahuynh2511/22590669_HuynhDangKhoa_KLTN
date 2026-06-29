import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';

export interface GeocodedLocation {
    lat: number;
    lon: number;
    display_name: string;
    osm_type?: string;
    osm_id?: number;
}

export interface PlaceSuggestion {
    name: string;
    category: string;
    lat: number;
    lng: number;
    description?: string | null;
    image_url?: string | null;
    wikipedia_url?: string | null;
    osm_id: number;
    osm_type: string;
    distance_km: number;
    saved_by_user: boolean;
}

export interface PlaceSuggestionResult {
    EC: number;
    EM: string;
    query: string;
    location: GeocodedLocation | null;
    places: PlaceSuggestion[];
    total: number;
    offset: number;
}

export interface GalleryImage {
    title: string;
    thumb_url: string;
    full_url: string;
    description?: string | null;
    license?: string | null;
    license_url?: string | null;
    author?: string | null;
}

export interface PlaceGalleryResult {
    EC: number;
    EM: string;
    place: string;
    total: number;
    images: GalleryImage[];
}

export interface SeasonMonth {
    month: number;
    name: string;
    temp: number | null;
    rain: number | null;
}

export interface BestSeasonResult {
    EC: number;
    EM: string;
    place: string;
    monthly: SeasonMonth[];
    best_months: SeasonMonth[];
    summary: string;
}

export interface Festival {
    name: string;
    description?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    location?: string | null;
    image_url?: string | null;
    wikidata_url?: string | null;
    wikipedia_url?: string | null;
    month?: number | null;
    region?: string | null;
    lunar?: string | null;
    country?: string | null;
    source?: string | null;
}

export interface FestivalResult {
    EC: number;
    EM: string;
    province: string;
    month: number | null;
    region: string;
    country: string;
    festivals: Festival[];
    total: number;
}

/**
 * Service gọi backend place-suggestion (Nominatim + Overpass + Wikimedia).
 * Backend proxy => tuân thủ OSM usage policy + tránh CORS.
 */
@Injectable({ providedIn: 'root' })
export class PlaceService {
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

    /** Gợi ý các điểm đến / attraction quanh một địa điểm (toàn cầu). Hỗ trợ phân trang qua offset. */
    async suggest(q: string, limit = 10, radiusKm = 15, offset = 0): Promise<PlaceSuggestionResult> {
        const params = new URLSearchParams({
            q,
            limit: String(limit),
            radius_km: String(radiusKm),
            offset: String(offset)
        });
        const response = await fetch(`${this.apiBaseUrl}/places/suggest?${params.toString()}`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.EM || 'Không lấy được gợi ý địa điểm');
        return data as PlaceSuggestionResult;
    }

    /** Geocode tên địa điểm -> tọa độ. */
    async geocode(q: string): Promise<GeocodedLocation | null> {
        const params = new URLSearchParams({ q });
        const response = await fetch(`${this.apiBaseUrl}/places/geocode?${params.toString()}`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) return null;
        return data.location as GeocodedLocation;
    }

    /** Thư viện ảnh địa điểm từ Wikimedia Commons (ảnh CC, open-source). */
    async gallery(place: string, limit = 12): Promise<PlaceGalleryResult> {
        const params = new URLSearchParams({ place, limit: String(limit) });
        const response = await fetch(`${this.apiBaseUrl}/places/gallery?${params.toString()}`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.EM || 'Không lấy được ảnh địa điểm');
        return data as PlaceGalleryResult;
    }

    /** Gợi ý "mùa đẹp nhất" dựa trên khí hậu lịch sử (Open-Meteo Archive). */
    async bestSeason(lat: number, lng: number, place = ''): Promise<BestSeasonResult> {
        const params = new URLSearchParams({
            lat: String(lat),
            lng: String(lng),
            place
        });
        const response = await fetch(`${this.apiBaseUrl}/places/best-season?${params.toString()}`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.EM || 'Không lấy được dữ liệu mùa');
        return data as BestSeasonResult;
    }

    /** Lễ hội / sự kiện TOÀN CẦU (dataset tĩnh VN + Wikidata SPARQL + Nager.Date + Wikipedia). Lọc theo nước/tỉnh/miền/tháng. */
    async festivals(province = '', month: number | null = null, region = '', country = ''): Promise<FestivalResult> {
        const params = new URLSearchParams();
        if (province) params.set('province', province);
        if (month) params.set('month', String(month));
        if (region) params.set('region', region);
        if (country) params.set('country', country);
        const qs = params.toString();
        const response = await fetch(`${this.apiBaseUrl}/places/festivals${qs ? '?' + qs : ''}`, {
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.EM || 'Không lấy được dữ liệu lễ hội');
        return data as FestivalResult;
    }

    /**
     * Lấy 1 lễ hội theo tên (dùng cho trang chi tiết).
     * Fetch toàn bộ curated (country='world' = VN + world) rồi tìm theo tên —
     * refresh-safe, không phụ thuộc state của trang listing.
     */
    async festivalByName(name: string): Promise<Festival | null> {
        try {
            const res = await this.festivals('', null, '', 'world');
            const key = (name || '').trim().toLowerCase();
            return res.festivals.find(f => (f.name || '').trim().toLowerCase() === key) ?? null;
        } catch {
            return null;
        }
    }
}
