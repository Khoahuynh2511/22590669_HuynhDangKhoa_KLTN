import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface DialogConfig {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'confirm' | 'alert' | 'warning';
}

export interface DialogResult {
  confirmed: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AdminDialogService {
  private dialogSubject = new BehaviorSubject<DialogConfig | null>(null);
  private resultSubject = new BehaviorSubject<DialogResult | null>(null);

  dialog$ = this.dialogSubject.asObservable();
  result$ = this.resultSubject.asObservable();

  /**
   * Show confirmation dialog
   */
  confirm(config: DialogConfig): Promise<boolean> {
    return new Promise((resolve) => {
      const dialogConfig: DialogConfig = {
        ...config,
        confirmText: config.confirmText || 'Xác nhận',
        cancelText: config.cancelText || 'Hủy',
        type: config.type || 'confirm'
      };

      this.dialogSubject.next(dialogConfig);

      const subscription = this.result$.subscribe((result) => {
        if (result !== null) {
          resolve(result.confirmed);
          subscription.unsubscribe();
          this.resultSubject.next(null);
        }
      });
    });
  }

  /**
   * Show alert dialog (only OK button)
   */
  alert(title: string, message: string): Promise<boolean> {
    return this.confirm({
      title,
      message,
      confirmText: 'OK',
      cancelText: '',
      type: 'alert'
    });
  }

  /**
   * Show warning dialog
   */
  warning(title: string, message: string): Promise<boolean> {
    return this.confirm({
      title,
      message,
      confirmText: 'OK',
      cancelText: '',
      type: 'warning'
    });
  }

  /**
   * Close dialog with result
   */
  closeDialog(confirmed: boolean): void {
    this.resultSubject.next({ confirmed });
    this.dialogSubject.next(null);
  }

  /**
   * Close dialog without result
   */
  dismiss(): void {
    this.dialogSubject.next(null);
  }
}
