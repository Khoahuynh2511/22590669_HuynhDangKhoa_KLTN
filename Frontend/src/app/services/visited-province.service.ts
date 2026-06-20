import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';

export interface Province {
    province_id: string;
    province_code: string;
    province_name: string;
    province_name_en?: string;
    region: 'north' | 'central' | 'south';
    latitude?: number;
    longitude?: number;
}

export interface VisitedStats {
    EC: number;
    EM: string;
    total: number;
    total_provinces: number;
    north_count: number;
    central_count: number;
    south_count: number;
    progress_percentage: number;
    provinces: any[];
}

@Injectable({ providedIn: 'root' })
export class VisitedProvinceService {
    /** province_id -> đã check-in */
    private visitedSubject = new BehaviorSubject<Map<string, boolean>>(new Map());
    public visited$ = this.visitedSubject.asObservable();

    private toggling = new Set<string>();

    constructor(
        private configService: ConfigService,
        private authService: AuthService
    ) {
        if (this.authService.getToken()) {
            this.loadInitialVisited();
        }
    }

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

    isVisited(provinceId: string): boolean {
        return this.visitedSubject.value.get(provinceId) || false;
    }

    snapshot(): Map<string, boolean> {
        return new Map(this.visitedSubject.value);
    }

    private setVisitedIds(ids: string[]): void {
        const m = new Map<string, boolean>();
        ids.forEach(id => m.set(id, true));
        this.visitedSubject.next(m);
    }

    async loadInitialVisited(): Promise<void> {
        if (!this.authService.getToken()) return;
        try {
            const res = await this.getMyVisited();
            this.setVisitedIds((res.provinces || []).map((p: any) => p.province_id));
        } catch (e) {
            console.error('Error loading initial visited provinces:', e);
        }
    }

    async getAllProvinces(): Promise<{ EC: number; EM: string; total: number; provinces: Province[] }> {
        const response = await fetch(`${this.apiBaseUrl}/visited-provinces/provinces`, {
            headers: this.getHeaders()
        });
        if (!response.ok) throw new Error('Không tải được danh sách tỉnh');
        return response.json();
    }

    async getMyVisited(): Promise<VisitedStats> {
        const response = await fetch(`${this.apiBaseUrl}/visited-provinces/my`, {
            headers: this.getHeaders()
        });
        if (!response.ok) throw new Error('Không tải được tỉnh đã check-in');
        return response.json();
    }

    async addVisited(provinceId: string): Promise<any> {
        const response = await fetch(`${this.apiBaseUrl}/visited-provinces/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ province_id: provinceId })
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Check-in thất bại');
        return data;
    }

    async removeVisited(provinceId: string): Promise<any> {
        const response = await fetch(`${this.apiBaseUrl}/visited-provinces/${provinceId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Bỏ check-in thất bại');
        return data;
    }

    async autoCheckin(): Promise<{ EC: number; EM: string; auto_checkins: number; matched: string[] }> {
        const response = await fetch(`${this.apiBaseUrl}/visited-provinces/auto-checkin`, {
            method: 'POST',
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Đồng bộ booking thất bại');
        return data;
    }

    /** Toggle optimistic, trả về trạng thái mới (true = đã check-in). */
    async toggle(provinceId: string): Promise<boolean> {
        if (this.toggling.has(provinceId)) return this.isVisited(provinceId);
        this.toggling.add(provinceId);

        const wasVisited = this.isVisited(provinceId);
        const optimistic = this.snapshot();
        optimistic.set(provinceId, !wasVisited);
        this.visitedSubject.next(optimistic);

        try {
            if (wasVisited) {
                await this.removeVisited(provinceId);
            } else {
                await this.addVisited(provinceId);
            }
            return !wasVisited;
        } catch (err) {
            const revert = this.snapshot();
            revert.set(provinceId, wasVisited);
            this.visitedSubject.next(revert);
            throw err;
        } finally {
            this.toggling.delete(provinceId);
        }
    }
}
