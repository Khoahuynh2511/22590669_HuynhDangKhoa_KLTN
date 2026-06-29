import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';

/** Một dòng trong bảng xếp hạng người khám phá. */
export interface LeaderboardUser {
    user_id: string;
    full_name?: string | null;
    avatar_url?: string | null;
    provinces_visited: number;
    north_count: number;
    central_count: number;
    south_count: number;
    last_visit_at?: string | null;
}

export interface LeaderboardData {
    items: LeaderboardUser[];
    total: number;
    limit: number;
    offset: number;
    my_rank: number | null;
    my_provinces_visited: number;
}

export interface LeaderboardResult {
    EC: number;
    EM: string;
    data: LeaderboardData;
}

@Injectable({ providedIn: 'root' })
export class LeaderboardService {
    constructor(
        private configService: ConfigService,
        private authService: AuthService
    ) {}

    private get apiBaseUrl(): string {
        return this.configService.getApiUrl();
    }

    private getHeaders() {
        const token = this.authService.getToken();
        return {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        };
    }

    /** Lấy bảng xếp hạng người khám phá (top explorers theo số tỉnh đã check-in). */
    async getLeaderboard(limit = 50, offset = 0): Promise<LeaderboardResult> {
        const url = `${this.apiBaseUrl}/visited-provinces/leaderboard?limit=${limit}&offset=${offset}`;
        const response = await fetch(url, { headers: this.getHeaders() });
        if (!response.ok) throw new Error('Không tải được bảng xếp hạng');
        return response.json();
    }
}
