import { Component, OnInit, OnDestroy, Input, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { NotificationService, Notification } from '../../services/notification.service';

@Component({
    selector: 'app-notification-bell',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './notification-bell.component.html',
    styleUrls: ['./notification-bell.component.scss']
})
export class NotificationBellComponent implements OnInit, OnDestroy {
    @Input() isWhiteMode = false; // For transparent header

    notifications: Notification[] = [];
    unreadCount = 0;
    isDropdownOpen = false;
    isLoading = false;

    private subscriptions: Subscription[] = [];
    private pollInterval = 30000; // Poll every 30 seconds

    constructor(
        private notificationService: NotificationService,
        private router: Router,
        private elementRef: ElementRef
    ) { }

    ngOnInit(): void {
        // Only load notifications if user is logged in
        if (this.isLoggedIn()) {
            this.loadUnreadCount();
            this.loadNotifications();

            // Set up polling for new notifications
            const pollSub = interval(this.pollInterval).subscribe(() => {
                if (this.isLoggedIn()) {
                    this.loadUnreadCount();
                }
            });
            this.subscriptions.push(pollSub);
        }
    }

    ngOnDestroy(): void {
        this.subscriptions.forEach(sub => sub.unsubscribe());
    }

    /**
     * Check if user is logged in
     */
    private isLoggedIn(): boolean {
        return !!localStorage.getItem('access_token');
    }

    @HostListener('document:click', ['$event'])
    onDocumentClick(event: Event): void {
        if (!this.elementRef.nativeElement.contains(event.target)) {
            this.isDropdownOpen = false;
        }
    }

    toggleDropdown(): void {
        if (!this.isLoggedIn()) {
            // Redirect to login if not logged in
            this.router.navigate(['/login']);
            return;
        }

        this.isDropdownOpen = !this.isDropdownOpen;
        if (this.isDropdownOpen) {
            this.loadNotifications();
        }
    }

    loadUnreadCount(): void {
        if (!this.isLoggedIn()) return;

        this.notificationService.getUnreadCount().subscribe({
            next: (response) => {
                if (response.EC === 0) {
                    this.unreadCount = response.count;
                }
            },
            error: () => {
                // Silent fail - user might not be logged in
            }
        });
    }

    loadNotifications(): void {
        if (!this.isLoggedIn()) return;

        this.isLoading = true;
        this.notificationService.getNotifications(false, 20).subscribe({
            next: (response) => {
                if (response.EC === 0 && response.data) {
                    this.notifications = response.data;
                }
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            }
        });
    }

    markAsRead(notification: Notification, event: Event): void {
        event.stopPropagation();

        if (!notification.is_read) {
            this.notificationService.markAsRead(notification.notification_id).subscribe({
                next: (response) => {
                    if (response.EC === 0) {
                        notification.is_read = true;
                        this.unreadCount = Math.max(0, this.unreadCount - 1);
                    }
                },
                error: (err) => console.error('Error marking as read:', err)
            });
        }

        // Navigate if metadata contains link
        if (notification.metadata?.link) {
            this.router.navigate([notification.metadata.link]);
            this.isDropdownOpen = false;
        }
    }

    markAllAsRead(): void {
        this.notificationService.markAllAsRead().subscribe({
            next: (response) => {
                if (response.EC === 0) {
                    this.notifications.forEach(n => n.is_read = true);
                    this.unreadCount = 0;
                }
            },
            error: (err) => console.error('Error marking all as read:', err)
        });
    }

    formatTimeAgo(dateString: string): string {
        return this.notificationService.formatTimeAgo(dateString);
    }

    getIcon(type: string): string {
        return this.notificationService.getNotificationIcon(type);
    }

    getIconColor(type: string): string {
        return this.notificationService.getNotificationIconColor(type);
    }

    trackByNotificationId(index: number, notification: Notification): string {
        return notification.notification_id;
    }
}
