import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';

@Injectable({
    providedIn: 'root'
})
export class FavoriteService {
    private favoriteStatusSubject = new BehaviorSubject<Map<string, boolean>>(new Map());
    public favoriteStatus$ = this.favoriteStatusSubject.asObservable();

    private loadingFavorites = new Set<string>();

    constructor(
        private configService: ConfigService,
        private authService: AuthService
    ) {
        // Initial load if token exists
        if (this.authService.getToken()) {
            this.loadInitialFavorites();
        }
    }

    private get apiBaseUrl(): string {
        return this.configService.getApiUrl();
    }

    private getHeaders() {
        const token = this.authService.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }

    async loadInitialFavorites(): Promise<void> {
        if (!this.authService.getToken()) return;

        try {
            const response = await this.getMyFavorites();
            const statusMap = new Map<string, boolean>();
            if (response.packages) {
                response.packages.forEach((pkg: any) => {
                    statusMap.set(pkg.package_id, true);
                });
            }
            this.favoriteStatusSubject.next(statusMap);
        } catch (error) {
            console.error('Error loading initial favorites:', error);
        }
    }

    isFavorite(packageId: string): boolean {
        return this.favoriteStatusSubject.value.get(packageId) || false;
    }

    async toggleFavorite(packageId: string): Promise<boolean> {
        if (!this.authService.getToken()) {
            throw new Error('User not authenticated');
        }

        if (this.loadingFavorites.has(packageId)) return this.isFavorite(packageId);

        this.loadingFavorites.add(packageId);

        const currentMap = new Map(this.favoriteStatusSubject.value);
        const wasFavorite = currentMap.get(packageId) || false;
        const newStatus = !wasFavorite;

        // Optimistic update
        currentMap.set(packageId, newStatus);
        this.favoriteStatusSubject.next(currentMap);

        try {
            if (newStatus) {
                await this.addFavorite(packageId);
            } else {
                await this.removeFavorite(packageId);
            }
            return newStatus;
        } catch (error) {
            // Revert on error
            const revertMap = new Map(this.favoriteStatusSubject.value);
            revertMap.set(packageId, wasFavorite);
            this.favoriteStatusSubject.next(revertMap);
            throw error;
        } finally {
            this.loadingFavorites.delete(packageId);
        }
    }

    async checkFavorite(packageId: string): Promise<{ EC: number; EM: string; is_favorite: boolean }> {
        const response = await fetch(`${this.apiBaseUrl}/favorites/check/${packageId}`, {
            headers: this.getHeaders()
        });
        if (!response.ok) throw new Error('Failed to check favorite status');
        const data = await response.json();

        // Sync local state if needed
        if (data.EC === 0) {
            const currentMap = new Map(this.favoriteStatusSubject.value);
            if (currentMap.get(packageId) !== data.is_favorite) {
                currentMap.set(packageId, data.is_favorite);
                this.favoriteStatusSubject.next(currentMap);
            }
        }

        return data;
    }

    async getMyFavorites(): Promise<{ EC: number; EM: string; packages: any[]; total: number }> {
        const response = await fetch(`${this.apiBaseUrl}/favorites/my`, {
            headers: this.getHeaders()
        });
        if (!response.ok) throw new Error('Failed to fetch favorite tours');
        return response.json();
    }

    async addFavorite(packageId: string): Promise<any> {
        const response = await fetch(`${this.apiBaseUrl}/favorites/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ package_id: packageId })
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Failed to add favorite');
        return data;
    }

    async removeFavorite(packageId: string): Promise<any> {
        const response = await fetch(`${this.apiBaseUrl}/favorites/${packageId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        const data = await response.json();
        if (!response.ok || data.EC !== 0) throw new Error(data.EM || 'Failed to remove favorite');
        return data;
    }
}
