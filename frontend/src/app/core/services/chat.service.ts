import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { isPlatformBrowser } from '@angular/common';
import { Observable } from 'rxjs';
import { getBackendUrl, getAiServiceUrl } from '../utils/api-base.util';

export interface ChatThread {
  id: string;
  user?: number;
  subject: number | null;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  id?: number;
  thread?: string; // Thread UUID
  user?: number;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private platformId = inject(PLATFORM_ID);
  private aiServiceKey = 'dev-ai-key-edututor-2024';

  private get aiUrl(): string {
    return `${getAiServiceUrl(this.platformId)}/api/v1/chat`;
  }

  private get djangoUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/chat`;
  }

  constructor(private http: HttpClient) { }

  /**
   * Real-time streaming using Fetch API (SSE compatible)
   * [NOTE] fetch() chỉ chạy trên trình duyệt nên URL của nó luôn là localhost
   */
  getChatStream(message: string, studentId: number, subject: string, chatHistory: any[], imageData?: string, threadId?: string | null): Observable<any> {
    return new Observable(observer => {
      const body: any = {
        message,
        student_id: studentId,
        subject_name: subject,
        chat_history: chatHistory.map(m => ({ role: m.role, content: m.content }))
      };

      if (imageData) {
        body.image_data = imageData;
      }
      if (threadId) {
        body.thread_id = threadId;
      }

      // fetch() chạy ở browser, nên dùng localhost trực tiếp
      fetch('http://localhost:8001/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-AI-Service-Key': this.aiServiceKey
        },
        body: JSON.stringify(body)
      }).then(async response => {
        if (!response.ok) {
          observer.error('Network response was not ok');
          return;
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          observer.error('ReadableStream not supported');
          return;
        }

        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                observer.next(data);
              } catch (e) {
                console.error('Error parsing SSE data', e);
              }
            }
          }
        }
        observer.complete();
      }).catch(err => {
        observer.error(err);
      });
    });
  }

  /**
   * Persist message pair to Django
   */
  saveChatPair(
    subjectId: number, 
    userMsg: string, 
    aiRes: string, 
    threadId: string | null = null,
    sourceMetadata: any[] = [],
    imageData: string | null = null
  ): Observable<any> {
    const payload: any = {
      subject: subjectId,
      user_message: userMsg,
      ai_response: aiRes,
      thread_id: threadId,
      source_metadata: sourceMetadata,
      image_data: imageData
    };
    return this.http.post(`${this.djangoUrl}/save/`, payload);
  }

  getChatHistory(threadId: string): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.djangoUrl}/history/?thread_id=${threadId}`);
  }

  clearChatHistory(threadId: string): Observable<any> {
    return this.http.post(`${this.djangoUrl}/clear/`, { thread_id: threadId });
  }

  // --- THREAD APIS ---
  getThreads(): Observable<ChatThread[]> {
    return this.http.get<ChatThread[]>(`${this.djangoUrl}/threads/`);
  }

  deleteThread(threadId: string): Observable<any> {
    return this.http.delete(`${this.djangoUrl}/threads/${threadId}/`);
  }

  // Legacy fallback
  sendMessage(message: ChatMessage): Observable<ChatMessage> {
    return this.http.post<ChatMessage>(`${this.djangoUrl}/send/`, message);
  }
}
