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
}
