import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';

export interface TripPlanMessage {
  type: 'start' | 'step' | 'token' | 'activities' | 'itinerary_confirmed' | 'flights' | 'trains' | 'checkout' | 'done' | 'error';
  conversation_id?: string;
  user_id?: string;
  step?: number;
  message?: string;
  content?: string;
  waiting_for_input?: boolean;
  is_complete?: boolean;
  data?: any;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class TripPlannerService {
  constructor(private configService: ConfigService) {}

  private get baseUrl(): string {
    return `${this.configService.getApiUrl()}/trip-planning`;
  }

  /**
   * Send a message in the trip planning workflow and get SSE streaming response.
   */
  async sendMessage(message: string, conversationId: string | null): Promise<ReadableStreamDefaultReader<Uint8Array>> {
    const token = localStorage.getItem('access_token');

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    return response.body.getReader();
  }

  /**
   * Start a new trip planning session with optional pre-fill data.
   */
  async startPlanning(initialData?: { destination?: string; duration_days?: number }): Promise<any> {
    const token = localStorage.getItem('access_token');

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}/start`, {
      method: 'POST',
      headers,
      body: JSON.stringify(initialData || {}),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Parse SSE stream events from the reader.
   * Calls the callback for each parsed event.
   */
  async parseStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onEvent: (event: TripPlanMessage) => void,
  ): Promise<void> {
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          try {
            const event = JSON.parse(trimmed.slice(6)) as TripPlanMessage;
            onEvent(event);
          } catch (e) {
            console.warn('Failed to parse SSE event:', trimmed, e);
          }
        }
      }
    }

    // Process remaining buffer
    if (buffer.trim().startsWith('data: ')) {
      try {
        const event = JSON.parse(buffer.trim().slice(6)) as TripPlanMessage;
        onEvent(event);
      } catch (e) {
        // Ignore
      }
    }
  }
}
