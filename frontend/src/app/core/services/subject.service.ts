import { Injectable, inject, PLATFORM_ID, TransferState, makeStateKey } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { isPlatformServer } from '@angular/common';
import { Observable, of, tap } from 'rxjs';
import { getBackendUrl } from '../utils/api-base.util';

export interface TeacherDocument {
  id: number;
  title: string;
  content: string;
  pdf_file?: string;
  uploaded_at: string;
}

export interface Subject {
  id: number;
  name: string;
  description: string;
  icon_url: string;
  grade_level?: number; 
  page_offset?: number;
  documents?: TeacherDocument[];
}

export interface Chapter {
  id: number;
  title: string;
  description?: string;
  order_num: number;
  subject: number;
  has_learning_path?: boolean;
  learning_path_id?: number;
  is_mastered?: boolean;
  is_completed?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class SubjectService {
  // [FIX SSR] Dynamic URL: dùng "backend" trong Docker, "localhost" trên trình duyệt
  private get apiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/subjects`;
  }

  private transferState = inject(TransferState);
  private platformId = inject(PLATFORM_ID);

  constructor(private http: HttpClient) {}

  getSubjects(): Observable<Subject[]> {
    const SUBJECTS_KEY = makeStateKey<Subject[]>('all-subjects');
    if (this.transferState.hasKey(SUBJECTS_KEY)) {
      const cached = this.transferState.get(SUBJECTS_KEY, []);
      this.transferState.remove(SUBJECTS_KEY);
      return of(cached);
    }

    return this.http.get<Subject[]>(`${this.apiUrl}/`).pipe(
      tap((data) => {
        if (isPlatformServer(this.platformId)) {
          this.transferState.set(SUBJECTS_KEY, data);
        }
      })
    );
  }

  getSubjectDetail(id: number): Observable<Subject> {
    const SUBJECT_DETAIL_KEY = makeStateKey<Subject>(`subject-${id}`);
    
    if (this.transferState.hasKey(SUBJECT_DETAIL_KEY)) {
      const cached = this.transferState.get(SUBJECT_DETAIL_KEY, null);
      if (cached) {
        this.transferState.remove(SUBJECT_DETAIL_KEY);
        return of(cached);
      }
    }

    return this.http.get<Subject>(`${this.apiUrl}/${id}/`).pipe(
      tap((data) => {
        if (isPlatformServer(this.platformId)) {
          this.transferState.set(SUBJECT_DETAIL_KEY, data);
        }
      })
    );
  }

  getChapters(subjectId: number): Observable<Chapter[]> {
    return this.http.get<Chapter[]>(`${getBackendUrl(this.platformId)}/api/curriculum/chapters/?subject_id=${subjectId}`);
  }
}
