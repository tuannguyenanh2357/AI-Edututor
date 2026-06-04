import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { getBackendUrl } from '../utils/api-base.util';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private platformId = inject(PLATFORM_ID);

  private get apiUrl(): string {
    return `${getBackendUrl(this.platformId)}/api/auth`;
  }

  constructor(private http: HttpClient) {}

  login(credentials: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/login`, credentials);
  }

  loginWithGoogle(idToken: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/google`, { idToken });
  }

  saveToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  saveUserData(token: string, role: string, id: number): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user_role', role);
      localStorage.setItem('user_id', id.toString());
    }
  }

  getUserId(): number | null {
    if (typeof window !== 'undefined') {
      const id = localStorage.getItem('user_id');
      return id ? parseInt(id, 10) : null;
    }
    return null;
  }

  saveRole(role: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('user_role', role);
    }
  }

  getRole(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('user_role');
    }
    return null;
  }

  isAdmin(): boolean {
    const role = this.getRole();
    return role ? role.toUpperCase() === 'ADMIN' : false;
  }

  isLoggedIn(): boolean {
    return this.getToken() !== null;
  }

  logout(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('user_id');
    }
  }

  register(userData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, userData);
  }

  forgotPassword(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/forgot-password`, { email });
  }

  resetPassword(data: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/reset-password`, data);
  }

  updateProfile(data: { full_name?: string; avatar_url?: string; ai_preferences?: string }): Observable<any> {
    return this.http.patch(`${this.apiUrl}/me/update`, data);
  }

  getPublicProfile(username: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/profile/${username}`);
  }

  logoutApi(refreshToken: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/logout`, { refresh_token: refreshToken });
  }

  getCurrentUser(): Observable<any> {
    return this.http.get(`${this.apiUrl}/me`);
  }
}