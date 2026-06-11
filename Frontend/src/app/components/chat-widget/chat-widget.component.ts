import { Component, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatService } from '../../services/chat.service';
import { ChatRoomService } from '../../services/chat-room.service';
import { BookingService } from '../../services/booking.service';
import { AuthStateService } from '../../services/auth-state.service';
import { OtpPopupComponent } from '../../shared/otp-popup/otp-popup.component';
import { firstValueFrom } from 'rxjs';

type WidgetMode = 'chat' | 'planner';

interface ChatMessage {
  content: string;
  isUser: boolean;
  isError?: boolean;
  tourSelections?: { name: string; price: number; index: number }[];
  mcpUiHtml?: string;
}

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule, OtpPopupComponent],
  templateUrl: './chat-widget.component.html',
  styleUrls: ['./chat-widget.component.scss'],
})
export class ChatWidgetComponent implements OnInit, OnDestroy {
  @ViewChild('chatBody') chatBody!: ElementRef;

  isOpen = false;
  mode: WidgetMode = 'chat';

  // Popup position/size
  popupX = 0;
  popupY = 0;
  popupW = 400;
  popupH = 580;
  private readonly MIN_W = 320;
  private readonly MIN_H = 400;

  // Drag state
  private isDragging = false;
  private dragOffsetX = 0;
  private dragOffsetY = 0;

  // Resize state
  private isResizing = false;
  private resizeDir = '';
  private resizeStartX = 0;
  private resizeStartY = 0;
  private resizeStartW = 0;
  private resizeStartH = 0;
  private resizeStartPX = 0;
  private resizeStartPY = 0;

  // Chat state
  chatMessages: ChatMessage[] = [];
  chatInputText = '';
  isChatStreaming = false;
  isChatTyping = false;
  private chatConversationId: string | null = null;
  private chatUserId: string | null = null;

