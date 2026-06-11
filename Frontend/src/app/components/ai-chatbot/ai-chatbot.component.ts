import { Component, ElementRef, EventEmitter, Output, ViewChild, ChangeDetectorRef, OnInit, OnDestroy, SecurityContext, AfterViewChecked, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatService } from '../../services/chat.service';
import { ChatRoomService } from '../../services/chat-room.service';
import { TripPlannerService } from '../../services/trip-planner.service';
import { PaymentService } from '../../services/payment.service';
import { TourService } from '../../services/tour.service';
import { AuthStateService } from '../../services/auth-state.service';
import { TourCardComponent } from '../tour-card/tour-card.component';
import { OtpPopupComponent } from '../../shared/otp-popup/otp-popup.component';
import { BookingService } from '../../services/booking.service';
import { Tour } from '../../shared/models/tour.model';
import { ActivitySlot, ItineraryDay, TripPlanStreamEvent } from '../../shared/models/trip-planning.model';
import { firstValueFrom } from 'rxjs';

interface TourSelection {
  name: string;
  price: number;
  index: number;
}

interface McpUiResource {
  text?: string;
  [key: string]: any;
}

interface Message {
  content: string;
  isUser: boolean;
  tours?: any[];
  tourSelections?: TourSelection[];
  isError?: boolean;
  tourPackages?: Tour[];
  mcpUiResource?: McpUiResource;
  mcpUiHtml?: string;
  showTourCards?: boolean;
  // Trip planning fields
  tripStep?: number;
  itineraryData?: Record<string, ItineraryDay>;
  availableActivities?: ActivitySlot[];
  showItineraryBuilder?: boolean;
  transportData?: { flights?: any[]; trains?: any[] };
  showTransport?: boolean;
  checkoutData?: any;
  showCheckout?: boolean;
  tripTotalPrice?: number;
  quickSuggestions?: string[];
}

interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  remoteConversationId: string | null;
  userId: string | null;
  conversationType: 'general_chat' | 'trip_planning';
}

@Component({
  selector: 'app-ai-chatbot',
  imports: [CommonModule, FormsModule, TourCardComponent, OtpPopupComponent],
  templateUrl: './ai-chatbot.component.html',
  styleUrl: './ai-chatbot.component.scss'
})
export class AiChatbotComponent implements OnInit, OnDestroy {
  @Output() close = new EventEmitter<void>();
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('messageInput') messageInputRef!: ElementRef;

  messages: Message[] = [];
  userMessage = '';
  isStreaming = false;
  isTyping = false;
  conversationId: string | null = null;
  userId: string | null = null;
  headerStatus = 'Online';
  currentStreamContent = '';
  conversations: Conversation[] = [];
  activeConversation: Conversation | null = null;
  // Cache and loading states
  private messagesCache = new Map<string, Message[]>();
  private readonly conversationsCacheKey = 'ai.chatbot.conversations.cache';
  private readonly conversationsCacheTTL = 5 * 60 * 1000; // 5 phút
  isDeletingConversation: string | null = null;
  isLoadingConversations = false;
  isLoadingMessages = false;
  userHasScrolledUp: boolean = false;
  isProcessingPayment: boolean = false;

  // Agent OTP popup state
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

  // Trip planning state
  currentTripStep = signal(1);
  isTripComplete = signal(false);
  tripConversationId: string | null = null;
  draggedActivity: { dayKey: string; slot: string; activity: ActivitySlot | null } | null = null;
  activeReplacePanel: { msgIndex: number; dayKey: string; slot: string } | null = null;
  dragOverSlot: { dayKey: string; slot: string } | null = null;
  composerQuickSuggestions: string[] = [];
  private lastRecommendedTours: Tour[] = [];

  constructor(
    private chatService: ChatService,
    private chatRoomService: ChatRoomService,
    private tripPlannerService: TripPlannerService,
    private paymentService: PaymentService,
    private cdr: ChangeDetectorRef,
    private router: Router,
    private route: ActivatedRoute,
    private tourService: TourService,
    private authStateService: AuthStateService,
    private bookingService: BookingService,
    private sanitizer: DomSanitizer
  ) { }

  private paymentButtonClickHandler = (event: MessageEvent) => {
    if (event.data && event.data.type === 'mcp_ui_payment') {
      const paymentUrl = event.data.payment_url;
      const bookingId = event.data.booking_id;
      console.log('Payment button clicked:', { paymentUrl, bookingId });

      if (paymentUrl) {
        window.location.href = paymentUrl;
      }
    }
  };

