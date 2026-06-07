import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { TourCardComponent } from '../../components/tour-card/tour-card.component';
import { FavoriteService } from '../../services/favorite.service';
import { AuthStateService } from '../../services/auth-state.service';
import { Tour } from '../../shared/models/tour.model';
import { MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';

@Component({
    selector: 'app-my-favorites',
    imports: [
        CommonModule,
        RouterLink,
        TourCardComponent,
        ToastModule
    ],
    providers: [MessageService],
    templateUrl: './my-favorites.component.html',
    styleUrl: './my-favorites.component.scss'
})
export class MyFavoritesComponent implements OnInit {
    favoriteTours: Tour[] = [];
    isLoading = false;
    errorMessage: string | null = null;
    totalFavorites = 0;

    constructor(
        private favoriteService: FavoriteService,
        private authStateService: AuthStateService,
        private router: Router,
        private messageService: MessageService
    ) { }

    ngOnInit(): void {
        // Check authentication
        if (!this.authStateService.getIsAuthenticated()) {
            this.router.navigate(['/login']);
            return;
        }

        this.loadFavorites();
    }

    async loadFavorites(): Promise<void> {
        this.isLoading = true;
        this.errorMessage = null;

        try {
            const response = await this.favoriteService.getMyFavorites();
            this.favoriteTours = response.packages || [];
            this.totalFavorites = response.total || 0;
            console.log('Loaded favorite tours:', this.totalFavorites);
        } catch (error: any) {
            console.error('Error loading favorites:', error);
            this.errorMessage = error?.message || 'Lỗi khi tải danh sách tours yêu thích. Vui lòng thử lại sau.';
            this.favoriteTours = [];
            this.totalFavorites = 0;

            // If unauthorized, redirect to login
            if (error?.message?.includes('đăng nhập')) {
                setTimeout(() => {
                    this.router.navigate(['/login']);
                }, 2000);
            }
        } finally {
            this.isLoading = false;
        }
    }

    async removeFavorite(packageId: string): Promise<void> {
        try {
            await this.favoriteService.removeFavorite(packageId);

            // Remove from local list
            this.favoriteTours = this.favoriteTours.filter(tour => tour.package_id !== packageId);
            this.totalFavorites = this.favoriteTours.length;

            this.messageService.add({
                severity: 'success',
                summary: 'Thành công',
                detail: 'Đã xóa tour khỏi danh sách yêu thích',
                life: 3000
            });
        } catch (error: any) {
            console.error('Error removing favorite:', error);
            this.messageService.add({
                severity: 'error',
                summary: 'Lỗi',
                detail: error?.message || 'Không thể xóa tour khỏi danh sách yêu thích',
                life: 3000
            });
        }
    }

    onRemoveFavorite(packageId: string): void {
        // The tour card will handle the toggle. 
        // We just need to make sure our list refreshes or removes the item.
        this.favoriteTours = this.favoriteTours.filter(tour => tour.package_id !== packageId);
        this.totalFavorites = this.favoriteTours.length;
    }
}
