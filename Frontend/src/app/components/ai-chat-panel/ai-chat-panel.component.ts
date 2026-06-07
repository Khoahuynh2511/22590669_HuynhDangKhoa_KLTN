import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer } from '@angular/platform-browser';
import { NewsAgentService, NewsAgentResponse } from '../../services/news-agent.service';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  timestamp: Date;
}

@Component({
  selector: 'app-ai-chat-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-chat-panel.component.html',
  styleUrl: './ai-chat-panel.component.scss'
})
export class AiChatPanelComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer', { static: false }) messagesContainer!: ElementRef;
  
  messages: ChatMessage[] = [];
  currentMessage: string = '';
  isSending: boolean = false;
  errorMessage: string | null = null;
  private shouldScroll = false;

  constructor(
    private newsAgentService: NewsAgentService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    // Add welcome message
    this.messages.push({
      role: 'assistant',
      content: 'Xin chào! Tôi có thể giúp bạn tìm kiếm tin tức và cẩm nang du lịch. Hãy cho tôi biết bạn muốn tìm gì nhé!',
      timestamp: new Date()
    });
  }

  ngOnDestroy(): void {
    // Component cleanup if needed
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  async sendMessage(): Promise<void> {
    if (!this.currentMessage.trim() || this.isSending) {
      return;
    }

    const userMessage = this.currentMessage.trim();
    this.currentMessage = '';
    this.errorMessage = null;

    // Add user message
    this.messages.push({
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    });

    this.shouldScroll = true;
    this.isSending = true;

    try {
      const response: NewsAgentResponse = await this.newsAgentService.sendMessage(userMessage);
      
      // Add assistant response
      this.messages.push({
        role: 'assistant',
        content: response.response,
        sources: response.sources || [],
        timestamp: new Date()
      });

      this.shouldScroll = true;
    } catch (error: any) {
      console.error('Error sending message:', error);
      this.errorMessage = error.message || 'Lỗi khi gửi tin nhắn. Vui lòng thử lại.';
      
      // Add error message
      this.messages.push({
        role: 'assistant',
        content: `Xin lỗi, đã có lỗi xảy ra: ${this.errorMessage}`,
        timestamp: new Date()
      });
    } finally {
      this.isSending = false;
    }
  }

  async onKeyDown(event: KeyboardEvent): Promise<void> {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await this.sendMessage();
    }
  }

  onTextareaInput(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  }

  async clearConversation(): Promise<void> {
    try {
      await this.newsAgentService.clearConversation();
      this.messages = [];
      this.errorMessage = null;
      
      // Add welcome message again
      this.messages.push({
        role: 'assistant',
        content: 'Xin chào! Tôi có thể giúp bạn tìm kiếm tin tức và cẩm nang du lịch. Hãy cho tôi biết bạn muốn tìm gì nhé!',
        timestamp: new Date()
      });
    } catch (error: any) {
      console.error('Error clearing conversation:', error);
      this.errorMessage = 'Lỗi khi xóa lịch sử. Vui lòng thử lại.';
    }
  }

  openSource(url: string): void {
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  formatMessage(content: string): string {
    // Simple formatting: convert markdown-style **bold** to HTML
    const formatted = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
    // Sanitize HTML to prevent XSS
    return this.sanitizer.sanitize(1, formatted) || content;
  }

  formatTime(timestamp: Date): string {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) {
      return 'Vừa xong';
    } else if (minutes < 60) {
      return `${minutes} phút trước`;
    } else {
      const hours = Math.floor(minutes / 60);
      if (hours < 24) {
        return `${hours} giờ trước`;
      } else {
        return timestamp.toLocaleDateString('vi-VN', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      }
    }
  }

  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        const element = this.messagesContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    } catch (error) {
      console.error('Error scrolling:', error);
    }
  }
}
