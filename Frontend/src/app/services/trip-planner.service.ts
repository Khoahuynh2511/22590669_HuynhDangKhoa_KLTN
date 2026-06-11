import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';
import { TripPlanStreamEvent } from '../shared/models/trip-planning.model';

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
   * Supports room_id for chat history persistence and updated_itinerary for drag-and-drop.
   */
  async sendMessage(
    message: string,
    conversationId: string | null,
    roomId?: string | null,
    updatedItinerary?: Record<string, any> | null
  ): Promise<ReadableStreamDefaultReader<Uint8Array>> {
    const token = localStorage.getItem('access_token');

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const body: any = {
      message,
      conversation_id: conversationId,
      room_id: roomId || undefined,
    };

    if (updatedItinerary) {
      body.updated_itinerary = updatedItinerary;
    }

    const response = await fetch(`${this.baseUrl}/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
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
   * Parse SSE stream events from the reader.
   * Calls the callback for each parsed event.
   */
  async parseStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onEvent: (event: TripPlanStreamEvent) => void,
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
            const event = JSON.parse(trimmed.slice(6)) as TripPlanStreamEvent;
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
        const event = JSON.parse(buffer.trim().slice(6)) as TripPlanStreamEvent;
        onEvent(event);
      } catch (e) {
        // Ignore
      }
    }
  }
}
