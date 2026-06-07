import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Notification {
    notification_id: string;
    user_id: string;
    type: string;
    title: string;
    message: string;
    metadata?: any;
    is_read: boolean;
    created_at: string;
}

export interface NotificationListResponse {
    EC: number;
    EM: string;
    data: Notification[] | null;
    total: number | null;
}

export interface NotificationMarkReadResponse {
    EC: number;
    EM: string;
}

export interface NotificationUnreadCountResponse {
    EC: number;
    EM: string;
    count: number;
}

@Injectable({
    providedIn: 'root'
})
export class NotificationService {
    private apiUrl = `${environment.apiUrl}/notifications`;

    constructor(private http: HttpClient) { }

    /**
     * Get headers with Authorization token
     */
    private getHeaders(): HttpHeaders {
        const token = localStorage.getItem('access_token');
        return new HttpHeaders({
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        });
    }

    /**
     * Lấy danh sách thông báo
     */
    getNotifications(
        unreadOnly: boolean = false,
        limit: number = 50,
        offset?: number
    ): Observable<NotificationListResponse> {
        let params = new HttpParams()
            .set('unread_only', unreadOnly.toString())
            .set('limit', limit.toString());

        if (offset !== undefined) {
            params = params.set('offset', offset.toString());
        }

        return this.http.get<NotificationListResponse>(this.apiUrl, {
            params,
            headers: this.getHeaders()
        });
    }

    /**
     * Lấy số lượng thông báo chưa đọc
     */
    getUnreadCount(): Observable<NotificationUnreadCountResponse> {
        return this.http.get<NotificationUnreadCountResponse>(
            `${this.apiUrl}/unread-count`,
            { headers: this.getHeaders() }
        );
    }

    /**
     * Đánh dấu một thông báo đã đọc
     */
    markAsRead(notificationId: string): Observable<NotificationMarkReadResponse> {
        return this.http.post<NotificationMarkReadResponse>(
            `${this.apiUrl}/${notificationId}/read`,
            {},
            { headers: this.getHeaders() }
        );
    }

    /**
     * Đánh dấu tất cả thông báo đã đọc
     */
    markAllAsRead(): Observable<NotificationMarkReadResponse> {
        return this.http.post<NotificationMarkReadResponse>(
            `${this.apiUrl}/read-all`,
            {},
            { headers: this.getHeaders() }
        );
    }

    /**
     * Format time ago cho thông báo
     */
    formatTimeAgo(dateString: string): string {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);

        if (diffSec < 60) return 'Vừa xong';
        if (diffMin < 60) return `${diffMin} phút trước`;
        if (diffHour < 24) return `${diffHour} giờ trước`;
        if (diffDay < 7) return `${diffDay} ngày trước`;

        return date.toLocaleDateString('vi-VN');
    }

    /**
     * Get icon class based on notification type
     */
    getNotificationIcon(type: string): string {
        const iconMap: Record<string, string> = {
            'booking_confirmed': 'fas fa-check-circle',
            'booking_cancelled': 'fas fa-times-circle',
            'tour_cancelled': 'fas fa-exclamation-triangle',
            'payment_success': 'fas fa-credit-card',
            'payment_failed': 'fas fa-exclamation-circle',
            'tour_reminder': 'fas fa-bell',
            'promotion': 'fas fa-gift',
            'system': 'fas fa-info-circle'
        };
        return iconMap[type] || 'fas fa-bell';
    }

    /**
     * Get icon color class based on notification type
     */
    getNotificationIconColor(type: string): string {
        const colorMap: Record<string, string> = {
            'booking_confirmed': 'text-green-500',
            'booking_cancelled': 'text-red-500',
            'tour_cancelled': 'text-orange-500',
            'payment_success': 'text-green-500',
            'payment_failed': 'text-red-500',
            'tour_reminder': 'text-blue-500',
            'promotion': 'text-purple-500',
            'system': 'text-gray-500'
        };
        return colorMap[type] || 'text-blue-500';
    }
}
