import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

/**
 * LoadingService — Quản lý trạng thái loading toàn cục.
 * Dùng counter để xử lý nhiều HTTP request song song,
 * loader chỉ ẩn khi TẤT CẢ request đã hoàn thành.
 */
@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private _requestCount = 0;
  private _loading$ = new BehaviorSubject<boolean>(false);

  /** Observable để các component lắng nghe trạng thái loading */
  readonly loading$: Observable<boolean> = this._loading$.asObservable();

  show(): void {
    this._requestCount++;
    if (this._requestCount === 1) {
      this._loading$.next(true);
    }
  }

  hide(): void {
    if (this._requestCount > 0) {
      this._requestCount--;
    }
    if (this._requestCount === 0) {
      this._loading$.next(false);
    }
  }
}