  showOtpPopup = false;
  otpBookingId = '';
  otpEmail = '';
  returnedOtpCode = '';
  isVerifyingOTP = false;
  isResendingOTP = false;
  otpError = '';
  otpSuccess = '';
  otpCountdown = 300;
  private otpCountdownInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    private chatService: ChatService,
    private chatRoomService: ChatRoomService,
    private bookingService: BookingService,
    private authStateService: AuthStateService,
    private cdr: ChangeDetectorRef,
    private router: Router,
    private sanitizer: DomSanitizer,
    private ngZone: NgZone
  ) {}

  ngOnInit(): void {
    this.resetPosition();
  }

  ngOnDestroy(): void {
    this.clearOtpCountdown();
  }

  openOtpPopup(data: { booking_id?: string; otp_code?: string; email?: string }): void {
    this.otpBookingId = data.booking_id || '';
    this.returnedOtpCode = data.otp_code || '';
    this.otpEmail = data.email || '';
    this.otpError = '';
    this.otpSuccess = '';
    this.showOtpPopup = true;
    this.startOtpCountdown();
    this.cdr.detectChanges();
  }

  private startOtpCountdown(): void {
    this.clearOtpCountdown();
    this.otpCountdown = 300;
    this.otpCountdownInterval = setInterval(() => {
      this.otpCountdown--;
      if (this.otpCountdown <= 0) {
        this.clearOtpCountdown();
        this.otpError = 'Mã OTP đã hết hạn. Vui lòng gửi lại.';
      }
    }, 1000);
  }

  private clearOtpCountdown(): void {
    if (this.otpCountdownInterval) {
      clearInterval(this.otpCountdownInterval);
      this.otpCountdownInterval = null;
    }
  }

  async verifyAgentOTP(code: string): Promise<void> {
    if (!code || code.length !== 6 || !this.otpBookingId) {
      this.otpError = 'Vui lòng nhập đủ 6 số OTP';
      return;
    }

    this.isVerifyingOTP = true;
    this.otpError = '';
    this.otpSuccess = '';

    try {
      const response = await firstValueFrom(
        this.bookingService.verifyOTP(this.otpBookingId, code)
      );
      if (response.EC === 0) {
        this.clearOtpCountdown();
        this.showOtpPopup = false;
        this.chatMessages.push({
          content: 'Xác thực OTP thành công! Đặt tour đã được xác nhận.',
          isUser: false,
        });
        this.cdr.detectChanges();
        setTimeout(() => this.scrollActive(), 50);
      } else {
        this.otpError = response.EM || 'Mã OTP không đúng';
      }
    } catch (error: any) {
      this.otpError = error?.error?.detail || 'Xác thực OTP thất bại';
    } finally {
      this.isVerifyingOTP = false;
    }
  }

  async resendAgentOTP(): Promise<void> {
    if (!this.otpBookingId) {
      this.otpError = 'Không tìm thấy thông tin booking';
      return;
    }

    this.isResendingOTP = true;
    this.otpError = '';
    this.otpSuccess = '';

    try {
      const response = await firstValueFrom(
        this.bookingService.resendOTP(this.otpBookingId)
      );
      if (response.EC === 0) {
        this.returnedOtpCode = response.data?.otp_code || '';
        this.otpSuccess = 'Mã OTP mới đã được tạo';
        this.startOtpCountdown();
      } else {
        this.otpError = response.EM || 'Không thể gửi lại OTP';
      }
    } catch {
      this.otpError = 'Không thể gửi lại OTP';
    } finally {
      this.isResendingOTP = false;
    }
  }

  private resetPosition(): void {
    if (typeof window !== 'undefined') {
      this.popupX = window.innerWidth - this.popupW - 28;
      this.popupY = window.innerHeight - this.popupH - 100;
    }
  }

  // ========== Drag ==========
  startDrag(event: MouseEvent): void {
    if ((event.target as HTMLElement).closest('.close-btn')) return;
    event.preventDefault();
    const offsetX = event.clientX - this.popupX;
    const offsetY = event.clientY - this.popupY;

    const onMove = (e: MouseEvent) => {
      this.popupX = Math.max(0, Math.min(e.clientX - offsetX, window.innerWidth - this.popupW));
      this.popupY = Math.max(0, Math.min(e.clientY - offsetY, window.innerHeight - 40));
      this.cdr.detectChanges();
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    this.ngZone.runOutsideAngular(() => {
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  // ========== Resize ==========
  startResize(event: MouseEvent, dir: string): void {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startY = event.clientY;
    const startW = this.popupW;
    const startH = this.popupH;
    const startPX = this.popupX;
    const startPY = this.popupY;

    const onMove = (e: MouseEvent) => {
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;

      if (dir.includes('e')) {
        this.popupW = Math.max(this.MIN_W, startW + dx);
      }
      if (dir.includes('w')) {
        const newW = Math.max(this.MIN_W, startW - dx);
        this.popupX = startPX + (startW - newW);
        this.popupW = newW;
      }
      if (dir.includes('s')) {
        this.popupH = Math.max(this.MIN_H, startH + dy);
      }
      if (dir.includes('n')) {
        const newH = Math.max(this.MIN_H, startH - dy);
        this.popupY = startPY + (startH - newH);
        this.popupH = newH;
      }
      this.cdr.detectChanges();
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    this.ngZone.runOutsideAngular(() => {
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  // ========== Popup controls ==========
  togglePopup(): void {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.resetPosition();
      if (this.mode === 'chat' && !this.chatMessages.length) this.initChat();
    }
  }

  switchMode(m: WidgetMode): void {
    if (m === 'planner') {
      this.isOpen = false;
      if (!this.authStateService.getIsAuthenticated()) {
        this.router.navigate(['/login']);
        return;
      }
      this.router.navigate(['/chat-room'], { queryParams: { mode: 'planning' } });
      return;
    }
    this.mode = m;
    if (m === 'chat' && !this.chatMessages.length) this.initChat();
    setTimeout(() => this.scrollActive(), 50);
  }

  // ========== Chat ==========
  private initChat(): void {
    if (!this.authStateService.getIsAuthenticated()) return;
    this.chatRoomService.getRooms().subscribe({
      next: (res: any) => {
        if (res.EC === 0 && res.data?.length) {
          const rooms = res.data.sort((a: any, b: any) =>
            new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()
          );
          const latest = rooms[0];
          this.chatConversationId = latest.room_id;
          this.chatUserId = latest.user_id;
          this.loadChatMessages(latest.room_id);
        }
      },
    });
  }

  private loadChatMessages(roomId: string): void {
    this.chatRoomService.getRoomMessages(roomId).subscribe({
      next: (res: any) => {
        if (res.EC === 0 && res.data) {
          this.chatMessages = (res.data || []).map((msg: any) => ({
            content: this.parseContent(msg.content),
            isUser: msg.role === 'user',
          }));
          this.cdr.detectChanges();
          setTimeout(() => this.scrollActive(), 50);
        }
      },
    });
  }

  private parseContent(content: string): string {
    if (!content) return '';
    try {
      const t = content.trim();
      if (t.startsWith('[') && t.endsWith(']')) {
        const arr = JSON.parse(t);
        if (Array.isArray(arr)) {
          const parts = arr.filter((b: any) => b.type === 'text' && b.text).map((b: any) => b.text);
          if (parts.length) return parts.join('\n');
        }
      }
    } catch {}
    return content;
  }

  async sendChatMessage(): Promise<void> {
    if (!this.authStateService.getIsAuthenticated()) {
      this.router.navigate(['/login']);
      this.isOpen = false;
      return;
    }
    if (this.isChatStreaming || !this.chatInputText.trim()) return;

    const msg = this.chatInputText.trim();
    this.chatMessages.push({ content: msg, isUser: true });
    this.chatInputText = '';
    this.isChatStreaming = true;
    this.isChatTyping = true;
    setTimeout(() => this.scrollActive(), 50);

    if (!this.chatConversationId) {
      try {
        const res: any = await this.chatRoomService.createRoom().toPromise();
        if (res.EC === 0 && res.data) {
          this.chatConversationId = res.data.room_id;
          this.chatUserId = res.data.user_id;
        }
      } catch {
        this.isChatStreaming = false;
        this.isChatTyping = false;
        this.chatMessages.push({ content: 'Kh\u00F4ng th\u1EC3 k\u1EBFt n\u1ED1i.', isUser: false, isError: true });
        return;
      }
    }

    try {
      const reader = await this.chatService.sendMessage(msg, this.chatConversationId, this.chatUserId, 5);
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantMsg: ChatMessage | null = null;
      let content = '';
      let isFirst = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.type === 'start') {
              this.chatConversationId = ev.conversation_id;
              this.chatUserId = ev.user_id;
            } else if (ev.type === 'token') {
              if (isFirst) {
                this.isChatTyping = false;
                assistantMsg = { content: '', isUser: false };
                this.chatMessages.push(assistantMsg);
                isFirst = false;
              }
              content += ev.content;
              if (assistantMsg) assistantMsg.content = content;
              this.cdr.detectChanges();
              setTimeout(() => this.scrollActive(), 0);
            } else if (ev.type === 'mcp_ui' && assistantMsg && ev.html) {
              assistantMsg.mcpUiHtml = ev.html;
              this.cdr.detectChanges();
            } else if (ev.type === 'otp_required' && ev.data) {
              this.openOtpPopup(ev.data);
            } else if (ev.type === 'error') {
              if (isFirst) {
                this.isChatTyping = false;
                this.chatMessages.push({ content: ev.error || 'L\u1ED7i', isUser: false, isError: true });
                isFirst = false;
              }
            }
          } catch {}
        }
      }
    } catch {
      this.isChatTyping = false;
      this.chatMessages.push({ content: 'Kh\u00F4ng th\u1EC3 k\u1EBFt n\u1ED1i \u0111\u1EBFn m\u00E1y ch\u1EE7.', isUser: false, isError: true });
    } finally {
      this.isChatStreaming = false;
      this.isChatTyping = false;
      this.cdr.detectChanges();
    }
  }

  onChatKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendChatMessage();
    }
  }

  selectTour(name: string, price: number): void {
    this.chatInputText = `T\u00F4i mu\u1ED1n \u0111\u1EB7t tour "${name}" v\u1EDBi gi\u00E1 ${this.formatPrice(price)}`;
  }

  handleMcpClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const btn = target.closest('[data-payment-url]') as HTMLElement;
    if (btn) {
      const url = btn.getAttribute('data-payment-url');
      if (url) window.location.href = url;
    }
  }

  // ========== Shared ==========
  autoResize(event: Event): void {
    const el = event.target as HTMLTextAreaElement;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 80) + 'px';
  }

  formatContent(content: string): string {
    if (!content) return '';
    return content
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  sanitize(html: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(html || '');
  }

  private scrollActive(): void {
    const el = this.chatBody?.nativeElement;
    if (el) el.scrollTop = el.scrollHeight;
  }
}