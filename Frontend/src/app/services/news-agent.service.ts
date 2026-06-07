import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { AuthService } from './auth.service';

export interface NewsAgentMessage {
  message: string;
}

export interface NewsAgentResponse {
  EC: number;
  EM: string;
  response: string;
  sources: string[];
  destination?: string;
}

@Injectable({
  providedIn: 'root'
})
export class NewsAgentService {
  constructor(
    private configService: ConfigService,
    private authService: AuthService
  ) {}

  private get apiBaseUrl(): string {
    return this.configService.getApiUrl();
  }

  private getAuthHeaders(): HeadersInit {
    const token = this.authService.getToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }

  async sendMessage(message: string): Promise<NewsAgentResponse> {
    try {
      const url = `${this.apiBaseUrl}/news-agent/chat`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ message })
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Bạn cần đăng nhập để sử dụng tính năng này');
        }
        
        let errorMessage = 'Lỗi khi gửi tin nhắn';
        try {
          const errorData = await response.json();
          errorMessage = errorData.EM || errorData.detail || errorMessage;
        } catch {
          errorMessage = `Lỗi ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data: NewsAgentResponse = await response.json();
      
      if (data.EC !== 0) {
        throw new Error(data.EM || 'Lỗi không xác định');
      }

      return data;
    } catch (error: any) {
      console.error('Error sending message to news agent:', error);
      throw error;
    }
  }

  async clearConversation(): Promise<void> {
    try {
      const url = `${this.apiBaseUrl}/news-agent/clear`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Bạn cần đăng nhập');
        }
        throw new Error('Lỗi khi xóa lịch sử');
      }

      const data = await response.json();
      if (data.EC !== 0) {
        throw new Error(data.EM || 'Lỗi không xác định');
      }
    } catch (error: any) {
      console.error('Error clearing conversation:', error);
      throw error;
    }
  }
}
