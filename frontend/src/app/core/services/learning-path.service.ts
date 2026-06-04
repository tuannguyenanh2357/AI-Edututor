import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { getBackendUrl } from '../utils/api-base.util';

export interface PreTestAnswer {
  id: number;
  answer_text: string;
  order_num: number;
}

export interface PreTestQuestion {
  id: number;
  question_text: string;
  explanation: string;
  chapter_title: string;
  difficulty_level?: number;
  difficulty_display?: string;
  topic?: number;
  answers: PreTestAnswer[];
}

export interface LearningPathItem {
  id: number;
  item_type: 'LESSON' | 'QUIZ' | 'TOPIC';
  lesson: any; 
  lesson_id?: number;
  lesson_title?: string;
  topic: any;
  quiz: any;   
  quiz_title?: string;
  chapter_name?: string;
  chapter_id?: number;
  order_num: number;
  is_unlocked: boolean;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED';
  mastery_level?: 'RED' | 'YELLOW' | 'GREEN';
  progress_records?: any[];
  error_tags?: string[];
  topics_list?: string[];
  lesson_number?: string;
}

export interface LearningPath {
  id: number;
  subject: any;
  subject_name: string;
  grade_level: number;
  chapter?: number;
  chapter_title?: string;
  pre_test_score: number;
  post_test_score?: number;
  post_test_ai_feedback?: string;
  strategy: 'foundation' | 'standard' | 'advanced';
  ai_feedback: string;
  status: 'ACTIVE' | 'COMPLETED' | 'PENDING';
  items: LearningPathItem[];
  progress_percentage: number;
  completed_items: number;
  total_items: number;
}

@Injectable({
  providedIn: 'root'
})
export class LearningPathService {
  private platformId = inject(PLATFORM_ID);
  
  constructor(private http: HttpClient) {}

  private get quizApiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/quiz`;
  }
  
  private get usersApiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/users`;
  }

  // Lấy Pre-Test cho 1 môn học — backend trả về QuizSerializer (id + questions[])
  getPreTest(subjectId: number): Observable<{id: number, questions: PreTestQuestion[]}> {
    return this.http.get<{id: number, questions: PreTestQuestion[]}>(`${this.quizApiUrl}/pre-test/?subject_id=${subjectId}`);
  }

  // Gửi bài Pre-Test — backend expect { quiz_id, answers: {"question_id": answer_id, ...} }
  submitPreTest(submission: { quiz_id: number; answers: { [questionId: string]: number } }): Observable<{submission_id: number, score: number, message: string}> {
    return this.http.post<{submission_id: number, score: number, message: string}>(`${this.quizApiUrl}/pre-test/submit/`, submission);
  }

  // Poll kết quả Chapter Test (luồng chính, thay thế pre-test)
  getChapterTestResult(submissionId: number): Observable<any> {
    return this.http.get<any>(`${this.quizApiUrl}/chapter-test/result/${submissionId}/`);
  }

  // Poll kết quả Post-test
  getPostTestResult(submissionId: number): Observable<any> {
    return this.http.get<any>(`${this.quizApiUrl}/post-test/result/${submissionId}/`);
  }

  // Poll kết quả Pre-Test (LEGACY - giữ lại để backward compat)
  getPreTestResult(submissionId: number): Observable<any> {
    return this.http.get<any>(`${this.quizApiUrl}/pre-test/result/${submissionId}/`);
  }

  // Lấy các Learning Paths của user
  getLearningPaths(subjectId?: number): Observable<LearningPath[]> {
    const url = subjectId ? `${this.usersApiUrl}/learning-path/?subject_id=${subjectId}` : `${this.usersApiUrl}/learning-path/`;
    return this.http.get<LearningPath[]>(url);
  }

  // Lấy 1 Learning Path chi tiết
  getLearningPathDetail(pathId: number): Observable<LearningPath> {
    return this.http.get<LearningPath>(`${this.usersApiUrl}/learning-path/${pathId}/`);
  }

  // Đánh dấu bắt đầu item (IN_PROGRESS)
  startItem(itemId: number): Observable<any> {
    return this.http.post<any>(`${this.usersApiUrl}/learning-path/items/${itemId}/start/`, {});
  }

  // Đánh dấu hoàn thành item (mở khóa item tiếp theo)
  completeItem(itemId: number, options?: any): Observable<any> {
    return this.http.post<any>(`${this.usersApiUrl}/learning-path/items/${itemId}/complete/`, options || {});
  }

  // Reset Learning Path (học lại từ đầu sau khi thi trượt post-test)
  resetLearningPath(pathId: number): Observable<any> {
    return this.http.post<any>(`${this.usersApiUrl}/learning-path/reset/`, { path_id: pathId });
  }
}
