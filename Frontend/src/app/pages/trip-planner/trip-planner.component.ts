import { Component, OnInit, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TripPlannerService, TripPlanMessage } from '../../services/trip-planner.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ActivitySlot {
  activity_id: string;
  name: string;
  price: number;
  category?: string;
  time_slot?: string;
  location?: string;
  image_url?: string;
  duration_hours?: number;
  difficulty?: string;
}

interface ItineraryDay {
  morning: ActivitySlot | null;
  afternoon: ActivitySlot | null;
  evening: ActivitySlot | null;
}

@Component({
  selector: 'app-trip-planner',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './trip-planner.component.html',
  styleUrls: ['./trip-planner.component.scss'],
})
export class TripPlannerComponent implements OnInit, OnDestroy {
  // === Wizard State ===
  currentStep = signal(1);
  isLoading = signal(false);
  isComplete = signal(false);

  // === Chat Messages ===
  messages = signal<ChatMessage[]>([]);
  inputMessage = '';
  conversationId: string | null = null;

  // === Step 4: Itinerary Builder ===
  availableActivities = signal<any[]>([]);
  suggestedItinerary = signal<Record<string, ItineraryDay>>({});
  totalPrice = signal(0);
  showItineraryBuilder = signal(false);

  // === Step 5: Transportation ===
  flights = signal<any[]>([]);
  trains = signal<any[]>([]);
  selectedFlight: any = null;
  selectedTrain: any = null;
  showTransport = signal(false);

  // === Step 6: Checkout ===
  checkoutData = signal<any>(null);
  showCheckout = signal(false);

  // Step labels
  readonly stepLabels = [
    { num: 1, label: 'Thông tin', icon: '📍' },
    { num: 2, label: 'Người & Ngân sách', icon: '👥' },
    { num: 3, label: 'Sở thích', icon: '🎯' },
    { num: 4, label: 'Lập kế hoạch', icon: '🗺️' },
    { num: 5, label: 'Di chuyển', icon: '✈️' },
    { num: 6, label: 'Thanh toán', icon: '💳' },
  ];

  constructor(private tripPlannerService: TripPlannerService) {}

  ngOnInit(): void {
    // Add welcome message
    this.messages.update(msgs => [
      ...msgs,
      {
        role: 'assistant',
        content: '👋 Xin chào! Tôi là trợ lý lên kế hoạch du lịch.\n\nHãy cho mình biết: **Bạn muốn đi đâu và trong bao lâu?**\n\n_(Ví dụ: "Đà Lạt 3 ngày", "Hội An 2 ngày 1 đêm")_',
      },
    ]);
  }

  ngOnDestroy(): void {
    // Cleanup if needed
  }

  /**
   * Send user message and process streaming response.
   */
  async sendMessage(): Promise<void> {
    const msg = this.inputMessage.trim();
    if (!msg || this.isLoading()) return;

    // Add user message
    this.messages.update(msgs => [...msgs, { role: 'user', content: msg }]);
    this.inputMessage = '';
    this.isLoading.set(true);

    try {
      const reader = await this.tripPlannerService.sendMessage(msg, this.conversationId);

      let assistantContent = '';

      await this.tripPlannerService.parseStream(reader, (event: TripPlanMessage) => {
        switch (event.type) {
          case 'start':
            this.conversationId = event.conversation_id || null;
            break;

          case 'token':
            assistantContent += event.content || '';
            // Update or add assistant message
            this.messages.update(msgs => {
              const last = msgs[msgs.length - 1];
              if (last && last.role === 'assistant' && !last.content.endsWith('\n')) {
                // Append to existing
                last.content = assistantContent;
                return [...msgs];
              } else if (last && last.role === 'assistant') {
                last.content = assistantContent;
                return [...msgs];
              } else {
                return [...msgs, { role: 'assistant', content: event.content || '' }];
              }
            });
            break;

          case 'step':
            if (event.step) {
              this.currentStep.set(event.step);
            }
            // Activate UI sections based on step
            if (event.step === 4) {
              this.showItineraryBuilder.set(true);
            }
            if (event.step === 5) {
              this.showTransport.set(true);
            }
            if (event.step === 6) {
              this.showCheckout.set(true);
            }
            // Show token content as assistant message if not already shown
            if (event.message && !assistantContent) {
              this.messages.update(msgs => [...msgs, { role: 'assistant', content: event.message || '' }]);
            }
            break;

          case 'activities':
            if (event.data) {
              this.availableActivities.set(event.data.available || []);
              this.suggestedItinerary.set(event.data.suggested_itinerary || {});
              this.totalPrice.set(event.data.total_price || 0);
              this.showItineraryBuilder.set(true);
            }
            break;

          case 'itinerary_confirmed':
            if (event.data) {
              this.totalPrice.set(event.data.total_price || 0);
            }
            break;

          case 'flights':
            if (event.data) {
              this.flights.set(event.data);
              this.showTransport.set(true);
            }
            break;

          case 'trains':
            if (event.data) {
              this.trains.set(event.data);
              this.showTransport.set(true);
            }
            break;

          case 'checkout':
            if (event.data) {
              this.checkoutData.set(event.data);
              this.showCheckout.set(true);
            }
            break;

          case 'done':
            this.isLoading.set(false);
            if (event.is_complete) {
              this.isComplete.set(true);
            }
            break;

          case 'error':
            this.isLoading.set(false);
            this.messages.update(msgs => [
              ...msgs,
              { role: 'assistant', content: `❌ Lỗi: ${event.error || 'Không xác định'}` },
            ]);
            break;
        }
      });

      // If no token events were received, use the step message
      if (!assistantContent) {
        this.isLoading.set(false);
      }
    } catch (error: any) {
      this.isLoading.set(false);
      this.messages.update(msgs => [
        ...msgs,
        { role: 'assistant', content: `❌ Lỗi kết nối: ${error.message}` },
      ]);
    }
  }

