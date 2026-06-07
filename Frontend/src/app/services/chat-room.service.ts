import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

export interface ChatRoom {
  room_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  message_count?: number;
  last_message?: string;
  last_message_at?: string;
  metadata?: any;
}

export interface ChatMessage {
  message_id: string;
  room_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  message_order: number;
  intent?: string;
  entities?: any;
}

export interface ChatRoomListResponse {
  EC: number;
  EM: string;
  data: ChatRoom[];
  total: number;
}

export interface ChatRoomDetailResponse {
  EC: number;
  EM: string;
  data: ChatRoom | null;
}

export interface ChatMessagesResponse {
  EC: number;
  EM: string;
  data: ChatMessage[];
  total: number;
  limit: number;
  offset: number;
}

@Injectable({
  providedIn: 'root'
})
export class ChatRoomService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) { }

  private get apiUrl(): string {
    return `${this.configService.getApiUrl()}/chat`;
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    });
  }

  /**
   * Tạo chat room mới
   */
  createRoom(title?: string): Observable<ChatRoomDetailResponse> {
    return this.http.post<ChatRoomDetailResponse>(
      `${this.apiUrl}/rooms`,
      { title: title || null },
      { headers: this.getHeaders() }
    );
  }

  /**
   * Lấy danh sách chat rooms của user
   */
  getRooms(archived?: boolean, limit: number = 50, offset: number = 0): Observable<ChatRoomListResponse> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    
    if (archived !== undefined) {
      params = params.set('archived', archived.toString());
    }

    return this.http.get<ChatRoomListResponse>(
      `${this.apiUrl}/rooms`,
      { headers: this.getHeaders(), params }
    );
  }

  /**
   * Lấy thông tin chi tiết một room
   */
  getRoom(roomId: string): Observable<ChatRoomDetailResponse> {
    return this.http.get<ChatRoomDetailResponse>(
      `${this.apiUrl}/rooms/${roomId}`,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Lấy lịch sử messages của một room
   */
  getRoomMessages(roomId: string, limit: number = 50, offset: number = 0): Observable<ChatMessagesResponse> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    return this.http.get<ChatMessagesResponse>(
      `${this.apiUrl}/rooms/${roomId}/messages`,
      { headers: this.getHeaders(), params }
    );
  }

  /**
   * Cập nhật room (title, archive status)
   */
  updateRoom(roomId: string, data: { title?: string; is_archived?: boolean }): Observable<ChatRoomDetailResponse> {
    return this.http.put<ChatRoomDetailResponse>(
      `${this.apiUrl}/rooms/${roomId}`,
      data,
      { headers: this.getHeaders() }
    );
  }

  /**
   * Xóa room và tất cả messages
   */
  deleteRoom(roomId: string): Observable<any> {
    return this.http.delete(
      `${this.apiUrl}/rooms/${roomId}`,
      { headers: this.getHeaders() }
    );
  }

}

