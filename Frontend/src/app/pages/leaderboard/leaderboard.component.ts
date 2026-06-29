import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { LeaderboardService, LeaderboardUser } from '../../services/leaderboard.service';
import { AuthStateService } from '../../services/auth-state.service';

@Component({
    selector: 'app-leaderboard',
    imports: [CommonModule],
    templateUrl: './leaderboard.component.html',
    styleUrl: './leaderboard.component.scss'
})
export class LeaderboardComponent implements OnInit {
    items: LeaderboardUser[] = [];
    total = 0;
    myRank: number | null = null;
    myProvincesVisited = 0;
    currentUserId: string | null = null;

    loading = true;
    errorMsg: string | null = null;

    constructor(
        private leaderboardService: LeaderboardService,
        private authStateService: AuthStateService
    ) {}

    ngOnInit(): void {
        const user = this.authStateService.getCurrentUser();
        this.currentUserId = user?.user_id ?? user?.id ?? null;
        this.load();
    }

    async load(): Promise<void> {
        this.loading = true;
        this.errorMsg = null;
        try {
            const res = await this.leaderboardService.getLeaderboard(50, 0);
            this.items = res.data?.items || [];
            this.total = res.data?.total || 0;
            this.myRank = res.data?.my_rank ?? null;
            this.myProvincesVisited = res.data?.my_provinces_visited || 0;
        } catch (e: any) {
            this.errorMsg = e?.message || 'Không tải được bảng xếp hạng.';
        } finally {
            this.loading = false;
        }
    }

    /** Nhãn phân bổ 3 miền (vd: "Bắc 5 · Trung 3 · Nam 2"). */
    regionBreakdown(user: LeaderboardUser): string {
        const parts: string[] = [];
        if (user.north_count) parts.push(`Bắc ${user.north_count}`);
        if (user.central_count) parts.push(`Trung ${user.central_count}`);
        if (user.south_count) parts.push(`Nam ${user.south_count}`);
        return parts.join(' · ') || '—';
    }

    isMe(user: LeaderboardUser): boolean {
        return !!this.currentUserId && !!user.user_id && this.currentUserId === user.user_id;
    }

    /** Top 3 để render podium. */
    get podium(): LeaderboardUser[] {
        return this.items.slice(0, 3);
    }

    /** Các dòng từ hạng 4 trở đi. */
    get rest(): LeaderboardUser[] {
        return this.items.slice(3);
    }
}
