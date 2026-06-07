import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ChatbotService {
  private openChatbotSubject = new Subject<void>();
  openChatbot$ = this.openChatbotSubject.asObservable();

  openChatbot(): void {
    this.openChatbotSubject.next();
  }
}

