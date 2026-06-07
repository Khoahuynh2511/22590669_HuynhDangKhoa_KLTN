import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Review } from '../../services/review.service';

@Component({
    selector: 'app-review-card',
    imports: [CommonModule],
    templateUrl: './review-card.component.html',
    styleUrl: './review-card.component.scss'
})
export class ReviewCardComponent {
    @Input() review!: Review;

    getStarArray(rating: number): boolean[] {
        return Array(5).fill(false).map((_, i) => i < rating);
    }

    getUserInitial(): string {
        const name = this.getUserName();
        return name.charAt(0).toUpperCase() || 'U';
    }

    getUserName(): string {
        // Priority: flat field > nested object > fallback
        if (this.review.user_full_name) return this.review.user_full_name;
        if (this.review.user?.full_name) return this.review.user.full_name;
        return 'Khách hàng';
    }

    getPackageTitle(): string {
        // Priority: flat field > nested object > fallback
        if ((this.review as any).package_name) return (this.review as any).package_name;
        if (this.review.package?.title) return this.review.package.title;
        return 'Tour du lịch';
    }

    getAvatarUrl(): string | null {
        if ((this.review as any).user_profile_picture) {
            return (this.review as any).user_profile_picture;
        }
        return null;
    }

    getAvatarBackground(): string {
        const name = this.getUserName();
        const gradients = [
            'linear-gradient(135deg, #FF6B6B 0%, #EE5D5D 100%)', // Red
            'linear-gradient(135deg, #4FACFE 0%, #00F2FE 100%)', // Blue
            'linear-gradient(135deg, #43E97B 0%, #38F9D7 100%)', // Green
            'linear-gradient(135deg, #FA709A 0%, #FEE140 100%)', // Orange
            'linear-gradient(135deg, #667EEA 0%, #764BA2 100%)', // Purple
            'linear-gradient(135deg, #FDA085 0%, #F6D365 100%)', // Yellow/Peach
        ];

        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }

        const index = Math.abs(hash) % gradients.length;
        return gradients[index];
    }

    truncateComment(comment: string, maxLength: number = 150): string {
        if (comment.length <= maxLength) return comment;
        return comment.substring(0, maxLength) + '...';
    }
}
