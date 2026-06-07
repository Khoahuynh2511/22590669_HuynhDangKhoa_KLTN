import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { AdminDialogService, DialogConfig } from '../../services/admin/admin-dialog.service';

@Component({
  selector: 'app-admin-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-dialog.component.html',
  styleUrls: ['./admin-dialog.component.scss']
})
export class AdminDialogComponent implements OnInit, OnDestroy {
  dialogConfig: DialogConfig | null = null;
  isVisible = false;
  private subscription?: Subscription;

  constructor(private dialogService: AdminDialogService) {}

  ngOnInit() {
    this.subscription = this.dialogService.dialog$.subscribe((config) => {
      this.dialogConfig = config;
      this.isVisible = !!config;
    });
  }

  ngOnDestroy() {
    this.subscription?.unsubscribe();
  }

  onConfirm() {
    this.dialogService.closeDialog(true);
  }

  onCancel() {
    this.dialogService.closeDialog(false);
  }

  onBackdropClick(event: MouseEvent) {
    if ((event.target as HTMLElement).classList.contains('dialog-backdrop')) {
      this.onCancel();
    }
  }

  getIconColor(): string {
    switch (this.dialogConfig?.type) {
      case 'warning':
        return 'text-yellow-500';
      case 'alert':
        return 'text-blue-500';
      default:
        return 'text-red-500';
    }
  }

  getIcon(): string {
    switch (this.dialogConfig?.type) {
      case 'warning':
        return 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z';
      case 'alert':
        return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
      default:
        return 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
    }
  }
}
