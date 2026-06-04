import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { getBackendUrl } from '../utils/api-base.util';

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private platformId = inject(PLATFORM_ID);

  private get apiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/admin-panel`;
  }

  constructor(private http: HttpClient) {}

  getDashboardStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/stats`);
  }

  getUsers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/users`);
  }

  toggleUserStatus(userId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/${userId}/toggle-status`, {});
  }

  getSubjectDetail(subjectId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/subjects/${subjectId}`);
  }
}
