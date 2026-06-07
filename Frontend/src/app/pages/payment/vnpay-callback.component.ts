import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-vnpay-callback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="callback-container">
      <div class="payment-result-card">
        @if (isProcessing) {
          <div class="loading-section">
            <div class="spinner"></div>
            <p class="loading-text">Đang xử lý kết quả thanh toán...</p>
          </div>
        } @else {
          <div class="result-section">
            @if (isSuccess) {
              <div class="success-icon">
                <svg class="w-16 h-16 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <h2 class="result-title success">Thanh toán thành công!</h2>
              <p class="result-message">Giao dịch của bạn đã được xử lý thành công.</p>
              @if (transactionInfo) {
                <div class="transaction-info">
                  <div class="info-item">
                    <span class="info-label">Mã giao dịch:</span>
                    <span class="info-value">{{ transactionInfo.transactionNo }}</span>
                  </div>
                  @if (transactionInfo.amount) {
                    <div class="info-item">
                      <span class="info-label">Số tiền:</span>
                      <span class="info-value">{{ formatPrice(transactionInfo.amount) }}</span>
                    </div>
                  }
                  @if (transactionInfo.bankCode) {
                    <div class="info-item">
                      <span class="info-label">Ngân hàng:</span>
                      <span class="info-value">{{ transactionInfo.bankCode }}</span>
                    </div>
                  }
                </div>
              }
            } @else {
              <div class="error-icon">
                <svg class="w-16 h-16 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <h2 class="result-title error">Thanh toán thất bại</h2>
              <p class="result-message">{{ errorMessage || 'Giao dịch không thành công. Vui lòng thử lại.' }}</p>
            }
            <div class="action-buttons">
              <button (click)="goToBookings()" class="primary-button">
                Xem đơn hàng của tôi
              </button>
              <button (click)="goToHome()" class="secondary-button">
                Về trang chủ
              </button>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .callback-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }

    .payment-result-card {
      background: white;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      padding: 48px;
      max-width: 500px;
      width: 100%;
      text-align: center;
    }

    .loading-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
    }

    .spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #f3f4f6;
      border-top-color: #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loading-text {
      color: #6b7280;
      font-size: 16px;
      margin: 0;
    }

    .result-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
    }

    .success-icon, .error-icon {
      display: flex;
      justify-content: center;
    }

    .result-title {
      font-size: 28px;
      font-weight: bold;
      margin: 0;
    }

    .result-title.success {
      color: #10b981;
    }

    .result-title.error {
      color: #ef4444;
    }

    .result-message {
      color: #6b7280;
      font-size: 16px;
      margin: 0;
    }

    .transaction-info {
      width: 100%;
      background: #f9fafb;
      border-radius: 8px;
      padding: 20px;
      margin-top: 8px;
    }

    .info-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #e5e7eb;
    }

    .info-item:last-child {
      border-bottom: none;
    }

    .info-label {
      color: #6b7280;
      font-size: 14px;
    }

    .info-value {
      color: #111827;
      font-weight: 600;
      font-size: 14px;
    }

    .action-buttons {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
      margin-top: 8px;
    }

    .primary-button {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 14px 24px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .primary-button:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
    }

    .secondary-button {
      background: white;
      color: #6b7280;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      padding: 14px 24px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.2s;
    }

    .secondary-button:hover {
      background: #f9fafb;
    }
  `]
})
export class VnpayCallbackComponent implements OnInit {
  isProcessing = true;
  isSuccess = false;
  errorMessage = '';
  transactionInfo: {
    transactionNo?: string;
    amount?: number;
    bankCode?: string;
  } | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Check payment return URL và redirect về chat room nếu có
    const returnUrl = sessionStorage.getItem('payment_return_url');
    if (returnUrl && returnUrl.includes('/chat-room/')) {
      sessionStorage.removeItem('payment_return_url');
      // Extract path từ full URL
      try {
        const url = new URL(returnUrl);
        // Redirect về chat room sau 2 giây (để user thấy kết quả thanh toán)
        setTimeout(() => {
          this.router.navigateByUrl(url.pathname + url.search);
        }, 2000);
      } catch {
        // Fallback: extract path manually
        const pathMatch = returnUrl.match(/\/chat-room\/[^?#]+/);
        if (pathMatch) {
          setTimeout(() => {
            this.router.navigateByUrl(pathMatch[0]);
          }, 2000);
        }
      }
    }
    
    this.route.queryParams.subscribe(params => {
      this.processCallback(params);
    });
  }

  private processCallback(params: any): void {
    const status = params['status'];
    const paymentStatus = params['payment_status'];
    const message = params['message'];
    const paymentId = params['payment_id'];
    const bookingId = params['booking_id'];
    
    const responseCode = params['vnp_ResponseCode'];
    const transactionStatus = params['vnp_TransactionStatus'];
    const transactionNo = params['vnp_TransactionNo'];
    const amount = params['vnp_Amount'];
    const bankCode = params['vnp_BankCode'];
    const orderInfo = params['vnp_OrderInfo'];
    const txnRef = params['vnp_TxnRef'];

    setTimeout(() => {
      this.isProcessing = false;

      if (status || paymentStatus) {
        this.handleBackendRedirect(status || paymentStatus, message, transactionNo, amount, bankCode);
      } else if (responseCode !== undefined) {
        this.handleVnpayDirectRedirect(responseCode, transactionStatus, transactionNo, amount, bankCode);
      } else {
        this.isSuccess = false;
        this.errorMessage = 'Không tìm thấy thông tin thanh toán. Vui lòng kiểm tra lại.';
      }
    }, 1500);
  }

  private handleBackendRedirect(status: string, message: string | undefined, transactionNo: string | undefined, amount: string | undefined, bankCode: string | undefined): void {
    const isSuccess = status === 'success' || status === 'completed' || status === 'paid';
    
    if (isSuccess) {
      this.isSuccess = true;
      this.transactionInfo = {
        transactionNo: transactionNo || undefined,
        amount: amount ? parseInt(amount) / 100 : undefined,
        bankCode: bankCode || undefined
      };
      
      if (message) {
        this.errorMessage = '';
      }

      // Check nếu có return URL từ chat room thì redirect về đó với payment_success param, không thì về bookings
      const returnUrl = sessionStorage.getItem('payment_return_url');
      if (returnUrl && returnUrl.includes('/chat-room/')) {
        sessionStorage.removeItem('payment_return_url');
        try {
          const url = new URL(returnUrl);
          // Thêm query param payment_success để chatbot hiển thị message chúc mừng
          const separator = url.search ? '&' : '?';
          const redirectUrl = `${url.pathname}${url.search}${separator}payment_success=true`;
          setTimeout(() => {
            this.router.navigateByUrl(redirectUrl);
          }, 2000);
        } catch {
          const pathMatch = returnUrl.match(/\/chat-room\/[^?#]+/);
          if (pathMatch) {
            setTimeout(() => {
              this.router.navigateByUrl(`${pathMatch[0]}?payment_success=true`);
            }, 2000);
          } else {
            setTimeout(() => {
              this.goToBookings();
            }, 2000);
          }
        }
      } else {
        setTimeout(() => {
          this.goToBookings();
        }, 2000);
      }
    } else {
      this.isSuccess = false;
      this.errorMessage = message || 'Thanh toán không thành công. Vui lòng thử lại.';
    }
  }

  private handleVnpayDirectRedirect(responseCode: string, transactionStatus: string | undefined, transactionNo: string | undefined, amount: string | undefined, bankCode: string | undefined): void {
    if (responseCode === '00' && transactionStatus === '00') {
      this.isSuccess = true;
      this.transactionInfo = {
        transactionNo: transactionNo || undefined,
        amount: amount ? parseInt(amount) / 100 : undefined,
        bankCode: bankCode || undefined
      };

      // Check nếu có return URL từ chat room thì redirect về đó với payment_success param, không thì về bookings
      const returnUrl = sessionStorage.getItem('payment_return_url');
      if (returnUrl && returnUrl.includes('/chat-room/')) {
        sessionStorage.removeItem('payment_return_url');
        try {
          const url = new URL(returnUrl);
          // Thêm query param payment_success để chatbot hiển thị message chúc mừng
          const separator = url.search ? '&' : '?';
          const redirectUrl = `${url.pathname}${url.search}${separator}payment_success=true`;
          setTimeout(() => {
            this.router.navigateByUrl(redirectUrl);
          }, 2000);
        } catch {
          const pathMatch = returnUrl.match(/\/chat-room\/[^?#]+/);
          if (pathMatch) {
            setTimeout(() => {
              this.router.navigateByUrl(`${pathMatch[0]}?payment_success=true`);
            }, 2000);
          } else {
            setTimeout(() => {
              this.goToBookings();
            }, 2000);
          }
        }
      } else {
        setTimeout(() => {
          this.goToBookings();
        }, 2000);
      }
    } else {
      this.isSuccess = false;
      this.errorMessage = this.getErrorMessage(responseCode);
    }
  }

  private getErrorMessage(responseCode: string): string {
    const errorMessages: { [key: string]: string } = {
      '07': 'Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường).',
      '09': 'Thẻ/Tài khoản chưa đăng ký dịch vụ InternetBanking',
      '10': 'Xác thực thông tin thẻ/tài khoản không đúng quá 3 lần',
      '11': 'Đã hết hạn chờ thanh toán. Xin vui lòng thực hiện lại giao dịch.',
      '12': 'Thẻ/Tài khoản bị khóa.',
      '13': 'Nhập sai mật khẩu xác thực giao dịch (OTP). Xin vui lòng thực hiện lại giao dịch.',
      '51': 'Tài khoản không đủ số dư để thực hiện giao dịch.',
      '65': 'Tài khoản đã vượt quá hạn mức giao dịch cho phép.',
      '75': 'Ngân hàng thanh toán đang bảo trì.',
      '79': 'Nhập sai mật khẩu thanh toán quá số lần quy định. Xin vui lòng thực hiện lại giao dịch.',
      '99': 'Lỗi không xác định.'
    };

    return errorMessages[responseCode] || `Mã lỗi: ${responseCode}. Vui lòng liên hệ hỗ trợ để được giải đáp.`;
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  goToBookings(): void {
    this.router.navigate(['/my-bookings']);
  }

  goToHome(): void {
    this.router.navigate(['/home']);
  }
}