  /**
   * Handle Enter key press in input.
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  /**
   * Select a flight.
   */
  selectFlight(index: number): void {
    const flights = this.flights();
    if (flights[index]) {
      this.selectedFlight = flights[index];
      this.messages.update(msgs => [
        ...msgs,
        { role: 'user', content: `${index + 1}` },
      ]);
      // Auto-send the selection
      this.autoSendMessage(`${index + 1}`);
    }
  }

  /**
   * Select a train.
   */
  selectTrain(index: number): void {
    const trains = this.trains();
    if (trains[index]) {
      this.selectedTrain = trains[index];
      this.messages.update(msgs => [
        ...msgs,
        { role: 'user', content: `${this.flights().length + index + 1}` },
      ]);
      this.autoSendMessage(`${this.flights().length + index + 1}`);
    }
  }

  /**
   * Confirm the suggested itinerary.
   */
  confirmItinerary(): void {
    this.autoSendMessage('xác nhận');
  }

  /**
   * Skip transportation.
   */
  skipTransport(): void {
    this.autoSendMessage('bỏ qua');
  }

  /**
   * Proceed to checkout.
   */
  proceedToCheckout(): void {
    this.autoSendMessage('thanh toán');
  }

  /**
   * Format price in VND.
   */
  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN').format(price) + 'đ';
  }

  /**
   * Render markdown-like content as HTML.
   */
  renderContent(content: string): string {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/_(.*?)_/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded text-sm">$1</code>')
      .replace(/\n/g, '<br>');
  }

  /**
   * Get itinerary days as array for iteration.
   */
  getItineraryDays(): { key: string; num: number; day: ItineraryDay }[] {
    const itinerary = this.suggestedItinerary();
    const days: { key: string; num: number; day: ItineraryDay }[] = [];
    for (let i = 1; i <= 10; i++) {
      const key = `day_${i}`;
      if (itinerary[key]) {
        days.push({ key, num: i, day: itinerary[key] });
      }
    }
    return days;
  }

  private async autoSendMessage(msg: string): Promise<void> {
    this.inputMessage = '';
    this.isLoading.set(true);

    try {
      const reader = await this.tripPlannerService.sendMessage(msg, this.conversationId);
      let assistantContent = '';

      await this.tripPlannerService.parseStream(reader, (event: TripPlanMessage) => {
        if (event.type === 'start') {
          this.conversationId = event.conversation_id || null;
        } else if (event.type === 'token') {
          assistantContent += event.content || '';
          this.messages.update(msgs => {
            const last = msgs[msgs.length - 1];
            if (last && last.role === 'assistant') {
              last.content = assistantContent;
              return [...msgs];
            }
            return [...msgs, { role: 'assistant', content: event.content || '' }];
          });
        } else if (event.type === 'step') {
          if (event.step) this.currentStep.set(event.step);
          if (event.step === 4) this.showItineraryBuilder.set(true);
          if (event.step === 5) this.showTransport.set(true);
          if (event.step === 6) this.showCheckout.set(true);
        } else if (event.type === 'activities') {
          if (event.data) {
            this.availableActivities.set(event.data.available || []);
            this.suggestedItinerary.set(event.data.suggested_itinerary || {});
            this.totalPrice.set(event.data.total_price || 0);
            this.showItineraryBuilder.set(true);
          }
        } else if (event.type === 'flights') {
          this.flights.set(event.data || []);
          this.showTransport.set(true);
        } else if (event.type === 'trains') {
          this.trains.set(event.data || []);
          this.showTransport.set(true);
        } else if (event.type === 'checkout') {
          this.checkoutData.set(event.data);
          this.showCheckout.set(true);
        } else if (event.type === 'done') {
          this.isLoading.set(false);
          if (event.is_complete) this.isComplete.set(true);
        } else if (event.type === 'error') {
          this.isLoading.set(false);
        }
      });

      if (!assistantContent) this.isLoading.set(false);
    } catch {
      this.isLoading.set(false);
    }
  }
}
