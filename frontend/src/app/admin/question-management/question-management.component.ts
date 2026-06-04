import { Component, OnInit, Inject, PLATFORM_ID, ChangeDetectorRef } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { getBackendUrl } from '../../core/utils/api-base.util';
import { MarkdownRenderPipe } from '../../core/pipes/markdown-render.pipe';
import { ToastrService } from 'ngx-toastr';

interface Question {
  id: number;
  question_text: string;
  subject_name: string;
  grade_level: number;
  chapter_title: string;
  bloom_level: number;
  explanation: string;
  lesson_title?: string;
  answers: any[];
}

@Component({
  selector: 'app-question-management',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, MarkdownRenderPipe],
  templateUrl: './question-management.component.html',
  styleUrls: ['./question-management.component.css']
})
export class QuestionManagementComponent implements OnInit {

  questions: Question[] = [];
  isLoading = false;
  isGenerating = false;
  showAIModal = false;

  // Filters for Main View
  filterGrade = '';
  filterSubject = '';
  filterChapter = '';
  searchQuery = '';

  // AI Modal Form
  aiForm = {
    grade: '',
    subject: '',
    chapter: '',
    numQuestions: 5
  };

  // Dropdown options
  grades = [10, 11, 12];
  subjects: any[] = [];
  filteredSubjects: any[] = [];
  aiFilteredSubjects: any[] = [];
  chapters: string[] = [];
  aiChapters: string[] = [];

  constructor(
    private http: HttpClient,
    private toastr: ToastrService,
    private cd: ChangeDetectorRef,
    @Inject(PLATFORM_ID) private platformId: Object
  ) { }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.loadFilters();
      this.loadQuestions();
    }
  }

  private get apiBase(): string {
    return `${getBackendUrl(this.platformId)}/api/admin/questions`;
  }

  loadFilters(): void {
    this.http.get<any>(`${this.apiBase}/filters/`).subscribe({
      next: (data) => {
        this.subjects = data.subjects;
        this.updateFilteredSubjects();
        this.chapters = data.chapters;
      },
      error: (err) => console.error('Lỗi load filters:', err)
    });
  }

  updateFilteredSubjects(): void {
    this.filteredSubjects = this.getUniqueSubjects(this.subjects, this.filterGrade);
  }

  updateAIFilteredSubjects(): void {
    this.aiFilteredSubjects = this.getUniqueSubjects(this.subjects, this.aiForm.grade);
  }

  private getUniqueSubjects(allSubjects: any[], grade?: string | number): any[] {
    let list = allSubjects;
    if (grade) {
      list = list.filter(s => s.grade_level == grade);
    }
    const uniqueMap = new Map();
    list.forEach(s => {
      if (!uniqueMap.has(s.name)) {
        uniqueMap.set(s.name, s);
      }
    });
    return Array.from(uniqueMap.values());
  }

  loadQuestions(): void {
    this.isLoading = true;
    let params: any = {};
    if (this.filterGrade) params.grade = this.filterGrade;
    if (this.filterSubject) params.subject_name = this.filterSubject;
    if (this.filterChapter) params.chapter_title = this.filterChapter;
    if (this.searchQuery) params.search = this.searchQuery;

    this.http.get<any>(`${this.apiBase}/`, { params }).subscribe({
      next: (data) => {
        this.questions = data.questions;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Lỗi load questions:', err);
        this.isLoading = false;
      }
    });
  }

  applyFilter(): void {
    this.updateFilteredSubjects();
    this.loadQuestions();
  }

  openAIModal(): void {
    this.showAIModal = true;
    this.aiChapters = []; 
    this.updateAIFilteredSubjects();
  }

  closeAIModal(): void {
    this.showAIModal = false;
  }

  onAIFormChange(): void {
    this.updateAIFilteredSubjects();
    if (this.aiForm.grade && this.aiForm.subject) {
      this.http.get<any>(`${this.apiBase}/filters/`, {
        params: { grade: this.aiForm.grade, subject_name: this.aiForm.subject }
      }).subscribe(data => {
        this.aiChapters = data.chapters;
      });
    }
  }

  generateWithAI(): void {
    const { grade, subject, chapter, numQuestions } = this.aiForm;
    if (!grade || !subject || !chapter) {
      this.toastr.warning('Vui lòng điền đầy đủ thông tin để AI sinh câu hỏi.', 'Thiếu thông tin');
      return;
    }

    this.isGenerating = true;
    this.http.post<any>(`${this.apiBase}/generate-ai/`, {
      grade,
      subject_name: subject,
      chapter_title: chapter,
      num_questions: numQuestions
    }).subscribe({
      next: (res) => {
        this.toastr.success(res.message, 'Thành công');
        this.showAIModal = false;
        // Dùng setTimeout để tránh lỗi NG0100
        setTimeout(() => {
          this.isGenerating = false;
          this.loadQuestions();
        }, 100);
      },
      error: (err) => {
        console.error('Lỗi AI:', err);
        this.toastr.error(err.error?.error || 'Lỗi AI', 'Lỗi');
        setTimeout(() => {
          this.isGenerating = false;
        }, 100);
      }
    });
  }

  deleteQuestion(id: number): void {
    if (!confirm('Bạn có chắc chắn muốn xóa câu hỏi này?')) return;

    this.http.delete<any>(`${this.apiBase}/?id=${id}`).subscribe({
      next: () => {
        this.toastr.success('Đã xóa câu hỏi', 'Thành công');
        this.loadQuestions();
      },
      error: (err) => this.toastr.error('Lỗi khi xóa', 'Lỗi')
    });
  }

  getBloomName(level: number): string {
    const names: { [key: number]: string } = {
      1: 'Nhận biết',
      2: 'Thông hiểu',
      3: 'Vận dụng',
      4: 'Phân tích',
      5: 'Đánh giá',
      6: 'Sáng tạo'
    };
    return names[level] || `Mức ${level}`;
  }
}
