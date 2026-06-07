import { Component, ElementRef, EventEmitter, Output, ViewChild, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ConfigService } from '../../services/config.service';

interface Message {
  content: string;
  role: 'user' | 'assistant' | 'admin';
  created_at: string;
  // UI helpers
  isUser: boolean;
  timestamp: Date;
  isError?: boolean;
}

interface Conversation {
  id: string;
  title: string;
  updatedAt: Date;
  lastMessage?: string;
  messageCount?: number;
}

@Component({
  selector: 'app-admin-chatbot',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-chatbot.component.html',
  styleUrls: ['./admin-chatbot.component.scss']
})
export class AdminChatbotComponent implements OnInit {
  @Output() close = new EventEmitter<void>();
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('messageInput') messageInputRef!: ElementRef;

  messages: Message[] = [];
  userMessage = '';
  isStreaming = false;
  isTyping = false;
  conversationId: string | null = null;
  headerStatus = 'Online';
  conversations: Conversation[] = [];
  activeConversation: Conversation | null = null;
  isLoadingConversations = false;
  isLoadingMessages = false;
  isDeletingConversation: string | null = null;

  private apiUrl = '';

  constructor(
    private router: Router,
    private configService: ConfigService
  ) {
    // Initialize API URL from ConfigService
    this.apiUrl = `${this.configService.getApiUrl()}/admin/agent`;
  }

  ngOnInit(): void {
    // Load conversations from API
    this.loadConversations();
  }

  onClose(): void {
    this.close.emit();
  }

  startNewConversation(): void {
    this.activeConversation = null;
    this.conversationId = null;
    this.messages = [];
    this.addSystemMessage('Xin chào Admin! Tôi có thể giúp gì cho bạn hôm nay?');
  }

  async loadConversations(): Promise<void> {
    this.isLoadingConversations = true;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${this.apiUrl}/conversations?limit=20`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Map Backend (snake_case) to Frontend (camelCase)
        this.conversations = data.map((item: any) => ({
          id: item.room_id,
          title: item.title,
          updatedAt: new Date(item.updated_at),
          lastMessage: item.last_message,
          messageCount: item.message_count
        }));

        // If there are conversations but no active selection, verify state
        if (this.conversations.length > 0 && !this.conversationId) {
          // Keep as new conversation state
        }
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      this.isLoadingConversations = false;
    }
  }

  async selectConversation(conversationId: string): Promise<void> {
    if (this.conversationId === conversationId) return;

    const conversation = this.conversations.find(c => c.id === conversationId);
    if (!conversation) return;

    this.activeConversation = conversation;
    this.conversationId = conversationId;
    this.isLoadingMessages = true;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${this.apiUrl}/conversations/${conversationId}/messages`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        this.messages = data.map((msg: any) => ({
          content: msg.content,
          role: msg.role,
          created_at: msg.created_at,
          isUser: msg.role === 'user' || msg.role === 'admin',
          timestamp: new Date(msg.created_at)
        }));
        setTimeout(() => this.scrollToBottom(), 100);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
      this.addSystemMessage('Không thể tải lịch sử trò chuyện.', true);
    } finally {
      this.isLoadingMessages = false;
    }
  }

  async deleteConversation(conversationId: string, event?: Event): Promise<void> {
    if (event) {
      event.stopPropagation();
    }

    if (this.isDeletingConversation) return;
    if (!confirm('Bạn có chắc muốn xóa cuộc trò chuyện này?')) return;

    this.isDeletingConversation = conversationId;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${this.apiUrl}/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        this.conversations = this.conversations.filter(c => c.id !== conversationId);

        if (this.conversationId === conversationId) {
          this.startNewConversation();
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    } finally {
      this.isDeletingConversation = null;
    }
  }

  async sendMessage(): Promise<void> {
    if (!this.userMessage.trim() || this.isStreaming) return;

    const messageText = this.userMessage.trim();
    this.userMessage = '';

    // Optimistic UI update
    this.addUserMessage(messageText);

    this.isTyping = true;
    this.isStreaming = true;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${this.apiUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: messageText,
          session_id: this.conversationId // Send current room ID if exists
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      this.isTyping = false;

      if (data.success) {
        this.addAssistantMessage(data.response || 'Đã xử lý xong yêu cầu của bạn.');

        // Update session ID if it was a new conversation
        if (!this.conversationId && data.session_id) {
          this.conversationId = data.session_id;
          // Refresh conversation list to show the new room
          this.loadConversations();
        }
      } else {
        this.addAssistantMessage(data.error || 'Có lỗi xảy ra khi xử lý yêu cầu.', true);
      }

    } catch (error) {
      this.isTyping = false;
      console.error('Admin agent error:', error);
      this.addAssistantMessage(
        'Lỗi kết nối đến Admin Intelligence. Vui lòng thử lại sau.',
        true
      );
    } finally {
      this.isStreaming = false;
    }
  }

  private addUserMessage(content: string): void {
    const message: Message = {
      content,
      role: 'admin',
      created_at: new Date().toISOString(),
      isUser: true,
      timestamp: new Date()
    };
    this.messages.push(message);
    setTimeout(() => this.scrollToBottom(), 100);
  }

  private addAssistantMessage(content: string, isError: boolean = false): void {
    const message: Message = {
      content,
      role: 'assistant',
      created_at: new Date().toISOString(),
      isUser: false,
      timestamp: new Date(),
      isError
    };
    this.messages.push(message);
    setTimeout(() => this.scrollToBottom(), 100);
  }

  private addSystemMessage(content: string, isError: boolean = false): void {
    // Treat system messages as assistant messages for UI purposes
    this.addAssistantMessage(content, isError);
  }

  private scrollToBottom(): void {
    if (this.messagesContainer?.nativeElement) {
      this.messagesContainer.nativeElement.scrollTop =
        this.messagesContainer.nativeElement.scrollHeight;
    }
  }

  getConversationPreview(conversation: Conversation): string {
    return conversation.lastMessage || 'Không có tin nhắn';
  }

  formatMessageContent(content: string): string {
    if (!content) return '';
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  formatTime(date: Date | string): string {
    const d = new Date(date);
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }

  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
