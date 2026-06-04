import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { getBackendUrl } from '../utils/api-base.util';

export interface Option {
  id: number;
  option_text: string;
  is_correct?: boolean;
}

export interface Question {
  id: number;
  question_text: string;
  question_type: string;
  order_num: number;
  options?: Option[];
}

export interface Quiz {
  id: number;
  subject: number;
  title: string;
  description: string;
  difficulty: 'Dễ' | 'Trung-bình' | 'Khó';
  questions: Question[];
  created_at?: string;
}

// ─ Kiểu dữ liệu chuẩn cho AI Practice Quiz ─
export interface PracticeQuestion {
  question: string;
  options: string[];      // 4 đáp án A, B, C, D
  correct_index: number;  // Vị trí đáp án đúng (0, 1, 2, 3)
  explanation: string;    // Giải thích tại sao đúng
}

// URL của AI Service — dùng biến môi trường nếu có
const AI_SERVICE_URL = 'http://localhost:8001';
const AI_SERVICE_KEY = 'dev-ai-key-edututor-2024';

@Injectable({
  providedIn: 'root'
})
export class QuizService {
  private platformId = inject(PLATFORM_ID);

  private get apiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/quiz`;
  }

  constructor(private http: HttpClient) {}

  getQuizzes(subjectId?: number): Observable<Quiz[]> {
    const url = subjectId ? `${this.apiUrl}/?subject_id=${subjectId}` : this.apiUrl + '/';
    return this.http.get<Quiz[]>(url);
  }

  getQuizDetail(quizId: number): Observable<Quiz> {
    return this.http.get<Quiz>(`${this.apiUrl}/${quizId}/`);
  }

  submitQuiz(submission: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/submit/`, submission);
  }

  // ── Curriculum APIs ──

  getChapters(subjectId: number): Observable<any[]> {
    const url = `${getBackendUrl(this.platformId)}/api/curriculum/chapters/?subject_id=${subjectId}`;
    return this.http.get<any[]>(url);
  }

  getLessons(chapterId: number): Observable<any[]> {
    const url = `${getBackendUrl(this.platformId)}/api/curriculum/lessons/?chapter_id=${chapterId}`;
    return this.http.get<any[]>(url);
  }

  /**
   * Gọi endpoint /api/v1/generate-quiz của AI Service.
   * Sinh câu hỏi trực tiếp bằng LLM (KHÔNG qua ReAct agent) — ổn định cao.
   */
  generateAIQuiz(
    subjectName: string,
    gradeLevel: number,
    chapterTitle: string,
    numQuestions: number,
    lessonId?: number
  ): Observable<PracticeQuestion[]> {
    return this.http.post<{ questions: PracticeQuestion[]; count: number }>(
      `${AI_SERVICE_URL}/api/v1/generate-quiz`,
      {
        subject_name: subjectName,
        grade_level: gradeLevel,
        chapter_title: chapterTitle,
        num_questions: numQuestions,
        lesson_id: lessonId
      },
      { headers: { 'X-AI-Service-Key': AI_SERVICE_KEY } }
    ).pipe(map(res => res.questions));
  }

  /**
   * Parse chuỗi JSON từ AI thành mảng PracticeQuestion (fallback legacy).
   */
  parseAIQuestions(rawText: string): PracticeQuestion[] {
    try {
      const jsonMatch = rawText.match(/```json\s*([\s\S]*?)\s*```/);
      let jsonStr = jsonMatch ? jsonMatch[1] : rawText;
      const start = jsonStr.indexOf('[');
      const end = jsonStr.lastIndexOf(']');
      if (start !== -1 && end !== -1 && start < end) {
        jsonStr = jsonStr.slice(start, end + 1);
        const parsed = JSON.parse(jsonStr.trim());
        if (Array.isArray(parsed)) return parsed as PracticeQuestion[];
      }
    } catch (e) {
      console.warn('[QuizService] Không parse được JSON từ AI:', e);
    }
    return [];
  }
}