  ngOnInit(): void {
    // Check nếu có payment_return_url trong sessionStorage (sau khi thanh toán xong)
    const returnUrl = sessionStorage.getItem('payment_return_url');
    if (returnUrl && returnUrl.includes('/chat-room/')) {
      // Clear sessionStorage và redirect về chat room
      sessionStorage.removeItem('payment_return_url');
      // Đảm bảo đang ở đúng chat room
      const currentUrl = window.location.href;
      if (!currentUrl.includes('/chat-room/')) {
        this.router.navigateByUrl(returnUrl);
        return;
      }
    }

    // Listen for payment button clicks from dynamically rendered HTML
    window.addEventListener('message', this.paymentButtonClickHandler);

    // Also listen for custom events
    window.addEventListener('mcpPayment', ((event: CustomEvent) => {
      const paymentUrl = event.detail?.payment_url;
      if (paymentUrl) {
        // Lưu chat room URL vào sessionStorage để redirect về sau khi thanh toán
        const currentUrl = window.location.href;
        sessionStorage.setItem('payment_return_url', currentUrl);
        // KHÔNG modify payment URL - giữ nguyên như backend generate
        window.location.href = paymentUrl;
      }
    }) as EventListener);
    if (!this.authStateService.getIsAuthenticated()) {
      this.onClose();
      this.router.navigate(['/login']);
      return;
    }

    // Clear conversations và load từ API
    this.conversations = [];
    this.messages = [];

    const urlRoomId = this.route.snapshot.paramMap.get('roomId');

    // Check query param payment_success để hiển thị message chúc mừng
    const paymentSuccess = this.route.snapshot.queryParamMap.get('payment_success');

    // Check query param mode=planning để mở trip planning mode
    const planningMode = this.route.snapshot.queryParamMap.get('mode');

    // Load conversations list trước, sau đó mới quyết định tạo mới hay load conversation cũ
    this.loadConversationsList(async () => {
      if (urlRoomId) {
        await this.loadRoomFromUrl(urlRoomId);
        // Sau khi load room, check payment_success và thêm message chúc mừng
        if (paymentSuccess === 'true') {
          setTimeout(() => {
            this.addPaymentSuccessMessage();
            // Remove query param để không hiển thị lại khi refresh
            this.router.navigate([], {
              relativeTo: this.route,
              queryParams: {},
              replaceUrl: true
            });
          }, 500);
        }
        return;
      }

      // If mode=planning, start a new trip planning conversation
      if (planningMode === 'planning') {
        this.startNewTripPlanning();
        // Clean up query param
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {},
          replaceUrl: true
        });
        return;
      }

      // Fallback: chọn conversation đầu tiên hoặc tạo mới
      if (this.conversations.length > 0) {
        const firstConversation = this.conversations[0];
        this.selectConversation(firstConversation.id);
        // Sau khi select conversation, check payment_success và thêm message chúc mừng
        if (paymentSuccess === 'true') {
          setTimeout(() => {
            this.addPaymentSuccessMessage();
            // Remove query param để không hiển thị lại khi refresh
            this.router.navigate([], {
              relativeTo: this.route,
              queryParams: {},
              replaceUrl: true
            });
          }, 500);
        }
      } else {
        this.startNewConversation();
        // Sau khi tạo conversation mới, check payment_success và thêm message chúc mừng
        if (paymentSuccess === 'true') {
          setTimeout(() => {
            this.addPaymentSuccessMessage();
            // Remove query param để không hiển thị lại khi refresh
            this.router.navigate([], {
              relativeTo: this.route,
              queryParams: {},
              replaceUrl: true
            });
          }, 500);
        }
      }
    });
  }

  onClose(): void {
    this.router.navigate(['/home'], { replaceUrl: true });
  }

  async sendMessage(): Promise<void> {
    if (!this.authStateService.getIsAuthenticated()) {
      this.onClose();
      this.router.navigate(['/login']);
      return;
    }

    if (this.isStreaming || !this.userMessage.trim()) return;

    const conversation = this.ensureActiveConversation();

    // Route to trip planning or general chat based on conversation type
    if (conversation.conversationType === 'trip_planning') {
      await this.sendTripPlanningMessage(conversation);
      return;
    }

    // === General Chat (existing logic) ===
    const message = this.userMessage.trim();

    // Nếu conversation chưa có room (chưa gửi message nào), tạo room trước
    if (!conversation.remoteConversationId) {
      try {
        await this.createRoomForConversation(conversation);
      } catch (e: any) {
        if (e?.status === 401) {
          this.authStateService.logout();
          this.router.navigate(['/login']);
        }
        return;
      }
    }

    if (conversation.remoteConversationId) {
      this.messagesCache.delete(conversation.remoteConversationId);
    }

    // Thêm user message vào UI
    const userMessageObj: Message = { content: message, isUser: true };
    this.messages.push(userMessageObj);
    this.userMessage = '';
    this.userHasScrolledUp = false; // Reset scroll state khi user gửi message mới

    this.touchConversation(conversation);
    if (!this.messages.some(m => !m.isUser)) {
      conversation.title = this.generateConversationTitle(message);
    }

    if (this.messageInputRef && this.messageInputRef.nativeElement) {
      this.messageInputRef.nativeElement.style.height = 'auto';
    }

    this.isStreaming = true;
    this.isTyping = true;
    this.headerStatus = 'Thinking...';
    this.conversationId = conversation.remoteConversationId;
    this.userId = conversation.userId;

    setTimeout(() => this.scrollToBottom(), 100);

    try {
      const reader = await this.chatService.sendMessage(message, this.conversationId, this.userId, 5);
      const decoder = new TextDecoder();
      let buffer = '';
      let assistantMessage: Message | null = null;
      let isFirstToken = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));

              switch (event.type) {
                case 'start':
                  this.conversationId = event.conversation_id;
                  this.userId = event.user_id;
                  conversation.remoteConversationId = event.conversation_id;
                  conversation.userId = event.user_id;
                  this.touchConversation(conversation);
                  console.log('Conversation started:', this.conversationId);
                  if (this.conversationId) {
                    this.router.navigate(['/chat-room', this.conversationId], { replaceUrl: true });
                  }
                  break;

                case 'token':
                  if (isFirstToken) {
                    this.isTyping = false;
                    assistantMessage = { content: '', isUser: false };
                    this.messages.push(assistantMessage);
                    this.currentStreamContent = '';
                    isFirstToken = false;
                  }
                  if (assistantMessage) {
                    this.currentStreamContent += event.content;
                    assistantMessage.content = this.currentStreamContent;

                    const tourSelections = this.extractTourSelections(this.currentStreamContent);
                    if (tourSelections.length > 0) {
                      assistantMessage.tourSelections = tourSelections;
                    }
                  }
                  this.touchConversation(conversation, false);
                  setTimeout(() => this.scrollToBottom(), 0);
                  break;

                case 'recommendations':
                  console.log('Recommendations received:', event.data);
                  if (!assistantMessage) {
                    this.isTyping = false;
                    assistantMessage = { content: '', isUser: false };
                    this.messages.push(assistantMessage);
                    isFirstToken = false;
                  }
                  this.applyTourPackagesToMessage(assistantMessage!, event.data);
                  this.touchConversation(conversation, false);
                  setTimeout(() => this.scrollToBottom(), 100);
                  break;

                case 'mcp_ui':
                  console.log('MCP UI received:', event);
                  if (!assistantMessage) {
                    this.isTyping = false;
                    assistantMessage = { content: '', isUser: false };
                    this.messages.push(assistantMessage);
                    isFirstToken = false;
                  }
                  if (assistantMessage) {
                    if (event.ui_resource) {
                      assistantMessage.mcpUiResource = event.ui_resource;
                    }
                    if (event.html) {
                      assistantMessage.mcpUiHtml = event.html;
                    }
                    if (event.tourPackages) {
                      this.applyTourPackagesToMessage(assistantMessage, event.tourPackages);
                    }
                    this.cdr.detectChanges();
                    this.touchConversation(conversation, false);

                    // Attach payment button click handlers after HTML is rendered (gọi nhiều lần để đảm bảo attach được)
                    setTimeout(() => {
                      this.attachPaymentButtonHandlers();
                    }, 50);
                    setTimeout(() => {
                      this.attachPaymentButtonHandlers();
                    }, 200);
                    setTimeout(() => {
                      this.attachPaymentButtonHandlers();
                    }, 500);
                  }
                  setTimeout(() => this.scrollToBottom(), 100);
                  break;

                case 'otp_required':
                  if (event.data) {
                    this.openOtpPopup(event.data);
                  }
                  break;

                case 'complete':
                  console.log('Complete:', event.full_response);
                  this.touchConversation(conversation);
                  break;

                case 'error':
                  if (isFirstToken) {
                    this.isTyping = false;
                    assistantMessage = { content: '', isUser: false, isError: true };
                    this.messages.push(assistantMessage);
                    this.currentStreamContent = '';
                    isFirstToken = false;
                  }
                  if (assistantMessage) {
                    this.currentStreamContent += '\n\n[ERROR]: ' + (event.error || event.content || 'Unknown error');
                    assistantMessage.content = this.currentStreamContent;
                    assistantMessage.isError = true;
                  }
                  this.touchConversation(conversation);
                  break;
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }

      if (assistantMessage) {
        await this.hydrateTourCardsForMessage(assistantMessage, message);
      }

      this.headerStatus = 'Online';
      this.touchConversation(conversation);
    } catch (error: any) {
      this.isTyping = false;
      let errorMessage = 'Unknown error occurred';

      if (error.message.includes('Failed to fetch')) {
        errorMessage = 'Cannot connect to backend API. Please check:<br><br>' +
          '1. Backend is running<br>' +
          '2. Backend has configured CORS<br>' +
          '3. API URL is configured correctly in config.json';
      } else {
        errorMessage = `Error: ${error.message}`;
      }

      const errorMsg: Message = {
        content: errorMessage,
        isUser: false,
        isError: true
      };
      this.messages.push(errorMsg);
      const conversation = this.ensureActiveConversation();
      this.touchConversation(conversation);
      this.headerStatus = 'Error';
      console.error('Chat error:', error);
    } finally {
      this.isStreaming = false;
      const activeRoomId = this.activeConversation?.remoteConversationId;
      if (activeRoomId) {
        this.messagesCache.set(activeRoomId, [...this.messages]);
      }
    }
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  onTextareaInput(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  }

  // ====================================================================
  // TRIP PLANNING METHODS
  // ====================================================================

  /**
   * Send a message in trip planning mode using TripPlannerService.
   */
  async sendTripPlanningMessage(conversation: Conversation): Promise<void> {
    const message = this.userMessage.trim();
    if (!message) return;

    // Create room if needed (same pattern as general chat)
    if (!conversation.remoteConversationId) {
      try {
        await this.createRoomForConversation(conversation);
      } catch (e: any) {
        if (e?.status === 401) {
          this.authStateService.logout();
          this.router.navigate(['/login']);
        }
        return;
      }
    }

    // Invalidate cache
    if (conversation.remoteConversationId) {
      this.messagesCache.delete(conversation.remoteConversationId);
    }

    // Add user message to UI
    const userMessageObj: Message = { content: message, isUser: true };
    this.messages.push(userMessageObj);
    this.userMessage = '';
    this.userHasScrolledUp = false;
    this.composerQuickSuggestions = [];

    if (this.messageInputRef && this.messageInputRef.nativeElement) {
      this.messageInputRef.nativeElement.style.height = 'auto';
    }

    this.touchConversation(conversation);
    if (!this.messages.some(m => !m.isUser)) {
      conversation.title = this.generateConversationTitle(message);
    }

    this.isStreaming = true;
    this.isTyping = true;
    this.headerStatus = 'Planning...';

    setTimeout(() => this.scrollToBottom(), 100);

    try {
      const roomId = conversation.remoteConversationId;
      this.tripConversationId = roomId;
      const reader = await this.tripPlannerService.sendMessage(
        message,
        roomId,
        roomId
      );

      let assistantMessage: Message | null = null;
      let isFirstToken = true;

      await this.tripPlannerService.parseStream(reader, (event: TripPlanStreamEvent) => {
        switch (event.type) {
          case 'start':
            this.tripConversationId = event.room_id || event.conversation_id || null;
            if (event.room_id && !conversation.remoteConversationId) {
              conversation.remoteConversationId = event.room_id;
              conversation.id = event.room_id;
              this.conversationId = event.room_id;
            }
            this.touchConversation(conversation);
            // Navigate to room URL
            if (conversation.remoteConversationId) {
              this.router.navigate(['/chat-room', conversation.remoteConversationId], { replaceUrl: true });
            }
            break;

          case 'token':
            if (isFirstToken) {
              this.isTyping = false;
              assistantMessage = { content: '', isUser: false };
              this.messages.push(assistantMessage);
              isFirstToken = false;
            }
            if (assistantMessage) {
              assistantMessage.content += event.content || '';
            }
            setTimeout(() => this.scrollToBottom(), 0);
            break;

          case 'step':
            this.applyTripStepEvent(event, assistantMessage);
            break;

          case 'activities':
            if (assistantMessage && event.data) {
              assistantMessage.itineraryData = event.data.suggested_itinerary || {};
              assistantMessage.availableActivities = event.data.available || [];
              assistantMessage.showItineraryBuilder = true;
              assistantMessage.tripTotalPrice = event.data.total_price || 0;
              assistantMessage.tripStep = 4;
              this.cdr.detectChanges();
            }
            setTimeout(() => this.scrollToBottom(), 100);
            break;

          case 'itinerary_confirmed':
            if (assistantMessage && event.data) {
              assistantMessage.tripTotalPrice = event.data.total_price || 0;
            }
            break;

          case 'flights':
            if (assistantMessage) {
              if (!assistantMessage.transportData) {
                assistantMessage.transportData = {};
              }
              assistantMessage.transportData.flights = event.data || [];
              assistantMessage.showTransport = true;
              this.cdr.detectChanges();
            }
            setTimeout(() => this.scrollToBottom(), 100);
            break;

          case 'trains':
            if (assistantMessage) {
              if (!assistantMessage.transportData) {
                assistantMessage.transportData = {};
              }
              assistantMessage.transportData.trains = event.data || [];
              assistantMessage.showTransport = true;
              this.cdr.detectChanges();
            }
            setTimeout(() => this.scrollToBottom(), 100);
            break;

          case 'checkout':
            if (assistantMessage && event.data) {
              assistantMessage.checkoutData = event.data;
              assistantMessage.showCheckout = true;
              assistantMessage.tripStep = 6;
              this.currentTripStep.set(6);
              if (event.data.booking_completed) {
                this.isTripComplete.set(true);
              }
              this.cdr.detectChanges();
            }
            setTimeout(() => this.scrollToBottom(), 100);
            break;

          case 'done':
            this.isStreaming = false;
            this.isTyping = false;
            this.headerStatus = 'Online';
            if (event.is_complete) {
              this.isTripComplete.set(true);
              this.composerQuickSuggestions = [];
            }
            this.touchConversation(conversation);
            break;

          case 'error':
            this.isStreaming = false;
            this.isTyping = false;
            this.headerStatus = 'Error';
            if (isFirstToken) {
              assistantMessage = { content: `❌ Lỗi: ${event.error || 'Không xác định'}`, isUser: false, isError: true };
              this.messages.push(assistantMessage);
              isFirstToken = false;
            } else if (assistantMessage) {
              assistantMessage.content += `\n\n❌ Lỗi: ${event.error || 'Không xác định'}`;
              assistantMessage.isError = true;
            }
            this.touchConversation(conversation);
            break;
        }
      });

      // Finalize
      this.headerStatus = 'Online';
      this.isStreaming = false;
      this.isTyping = false;
      this.refreshComposerQuickSuggestions();
      this.touchConversation(conversation);

      const activeRoomId = this.activeConversation?.remoteConversationId;
      if (activeRoomId) {
        this.messagesCache.set(activeRoomId, [...this.messages]);
      }
    } catch (error: any) {
      this.isStreaming = false;
      this.isTyping = false;
      const errorMsg: Message = {
        content: `❌ Lỗi kết nối: ${error.message}`,
        isUser: false,
        isError: true
      };
      this.messages.push(errorMsg);
      this.headerStatus = 'Error';
    }
  }

  /**
   * Confirm the itinerary and advance to next step.
   */
  confirmItinerary(msgIndex: number): void {
    const msg = this.messages[msgIndex];
    if (msg?.itineraryData) {
      void this.sendTripPlanningWithItinerary(msgIndex, 'xác nhận');
      return;
    }
    this.userMessage = 'xác nhận';
    void this.sendMessage();
  }

  toggleReplacePanel(msgIndex: number, dayKey: string, slot: string): void {
    const current = this.activeReplacePanel;
    if (
      current &&
      current.msgIndex === msgIndex &&
      current.dayKey === dayKey &&
      current.slot === slot
    ) {
      this.activeReplacePanel = null;
      return;
    }
    this.activeReplacePanel = { msgIndex, dayKey, slot };
  }

  isReplacePanelOpen(msgIndex: number, dayKey: string, slot: string): boolean {
    const panel = this.activeReplacePanel;
    return !!panel && panel.msgIndex === msgIndex && panel.dayKey === dayKey && panel.slot === slot;
  }

  getReplaceCandidates(msgIndex: number, dayKey: string, slot: string): ActivitySlot[] {
    const msg = this.messages[msgIndex];
    if (!msg?.availableActivities?.length) return [];

    const usedIds = new Set<string>();
    if (msg.itineraryData) {
      for (const day of Object.values(msg.itineraryData)) {
        for (const activity of [day.morning, day.afternoon, day.evening]) {
          if (activity?.activity_id) {
            usedIds.add(activity.activity_id);
          }
        }
      }
    }

    const currentActivity = msg.itineraryData?.[dayKey]?.[slot as keyof ItineraryDay] as ActivitySlot | null;

    return msg.availableActivities.filter((activity) => {
      if (currentActivity?.activity_id && activity.activity_id === currentActivity.activity_id) {
        return false;
      }
      return !usedIds.has(activity.activity_id);
    });
  }

  selectReplacement(msgIndex: number, dayKey: string, slot: string, activity: ActivitySlot): void {
    this.replaceActivity(msgIndex, dayKey, slot, activity);
    this.activeReplacePanel = null;
  }

  onActivityDragOver(event: DragEvent, dayKey: string, slot: string): void {
    event.preventDefault();
    this.dragOverSlot = { dayKey, slot };
  }

  onActivityDragLeave(dayKey: string, slot: string): void {
    if (
      this.dragOverSlot?.dayKey === dayKey &&
      this.dragOverSlot?.slot === slot
    ) {
      this.dragOverSlot = null;
    }
  }

  isDragOver(dayKey: string, slot: string): boolean {
    return this.dragOverSlot?.dayKey === dayKey && this.dragOverSlot?.slot === slot;
  }

  /**
   * Handle drag start for an activity slot.
   */
  onActivityDragStart(dayKey: string, slot: string, activity: ActivitySlot | null): void {
    this.draggedActivity = { dayKey, slot, activity };
  }

  /**
   * Handle drop on an activity slot — swap activities.
   */
  onActivityDrop(targetDayKey: string, targetSlot: string, msgIndex: number): void {
    if (!this.draggedActivity || !this.messages[msgIndex]) return;

    const msg = this.messages[msgIndex];
    if (!msg.itineraryData) return;

    const fromDay = this.draggedActivity.dayKey;
    const fromSlot = this.draggedActivity.slot;
    const fromActivity = this.draggedActivity.activity;

    // Get target activity
    const targetDay = msg.itineraryData[targetDayKey];
    if (!targetDay) return;

    const targetActivity = (targetDay as any)[targetSlot] as ActivitySlot | null;

    // Swap
    const itinerary = { ...msg.itineraryData };

    // Deep clone the affected days
    const fromDayData = { ...(itinerary[fromDay] || {}) };
    const toDayData = { ...(itinerary[targetDayKey] || {}) };

    (fromDayData as any)[fromSlot] = targetActivity;
    (toDayData as any)[targetSlot] = fromActivity;

    itinerary[fromDay] = fromDayData as ItineraryDay;
    itinerary[targetDayKey] = toDayData as ItineraryDay;

    msg.itineraryData = itinerary;

    // Recalculate price
    msg.tripTotalPrice = this.recalculateItineraryPrice(itinerary);

    this.draggedActivity = null;
    this.dragOverSlot = null;
    this.cdr.detectChanges();
  }

  /**
   * Replace an activity in a slot with another from the available pool.
   */
  replaceActivity(msgIndex: number, dayKey: string, slot: string, newActivity: ActivitySlot): void {
    const msg = this.messages[msgIndex];
    if (!msg.itineraryData) return;

    const itinerary = { ...msg.itineraryData };
    const dayData = { ...(itinerary[dayKey] || {}) };
    (dayData as any)[slot] = newActivity;
    itinerary[dayKey] = dayData as ItineraryDay;

    msg.itineraryData = itinerary;
    msg.tripTotalPrice = this.recalculateItineraryPrice(itinerary);
    this.cdr.detectChanges();
  }

  /**
   * Remove an activity from a slot.
   */
  removeActivity(msgIndex: number, dayKey: string, slot: string): void {
    const msg = this.messages[msgIndex];
    if (!msg.itineraryData) return;

    const itinerary = { ...msg.itineraryData };
    const dayData = { ...(itinerary[dayKey] || {}) };
    (dayData as any)[slot] = null;
    itinerary[dayKey] = dayData as ItineraryDay;

    msg.itineraryData = itinerary;
    msg.tripTotalPrice = this.recalculateItineraryPrice(itinerary);
    this.cdr.detectChanges();
  }

  /**
   * Send trip planning message with optional updated itinerary payload.
   */
  private async sendTripPlanningWithItinerary(
    msgIndex: number,
    messageText: string
  ): Promise<void> {
    const conversation = this.ensureActiveConversation();
    if (conversation.conversationType !== 'trip_planning') return;

    const msg = this.messages[msgIndex];
    if (!msg?.itineraryData) return;

    if (!conversation.remoteConversationId) {
      try {
        await this.createRoomForConversation(conversation);
      } catch (e: any) {
        if (e?.status === 401) {
          this.authStateService.logout();
          this.router.navigate(['/login']);
        }
        return;
      }
    }

    if (conversation.remoteConversationId) {
      this.messagesCache.delete(conversation.remoteConversationId);
    }

    this.messages.push({ content: messageText, isUser: true });
    this.userHasScrolledUp = false;
    this.isStreaming = true;
    this.isTyping = true;
    this.headerStatus = 'Updating...';

    setTimeout(() => this.scrollToBottom(), 100);

    try {
      const roomId = conversation.remoteConversationId;
      this.tripConversationId = roomId;
      const reader = await this.tripPlannerService.sendMessage(
        messageText,
        roomId,
        roomId,
        msg.itineraryData
      );

      let assistantMessage: Message | null = null;
      let isFirstToken = true;

      await this.tripPlannerService.parseStream(reader, (event: TripPlanStreamEvent) => {
        switch (event.type) {
          case 'start':
            this.tripConversationId = event.room_id || event.conversation_id || null;
            break;
          case 'token':
            if (isFirstToken) {
              this.isTyping = false;
              assistantMessage = { content: '', isUser: false };
              this.messages.push(assistantMessage);
              isFirstToken = false;
            }
            if (assistantMessage) {
              assistantMessage.content += event.content || '';
            }
            setTimeout(() => this.scrollToBottom(), 0);
            break;
          case 'step':
            this.applyTripStepEvent(event, assistantMessage);
            break;
          case 'itinerary_confirmed':
            if (assistantMessage && event.data) {
              assistantMessage.tripTotalPrice = event.data.total_price || 0;
            }
            break;
          case 'flights':
            if (assistantMessage) {
              if (!assistantMessage.transportData) assistantMessage.transportData = {};
              assistantMessage.transportData.flights = event.data || [];
              assistantMessage.showTransport = true;
              this.cdr.detectChanges();
            }
            break;
          case 'trains':
            if (assistantMessage) {
              if (!assistantMessage.transportData) assistantMessage.transportData = {};
              assistantMessage.transportData.trains = event.data || [];
              assistantMessage.showTransport = true;
              this.cdr.detectChanges();
            }
            break;
          case 'checkout':
            if (assistantMessage && event.data) {
              assistantMessage.checkoutData = event.data;
              assistantMessage.showCheckout = true;
              this.cdr.detectChanges();
            }
            break;
          case 'done':
            this.isStreaming = false;
            this.isTyping = false;
            this.headerStatus = 'Online';
            if (event.is_complete) this.isTripComplete.set(true);
            this.touchConversation(conversation);
            break;
          case 'error':
            this.isStreaming = false;
            this.isTyping = false;
            this.headerStatus = 'Error';
            break;
        }
      });

      this.isStreaming = false;
      this.isTyping = false;
      this.headerStatus = 'Online';
      this.touchConversation(conversation);

      const activeRoomId = this.activeConversation?.remoteConversationId;
      if (activeRoomId) {
        this.messagesCache.set(activeRoomId, [...this.messages]);
      }
    } catch {
      this.isStreaming = false;
      this.isTyping = false;
      this.headerStatus = 'Error';
    }
  }

  /**
   * Send the updated itinerary (after drag-drop/replace) to the backend.
   */
  async sendUpdatedItinerary(msgIndex: number): Promise<void> {
    await this.sendTripPlanningWithItinerary(msgIndex, 'Tôi đã sắp xếp lại lịch trình');
  }

  /**
   * Select a flight and send to backend.
   */
  selectFlightAndSend(flightIndex: number): void {
    this.userMessage = `${flightIndex + 1}`;
    this.sendMessage();
  }

  /**
   * Select a train and send to backend.
   */
  selectTrainAndSend(trainIndex: number, totalFlights: number): void {
    this.userMessage = `${totalFlights + trainIndex + 1}`;
    this.sendMessage();
  }

  /**
   * Skip transportation.
   */
  skipTransport(): void {
    this.userMessage = 'bỏ qua';
    this.sendMessage();
  }

  /**
   * Proceed to checkout — create booking then redirect to VNPay (same as My Bookings).
   */
  proceedToCheckout(): void {
    const checkoutMsg = [...this.messages].reverse().find(m => !m.isUser && m.showCheckout && m.checkoutData);
    const checkout = checkoutMsg?.checkoutData;

    if (checkout?.payment_url) {
      this.redirectToTripPayment(checkout.payment_url);
      return;
    }

    if (checkout?.booking_id) {
      this.paymentService.createPayment({
        booking_id: checkout.booking_id,
        payment_method: 'vnpay',
      }).subscribe({
        next: (response) => {
          if (response.EC === 0 && response.data?.payment_url) {
            if (checkoutMsg?.checkoutData) {
              checkoutMsg.checkoutData = {
                ...checkoutMsg.checkoutData,
                payment_url: response.data.payment_url,
                payment_id: response.data.payment_id,
              };
            }
            this.redirectToTripPayment(response.data.payment_url);
          }
        },
        error: () => {
          this.userMessage = 'thanh toán';
          void this.sendMessage();
        },
      });
      return;
    }

    this.userMessage = 'thanh toán';
    void this.sendMessage();
  }

  private redirectToTripPayment(paymentUrl: string): void {
    sessionStorage.setItem('payment_return_url', window.location.href);
    window.location.href = paymentUrl;
  }

  /**
   * Calculate total price from itinerary data.
   */
  recalculateItineraryPrice(itinerary: Record<string, ItineraryDay>): number {
    let total = 0;
    for (const dayKey of Object.keys(itinerary)) {
      const day = itinerary[dayKey];
      if (!day) continue;
      for (const slot of ['morning', 'afternoon', 'evening'] as const) {
        const activity = day[slot];
        if (activity && activity.price) {
          total += activity.price;
        }
      }
    }
    return total;
  }

  /**
   * Get itinerary days as array for iteration.
   */
  getItineraryDays(itinerary: Record<string, ItineraryDay>): { key: string; num: number; day: ItineraryDay }[] {
    const days: { key: string; num: number; day: ItineraryDay }[] = [];
    for (let i = 1; i <= 10; i++) {
      const key = `day_${i}`;
      if (itinerary[key]) {
        days.push({ key, num: i, day: itinerary[key] });
      }
    }
    return days;
  }

  /**
   * Get the conversation type of the active conversation.
   */
  getActiveConversationType(): 'general_chat' | 'trip_planning' {
    return this.activeConversation?.conversationType || 'general_chat';
  }

  /**
   * Check if active conversation is trip planning mode.
   */
  isTripPlanningMode(): boolean {
    return this.getActiveConversationType() === 'trip_planning';
  }

  get messagePlaceholder(): string {
    if (this.isTripPlanningMode()) {
      return 'Cho mình biết bạn muốn đi đâu và trong bao lâu...';
    }
    return 'Đặt câu hỏi về hành trình, điểm đến hay các ưu đãi du lịch...';
  }

  applyQuickReply(text: string): void {
    if (this.isStreaming || !text.trim()) return;
    this.userMessage = text.trim();
    void this.sendMessage();
  }

  getVisibleQuickSuggestions(): string[] {
    const lastMsg = this.messages[this.messages.length - 1];
    if (lastMsg && !lastMsg.isUser && lastMsg.quickSuggestions?.length) {
      return lastMsg.quickSuggestions;
    }
    return this.composerQuickSuggestions;
  }

  private refreshComposerQuickSuggestions(): void {
    const lastMsg = this.messages[this.messages.length - 1];
    if (lastMsg && !lastMsg.isUser && lastMsg.quickSuggestions?.length) {
      this.composerQuickSuggestions = [...lastMsg.quickSuggestions];
      return;
    }
    this.composerQuickSuggestions = [];
  }

  private applyTripStepEvent(event: TripPlanStreamEvent, assistantMessage: Message | null): void {
    if (event.step) {
      this.currentTripStep.set(event.step);
    }
    const waiting = event.waiting_for_input !== false;
    const suggestions = waiting && event.suggestions?.length ? [...event.suggestions] : [];
    if (assistantMessage) {
      assistantMessage.tripStep = event.step;
      assistantMessage.quickSuggestions = suggestions;
    }
    this.composerQuickSuggestions = suggestions;
    this.cdr.detectChanges();
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  formatMessageContent(content: string): string {
    if (!content) return '';
    const normalized = content.replace(/[—–]/g, ' - ');

    let html = this.parseMarkdown(normalized);
    // Convert URLs to clickable square buttons inside the bubble
    html = html.replace(/(https?:\/\/[^\s<]+)/gim, (url) => {
      return `<a class="source-button" href="${url}" target="_blank" rel="noopener noreferrer" title="${url}"><span>Nguồn</span></a>`;
    });

    return html;
  }

  private truncateUrl(url: string, maxLength: number): string {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
  }

  private getDomainFromUrl(url: string): string {
    try {
      const parsed = new URL(url);
      return parsed.hostname.replace(/^www\./, '');
    } catch {
      return 'Nguồn';
    }
  }

  startNewConversation(): void {
    if (this.isStreaming) return;

    const conversation: Conversation = {
      id: this.generateId(),
      title: 'Cuộc trò chuyện mới',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      remoteConversationId: null,
      userId: null,
      conversationType: 'general_chat'
    };

    this.conversations = [conversation, ...this.conversations];
    this.selectConversation(conversation.id);
  }

  /**
   * Start a new trip planning conversation.
   */
  startNewTripPlanning(): void {
    if (this.isStreaming) return;

    const conversation: Conversation = {
      id: this.generateId(),
      title: 'Lập kế hoạch du lịch',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      remoteConversationId: null,
      userId: null,
      conversationType: 'trip_planning'
    };

    this.conversations = [conversation, ...this.conversations];
    this.selectConversation(conversation.id);

    // Reset trip planning state
    this.currentTripStep.set(1);
    this.isTripComplete.set(false);
    this.tripConversationId = null;

    // Add welcome message
    const welcomeMsg: Message = {
      content: 'Xin chào! Tôi là trợ lý lên kế hoạch du lịch.\n\nBạn muốn đi đâu và bao lâu? Chọn gợi ý bên dưới hoặc gõ tự do:',
      isUser: false,
      tripStep: 1,
      quickSuggestions: [
        'Đà Lạt 3 ngày',
        'Hội An 2 ngày',
        'Nha Trang 4 ngày',
        'Đà Nẵng 3 ngày',
        'Phú Quốc 3 ngày',
      ],
    };
    this.messages.push(welcomeMsg);
    this.composerQuickSuggestions = welcomeMsg.quickSuggestions || [];
    this.cdr.detectChanges();
  }

  selectConversation(conversationId: string): void {
    if (this.isStreaming && this.activeConversation?.id !== conversationId) return;

    const conversation = this.conversations.find(conv => conv.id === conversationId);
    if (!conversation) return;

    this.activeConversation = conversation;
    this.conversationId = conversation.remoteConversationId;
    this.userId = conversation.userId;
    this.isTyping = false;
    this.isStreaming = false;
    this.currentStreamContent = '';
    this.userHasScrolledUp = false;
    this.activeReplacePanel = null;
    this.dragOverSlot = null;
    this.draggedActivity = null;
    this.composerQuickSuggestions = [];

    if (conversation.conversationType === 'trip_planning') {
      this.tripConversationId = conversation.remoteConversationId;
      this.isTripComplete.set(false);
    } else {
      this.currentTripStep.set(1);
      this.isTripComplete.set(false);
      this.tripConversationId = null;
    }

    // Navigate to the chat room URL
    this.router.navigate(['/chat-room', conversation.remoteConversationId || conversation.id]);

    // Clear messages và load từ API
    const roomId = conversation.remoteConversationId || conversation.id;
    const cachedMessages = roomId ? this.messagesCache.get(roomId) : null;
    if (cachedMessages) {
      this.messages = [...cachedMessages];
    } else {
      this.messages = [];
    }
    this.cdr.detectChanges();

    // Load messages từ API nếu có remoteConversationId
    if (conversation.remoteConversationId) {
      this.loadMessagesFromAPI(conversation.remoteConversationId);
    }
  }

  /**
   * Tạo room cho conversation khi user gửi message đầu tiên
   */
  private async createRoomForConversation(conversation: Conversation): Promise<void> {
    return new Promise((resolve, reject) => {
      const defaultTitle = conversation.conversationType === 'trip_planning'
        ? 'Lập kế hoạch du lịch'
        : 'New conversation';

      this.chatRoomService.createRoom(defaultTitle).subscribe({
        next: (response) => {
          if (response.EC === 0 && response.data) {
            const room = response.data;

            // Update conversation với room_id từ API
            conversation.id = room.room_id;
            conversation.remoteConversationId = room.room_id;
            conversation.userId = room.user_id;
            conversation.createdAt = new Date(room.created_at).getTime();
            conversation.updatedAt = new Date(room.updated_at).getTime();

            if (conversation.conversationType === 'trip_planning' && !room.title?.startsWith('🗺️')) {
              conversation.title = room.title?.startsWith('🗺️') ? room.title : `🗺️ ${room.title}`;
            } else {
              conversation.title = room.title || conversation.title;
            }

            // Update conversationId và userId để dùng cho chat
            this.conversationId = room.room_id;
            this.userId = room.user_id;

            if (conversation.conversationType === 'trip_planning') {
              this.tripConversationId = room.room_id;
            }

            resolve();
          } else {
            console.error('Failed to create room:', response.EM);
            reject(new Error(response.EM));
          }
        },
        error: (error) => {
          console.error('Error creating room from API:', error);
          if (error?.status === 401) {
            this.authStateService.logout();
            this.router.navigate(['/login']);
          }
          reject(error);
        }
      });
    });
  }

  /**
   * Load danh sách conversations từ API để hiển thị sidebar
   * @param callback Function được gọi sau khi load xong conversations
   */
  loadConversationsList(callback?: () => void): void {
    let callbackCalled = false;

    // Load từ cache để hiển thị ngay
    const cached = this.loadConversationsFromCache();
    if (cached && cached.length > 0) {
      this.conversations = cached.sort((a, b) => b.updatedAt - a.updatedAt);
      if (callback) {
        callback();
        callbackCalled = true;
      }
    }

    this.isLoadingConversations = true;

    this.chatRoomService.getRooms(false, 50, 0).subscribe({
      next: (response) => {
        if (response.EC === 0 && response.data) {
          const apiConversations = response.data.map((room: any) => ({
            id: room.room_id,
            title: room.title,
            createdAt: new Date(room.created_at).getTime(),
            updatedAt: new Date(room.updated_at).getTime(),
            remoteConversationId: room.room_id,
            userId: room.user_id,
            conversationType: room.title?.startsWith('🗺️') ? 'trip_planning' as const : 'general_chat' as const
          }));

          this.conversations = apiConversations.sort((a, b) => b.updatedAt - a.updatedAt);
          this.saveConversationsToCache(this.conversations);
        } else {
          this.conversations = [];
        }

        if (!callbackCalled && callback) {
          callback();
        }
      },
      error: (error) => {
        console.error('Error loading conversations list:', error);
        if (error?.status === 401) {
          this.authStateService.logout();
          this.router.navigate(['/login']);
          return;
        }
        // Keep cache if available; only clear if none
        if (!cached || cached.length === 0) {
          this.conversations = [];
        }

        if (!callbackCalled && callback) {
          callback();
        }
        this.isLoadingConversations = false;
      },
      complete: () => {
        this.isLoadingConversations = false;
      }
    });
  }

  /**
   * Load room theo roomId trong URL (nếu tồn tại), select và load messages
   */
  private async loadRoomFromUrl(roomId: string): Promise<void> {
    const existing = this.conversations.find(c => c.id === roomId || c.remoteConversationId === roomId);
    if (existing) {
      this.selectConversation(existing.id);
      return;
    }
    try {
      const roomResp = await this.chatRoomService.getRoom(roomId).toPromise();
      if (roomResp && roomResp.EC === 0 && roomResp.data) {
        const room = roomResp.data;
        const conv: Conversation = {
          id: room.room_id,
          title: room.title,
          createdAt: new Date(room.created_at).getTime(),
          updatedAt: new Date(room.updated_at).getTime(),
          remoteConversationId: room.room_id,
          userId: room.user_id,
          conversationType: room.title?.startsWith('🗺️') ? 'trip_planning' : 'general_chat',
        };
        this.conversations.unshift(conv);
        this.selectConversation(conv.id);
        return;
      }
    } catch (e) {
      console.warn('Could not load room from URL, fallback to default conversation', e);
    }
    // fallback
    this.startNewConversation();
  }

  /**
   * Load messages from API for a room (chỉ load nếu chưa có cache)
   */
  loadMessagesFromAPI(roomId: string): void {
    // Chỉ load nếu đây là conversation đang active (tránh race condition)
    if (this.activeConversation?.remoteConversationId !== roomId) {
      return;
    }
    this.isLoadingMessages = true;

    this.chatRoomService.getRoomMessages(roomId, 100, 0).subscribe({
      next: (response) => {
        // Double check conversation vẫn active sau khi response về
        if (this.activeConversation?.remoteConversationId !== roomId) {
          return;
        }

        if (response.EC === 0 && response.data) {
          // Convert API messages to local message format
          const loadedMessages = response.data.map((msg: any) => {
            const tourPackages = msg.entities?.tour_packages || [];
            // Parse content - backend may store as JSON array like [{"type":"text","text":"..."}]
            const parsedContent = this.parseMessageContent(msg.content);

            const messageObj: Message = {
              content: parsedContent,
              isUser: msg.role === 'user',
              tourPackages: tourPackages,
              showTourCards: tourPackages.length > 0,
              mcpUiResource: msg.entities?.mcp_ui_resource,
              mcpUiHtml: msg.entities?.mcp_ui_html
            };

            // Restore trip planning data from entities
            if (msg.entities?.trip_planning) {
              messageObj.tripStep = msg.entities.step;
              if (msg.entities.itinerary_data) {
                messageObj.itineraryData = msg.entities.itinerary_data;
                messageObj.showItineraryBuilder = true;
              }
              if (msg.entities.available_activities) {
                messageObj.availableActivities = msg.entities.available_activities;
              }
              if (msg.entities.total_price !== undefined) {
                messageObj.tripTotalPrice = msg.entities.total_price;
              }
              if (msg.entities.flights || msg.entities.trains) {
                messageObj.transportData = {
                  flights: msg.entities.flights || [],
                  trains: msg.entities.trains || []
                };
                messageObj.showTransport = !!(msg.entities.flights?.length || msg.entities.trains?.length);
              }
              if (msg.entities.checkout_data) {
                messageObj.checkoutData = msg.entities.checkout_data;
                messageObj.showCheckout = true;
              }
              if (msg.entities.suggestions?.length) {
                messageObj.quickSuggestions = msg.entities.suggestions;
              }
            }

            return messageObj;
          });

          // Update messages
          this.messages = loadedMessages;
          this.messagesCache.set(roomId, [...loadedMessages]);
          this.rebuildLastRecommendedTours(loadedMessages);

          // Restore trip planning state from loaded messages
          this.restoreTripPlanningFromHistory(loadedMessages);

          // Trigger change detection và scroll
          this.cdr.detectChanges();
          setTimeout(() => this.scrollToBottom(), 100);
        }
      },
      error: (error) => {
        console.error('Error loading messages from API:', error);
        this.isLoadingMessages = false;
      },
      complete: () => {
        this.isLoadingMessages = false;
      }
    });
  }

  deleteConversation(conversationId: string): void {
    if (this.isStreaming || this.isDeletingConversation) return;

    const conversation = this.conversations.find(conv => conv.id === conversationId);
    if (!conversation) return;

    const wasActive = this.activeConversation?.id === conversationId;
    const index = this.conversations.findIndex(conv => conv.id === conversationId);

    // Optimistic remove
    this.isDeletingConversation = conversationId;
    const deletedConversation = this.conversations.splice(index, 1)[0];
    // Invalidate cache for this room
    if (deletedConversation.remoteConversationId) {
      this.messagesCache.delete(deletedConversation.remoteConversationId);
    }

    if (!this.conversations.length) {
      this.startNewConversation();
    } else if (wasActive) {
      const nextConversation = this.conversations[Math.min(index, this.conversations.length - 1)];
      this.selectConversation(nextConversation.id);
    }

    const finalize = () => {
      this.saveConversationsToCache(this.conversations);
      this.isDeletingConversation = null;
    };

    // Gọi API delete room nếu có remoteConversationId
    if (deletedConversation.remoteConversationId) {
      this.chatRoomService.deleteRoom(deletedConversation.remoteConversationId).subscribe({
        next: (response) => {
          if (response.EC !== 0) {
            console.error('Failed to delete room:', response.EM);
            // Rollback
            this.conversations.splice(index, 0, deletedConversation);
            this.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
          }
        },
        error: (error) => {
          console.error('Error deleting room:', error);
          // Rollback
          this.conversations.splice(index, 0, deletedConversation);
          this.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
        },
        complete: finalize
      });
    } else {
      finalize();
    }
  }

  formatTimestamp(timestamp: number): string {
    if (!timestamp) return '';
    try {
      return new Intl.DateTimeFormat('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: '2-digit'
      }).format(timestamp);
    } catch (error) {
      console.warn('Timestamp format error:', error);
      return new Date(timestamp).toLocaleString();
    }
  }

  getConversationPreview(conversation: Conversation): string {
    // Không có cache messages nữa, chỉ hiển thị title
    return conversation.title || 'Cuộc trò chuyện';
  }

  /**
   * Parse message content from backend format
   * Backend may store content as JSON array like [{"type":"text","text":"..."}]
   */
  private parseMessageContent(content: string): string {
    if (!content) return '';

    // Try to parse as JSON array
    try {
      // Check if content looks like JSON array
      const trimmed = content.trim();
      if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) {
          // Extract text from content blocks
          const textParts = parsed
            .filter((block: any) => block.type === 'text' && block.text)
            .map((block: any) => block.text);
          if (textParts.length > 0) {
            return textParts.join('\n');
          }
        }
      }
    } catch (e) {
      // Not JSON, return as-is
    }

    return content;
  }

  private parseMarkdown(text: string): string {
    if (!text) return '';

    // Remove heading markers (##, ###) to avoid cluttering UI
    const stripped = text.replace(/^#{1,3}\s*/gm, '');

    // Replace long dashes with short dash for cleaner UI
    const dashCleaned = stripped.replace(/[—–]/g, '-');

    // Escape basic HTML
    const escaped = dashCleaned
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Bold
    const bolded = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Split by paragraph (double newline)
    const paragraphs = bolded.split(/\n\n+/);

    const htmlSegments = paragraphs.map((segment) => {
      const lines = segment.split(/\n/).map((l) => l.trim()).filter(Boolean);
      if (!lines.length) return '';

      // Bullet list
      const isDashList = lines.every((l) => /^- /.test(l));
      const isNumList = lines.every((l) => /^\d+\.\s+/.test(l));

      if (isDashList) {
        const items = lines.map((l) => l.replace(/^- /, '')).map((item) => `<li>${item}</li>`).join('');
        return `<ul>${items}</ul>`;
      }

      if (isNumList) {
        const items = lines.map((l) => l.replace(/^\d+\.\s+/, '')).map((item) => `<li>${item}</li>`).join('');
        return `<ol>${items}</ol>`;
      }

      // Default paragraph with line breaks
      return lines.join('<br>');
    }).filter(Boolean);

    return htmlSegments.join('<br><br>');
  }

  extractTourSelections(content: string): TourSelection[] {
    const patterns = [
      /<div class="list-item">.*?<strong>([^<]+)<\/strong>.*?(\d{1,3}(?:,\d{3})*)\s*VNĐ.*?<\/div>/gs,
      /<strong>([^<]+)<\/strong>.*?(\d{1,3}(?:,\d{3})*)\s*VNĐ/gs,
      /\*\*([^*]+)\*\*.*?(\d{1,3}(?:,\d{3})*)\s*VNĐ/gs
    ];

    const selections: TourSelection[] = [];

    for (const pattern of patterns) {
      const matches = [...content.matchAll(pattern)];
      if (matches.length > 0) {
        matches.forEach((match, index) => {
          const tourName = match[1].trim();
          const priceStr = match[2].replace(/,/g, '');
          const price = parseInt(priceStr);

          if (tourName && !isNaN(price)) {
            selections.push({
              name: tourName,
              price: price,
              index: index
            });
          }
        });
        break;
      }
    }

    return selections;
  }

  private applyTourPackagesToMessage(message: Message, data: unknown): void {
    const packages = this.normalizeTourPackages(data);
    if (!packages.length) {
      return;
    }

    message.tourPackages = packages;
    message.tours = packages;
    message.showTourCards = true;
    this.rememberRecommendedTours(packages);
    this.cdr.detectChanges();
  }

  private normalizeTourPackages(data: unknown): Tour[] {
    if (!Array.isArray(data) || data.length === 0) {
      return [];
    }

    if (typeof data[0] === 'string') {
      return data
        .map((id) => this.lastRecommendedTours.find((tour) => tour.package_id === id))
        .filter((tour): tour is Tour => !!tour);
    }

    return (data as Tour[]).filter((tour) => !!tour?.package_id || !!tour?.package_name);
  }

  private rememberRecommendedTours(packages: Tour[]): void {
    const merged = new Map<string, Tour>();
    for (const tour of [...this.lastRecommendedTours, ...packages]) {
      const key = tour.package_id || tour.package_name;
      if (key) {
        merged.set(key, tour);
      }
    }
    this.lastRecommendedTours = Array.from(merged.values());
  }

  private rebuildLastRecommendedTours(messages: Message[]): void {
    const merged = new Map<string, Tour>();
    for (const message of messages) {
      for (const tour of message.tourPackages || []) {
        const key = tour.package_id || tour.package_name;
        if (key) {
          merged.set(key, tour);
        }
      }
    }
    this.lastRecommendedTours = Array.from(merged.values());
  }

  private matchToursByNames(names: string[], source: Tour[]): Tour[] {
    const normalizedNames = names.map((name) => name.toLowerCase().trim()).filter(Boolean);
    if (!normalizedNames.length || !source.length) {
      return [];
    }

    const matched: Tour[] = [];
    for (const tour of source) {
      const tourName = (tour.package_name || '').toLowerCase().trim();
      if (!tourName) {
        continue;
      }

      const isMatch = normalizedNames.some((name) =>
        tourName === name ||
        tourName.includes(name) ||
        name.includes(tourName)
      );

      if (isMatch) {
        matched.push(tour);
      }
    }

    return matched;
  }

  private matchToursFromUserText(text: string, source: Tour[]): Tour[] {
    const normalizedText = text.toLowerCase();
    const selectionHints = ['chọn', 'chon', 'đặt tour', 'dat tour', 'muốn đặt', 'muon dat', 'book tour', 'tour này', 'tour nay'];
    const looksLikeSelection = selectionHints.some((hint) => normalizedText.includes(hint));

    if (!looksLikeSelection || !source.length) {
      return [];
    }

    const matched = source.filter((tour) => {
      const tourName = (tour.package_name || '').toLowerCase().trim();
      return tourName.length > 0 && normalizedText.includes(tourName);
    });

    return matched.slice(0, 1);
  }

  private async resolveToursByNames(names: string[]): Promise<Tour[]> {
    const fromCache = this.matchToursByNames(names, this.lastRecommendedTours);
    if (fromCache.length) {
      return fromCache;
    }

    for (const message of [...this.messages].reverse()) {
      const fromHistory = this.matchToursByNames(names, message.tourPackages || []);
      if (fromHistory.length) {
        return fromHistory;
      }
    }

    try {
      const allTours = await this.tourService.getTours();
      const matched = this.matchToursByNames(names, allTours);
      if (matched.length) {
        return matched;
      }
    } catch (error) {
      console.warn('Could not resolve tours by name:', error);
    }

    return [];
  }

  private async hydrateTourCardsForMessage(message: Message, userMessage?: string): Promise<void> {
    if (message.showTourCards && message.tourPackages?.length) {
      return;
    }

    if (message.tourSelections?.length) {
      const resolved = await this.resolveToursByNames(message.tourSelections.map((item) => item.name));
      if (resolved.length) {
        this.applyTourPackagesToMessage(message, resolved);
        return;
      }
    }

    if (userMessage) {
      const selected = this.matchToursFromUserText(userMessage, this.lastRecommendedTours);
      if (selected.length) {
        this.applyTourPackagesToMessage(message, selected);
        return;
      }

      const quotedMatch = userMessage.match(/"([^"]+)"/);
      if (quotedMatch?.[1]) {
        const resolved = await this.resolveToursByNames([quotedMatch[1]]);
        if (resolved.length) {
          this.applyTourPackagesToMessage(message, resolved);
        }
      }
    }
  }

  selectTour(tourName: string, price: string): void {
    if (this.isStreaming) {
      return;
    }

    this.userMessage = `Tôi muốn đặt tour "${tourName}" với giá ${this.formatPrice(parseInt(price.replace(/,/g, '')))}`;
    void this.sendMessage();
  }

  async viewTourDetails(tourName: string): Promise<void> {
    try {
      console.log('Searching for tour:', tourName);

      const normalizedSearchName = tourName.toLowerCase().trim();
      let foundTour = null;

      // Tìm trong recommended tours trước
      try {
        const recommendedTours = await this.tourService.getRecommendedTours(100);
        console.log('Available recommended tours:', recommendedTours.map(t => t.package_name));

        foundTour = recommendedTours.find(tour => {
          const normalizedTourName = tour.package_name.toLowerCase().trim();
          return normalizedTourName === normalizedSearchName ||
            normalizedTourName.includes(normalizedSearchName) ||
            normalizedSearchName.includes(normalizedTourName);
        });
      } catch (error) {
        console.log('Error loading recommended tours:', error);
      }

      // Nếu không tìm thấy trong recommended tours, tìm trong tất cả tours
      if (!foundTour) {
        try {
          const allTours = await this.tourService.getTours();
          console.log('Available all tours:', allTours.map(t => t.package_name));

          foundTour = allTours.find(tour => {
            const normalizedTourName = tour.package_name.toLowerCase().trim();
            return normalizedTourName === normalizedSearchName ||
              normalizedTourName.includes(normalizedSearchName) ||
              normalizedSearchName.includes(normalizedTourName);
          });
        } catch (error) {
          console.log('Error loading all tours:', error);
        }
      }

      if (foundTour && foundTour.package_id) {
        console.log('Found tour:', foundTour.package_name, 'ID:', foundTour.package_id);
        this.onClose();
        this.router.navigate(['/tour-details', foundTour.package_id]);
      } else {
        console.warn('Tour not found, redirecting to tours list');
        this.onClose();
        this.router.navigate(['/tours']);
      }
    } catch (error) {
      console.error('Error finding tour:', error);
      this.onClose();
      this.router.navigate(['/tours']);
    }
  }

  navigateToTourDetail(tourId: string): void {
    console.log('Navigating to tour detail:', tourId);
    console.log('Tour ID type:', typeof tourId);
    console.log('Tour ID value:', tourId);

    if (!tourId) {
      console.error('Tour ID is undefined or null');
      return;
    }

    // Navigate directly to tour details, replacing the chat route
    this.router.navigate(['/tour-details', tourId], { replaceUrl: true });
  }


  private scrollToBottom(): void {
    if (this.userHasScrolledUp) return; // Không scroll nếu user đã kéo lên
    if (this.messagesContainer) {
      const element = this.messagesContainer.nativeElement;
      element.scrollTop = element.scrollHeight;
    }
  }

  onMessagesScroll(): void {
    const el = this.messagesContainer?.nativeElement;
    if (!el) return;
    // User ở gần cuối (trong 100px) thì cho auto-scroll
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    this.userHasScrolledUp = !isNearBottom;
  }


  private ensureActiveConversation(): Conversation {
    if (!this.activeConversation) {
      this.startNewConversation();
    }
    return this.activeConversation!;
  }

  /**
   * Load messages from chat history — restore trip planning data from entities.
   */
  private restoreTripPlanningFromHistory(messages: Message[]): void {
    let latestStep = 1;
    let hasCheckout = false;

    for (const msg of messages) {
      if (!msg.isUser && msg.tripStep) {
        latestStep = msg.tripStep;
      }
      if (!msg.isUser && msg.showCheckout) {
        hasCheckout = true;
      }
    }

    this.currentTripStep.set(latestStep);
    this.isTripComplete.set(
      messages.some(m => !m.isUser && m.checkoutData?.booking_completed)
    );

    if (this.activeConversation?.conversationType === 'trip_planning') {
      this.tripConversationId = this.activeConversation.remoteConversationId;
    }

    const lastAssistant = [...messages].reverse().find(m => !m.isUser && m.quickSuggestions?.length);
    this.composerQuickSuggestions = lastAssistant?.quickSuggestions || [];
  }

  private generateConversationTitle(message: string): string {
    const cleaned = message.replace(/\s+/g, ' ').trim();
    if (!cleaned) {
      return 'Cuộc trò chuyện mới';
    }
    return cleaned.length > 40 ? `${cleaned.slice(0, 37)}…` : cleaned;
  }

  private generateId(): string {
    try {
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
      }
    } catch (error) {
      console.warn('crypto.randomUUID unavailable:', error);
    }
    return Math.random().toString(36).slice(2, 11);
  }

  private getCurrentUserId(): string | null {
    const user = this.authStateService.getCurrentUser();
    if (user && user.user_id) return user.user_id;
    if (this.userId) return this.userId;
    return null;
  }

  private loadConversationsFromCache(): Conversation[] {
    if (typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem(this.conversationsCacheKey);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      const userId = this.getCurrentUserId();
      if (!userId || parsed.userId !== userId) return [];
      const timestamp = parsed.timestamp || 0;
      if (Date.now() - timestamp > this.conversationsCacheTTL) return [];
      const conversations = parsed.conversations as Conversation[] || [];
      return conversations.map((conversation) => ({
        ...conversation,
        conversationType: conversation.conversationType
          || (conversation.title?.startsWith('🗺️') ? 'trip_planning' : 'general_chat'),
      }));
    } catch (e) {
      console.warn('Failed to load conversations cache', e);
      return [];
    }
  }

  private saveConversationsToCache(conversations: Conversation[]): void {
    if (typeof window === 'undefined') return;
    const userId = this.getCurrentUserId();
    if (!userId) return;
    try {
      const payload = {
        conversations,
        timestamp: Date.now(),
        userId
      };
      localStorage.setItem(this.conversationsCacheKey, JSON.stringify(payload));
    } catch (e) {
      console.warn('Failed to save conversations cache', e);
    }
  }

  private touchConversation(conversation: Conversation, bump: boolean = true): void {
    conversation.updatedAt = Date.now();
    if (!bump) {
      return;
    }

    // Move conversation to top và sort lại
    const index = this.conversations.findIndex(conv => conv.id === conversation.id);
    if (index > 0) {
      this.conversations.splice(index, 1);
      this.conversations.unshift(conversation);
    } else if (index === -1) {
      // Nếu không tìm thấy, thêm vào đầu
      this.conversations.unshift(conversation);
    }

    // Đảm bảo sort by updatedAt descending (mới nhất lên đầu)
    this.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
  }

  sanitizeHtml(html: string): SafeHtml {
    if (!html) return '';
    // Bypass security for payment button HTML to allow onclick handlers
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  ngOnDestroy(): void {
    // Clean up event listeners
    window.removeEventListener('message', this.paymentButtonClickHandler);
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
        this.otpSuccess = '';
        this.messages.push({
          content: 'Xác thực OTP thành công! Đặt tour của bạn đã được xác nhận. Bạn có thể tiếp tục thanh toán.',
          isUser: false,
        });
        this.cdr.detectChanges();
        setTimeout(() => this.scrollToBottom(), 100);
      } else {
        this.otpError = response.EM || 'Mã OTP không đúng';
      }
    } catch (error: any) {
      this.otpError = error?.error?.detail || error?.error?.EM || 'Xác thực OTP thất bại';
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
    } catch (error: any) {
      this.otpError = error?.error?.detail || 'Không thể gửi lại OTP';
    } finally {
      this.isResendingOTP = false;
    }
  }

  /**
   * Thêm message chúc mừng thanh toán thành công vào chat
   */
  private addPaymentSuccessMessage(): void {
    const successMessage: Message = {
      content: `🎉 **Chúc mừng bạn đã thanh toán thành công!**

Cảm ơn bạn đã tin tưởng và sử dụng dịch vụ của chúng tôi. Đơn hàng của bạn đã được xác nhận và đang được xử lý.

**Những điều bạn cần biết:**
- Đơn hàng sẽ được xử lý trong vòng 24 giờ
- Bạn sẽ nhận được email xác nhận đơn hàng trong thời gian sớm nhất
- Bạn có thể xem chi tiết đơn hàng trong mục "Đơn hàng của tôi"

Nếu bạn có bất kỳ câu hỏi nào về đơn hàng hoặc cần hỗ trợ thêm, đừng ngần ngại hỏi tôi nhé! 😊`,
      isUser: false
    };

    this.messages.push(successMessage);
    this.cdr.detectChanges();

    // Scroll xuống để hiển thị message mới
    setTimeout(() => {
      this.scrollToBottom();
    }, 100);
  }

  // Handle payment button clicks from dynamically rendered HTML
  handlePaymentClick(paymentUrl: string, bookingId: string): void {
    console.log('Payment button clicked:', { paymentUrl, bookingId });
    if (paymentUrl) {
      // Lưu chat room URL vào sessionStorage để redirect về sau khi thanh toán
      const currentUrl = window.location.href;
      sessionStorage.setItem('payment_return_url', currentUrl);
      // KHÔNG modify payment URL - giữ nguyên như backend generate
      window.location.href = paymentUrl;
    }
  }

  // Handle clicks on payment button HTML (delegation)
  handlePaymentClickFromHtml(event: MouseEvent): void {
    const target = event.target as HTMLElement;

    // Check if clicked element is payment button or inside it
    const button = target.closest('.mcp-payment-button') || target.closest('button[data-payment-url]');

    if (button) {
      event.preventDefault();
      event.stopPropagation();

      // Prevent multiple clicks
      if (this.isProcessingPayment || button.hasAttribute('disabled')) {
        return;
      }

      // Đánh dấu loading
      this.isProcessingPayment = true;
      button.setAttribute('disabled', 'true');
      button.classList.add('loading');

      // Try data attributes first (preferred method)
      const paymentUrl = button.getAttribute('data-payment-url') ||
        (button as HTMLElement).dataset['paymentUrl'];
      if (paymentUrl) {
        console.log('Extracted payment URL from data attribute:', paymentUrl);
        // Lưu chat room URL vào sessionStorage để redirect về sau khi thanh toán
        const currentUrl = window.location.href;
        sessionStorage.setItem('payment_return_url', currentUrl);
        // KHÔNG modify payment URL - giữ nguyên như backend generate
        window.location.href = paymentUrl;
        return;
      }

      // Fallback: try onclick attribute
      const onclickAttr = button.getAttribute('onclick');
      if (onclickAttr) {
        // Extract payment URL from onclick="handlePayment('url', 'id')"
        const urlMatch = onclickAttr.match(/handlePayment\(['"]([^'"]+)['"]/);
        if (urlMatch && urlMatch[1]) {
          const paymentUrl = urlMatch[1];
          console.log('Extracted payment URL from onclick:', paymentUrl);
          // Lưu chat room URL vào sessionStorage để redirect về sau khi thanh toán
          const currentUrl = window.location.href;
          sessionStorage.setItem('payment_return_url', currentUrl);
          // KHÔNG modify payment URL - giữ nguyên như backend generate
          window.location.href = paymentUrl;
          return;
        }
      }

      // Reset loading state nếu không tìm thấy URL
      this.isProcessingPayment = false;
      button.removeAttribute('disabled');
      button.classList.remove('loading');
      console.warn('Could not extract payment URL from button');
    }
  }

  // Attach click handlers to payment buttons after HTML is rendered
  private attachPaymentButtonHandlers(): void {
    const paymentButtons = document.querySelectorAll('.mcp-payment-button');
    paymentButtons.forEach((button) => {
      // Skip if already has handler (check for data attribute)
      if ((button as HTMLElement).dataset['handlerAttached'] === 'true') {
        return;
      }

      // Mark as handler attached
      (button as HTMLElement).dataset['handlerAttached'] = 'true';

      // Attach click handler
      button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();

        // Prevent multiple clicks
        if (this.isProcessingPayment || button.hasAttribute('disabled')) {
          return;
        }

        // Đánh dấu loading
        this.isProcessingPayment = true;
        button.setAttribute('disabled', 'true');
        button.classList.add('loading');

        const paymentUrl = button.getAttribute('data-payment-url') ||
          (button as HTMLElement).dataset['paymentUrl'];
        if (paymentUrl) {
          console.log('Payment button clicked, redirecting to:', paymentUrl);
          // Lưu chat room URL vào sessionStorage để redirect về sau khi thanh toán
          const currentUrl = window.location.href;
          sessionStorage.setItem('payment_return_url', currentUrl);
          // KHÔNG modify payment URL - giữ nguyên như backend generate
          window.location.href = paymentUrl;
        } else {
          // Reset loading state nếu không tìm thấy URL
          this.isProcessingPayment = false;
          button.removeAttribute('disabled');
          button.classList.remove('loading');
          console.warn('Payment URL not found in button');
        }
      });
    });
  }
}