import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { RegisterComponent } from './register/register.component';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./home/home.component').then(m => m.HomeComponent),
    pathMatch: 'full'
  },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'forgot-password', loadComponent: () => import('./forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent) },
  { path: 'reset-password', loadComponent: () => import('./reset-password/reset-password.component').then(m => m.ResetPasswordComponent) },
  { path: 'dashboard', loadComponent: () => import('./dashboard/dashboard').then(m => m.Dashboard), canActivate: [authGuard] },
  { path: 'profile', loadComponent: () => import('./profile/profile.component').then(m => m.ProfileComponent), canActivate: [authGuard] },
  { path: 'chat/:id', loadComponent: () => import('./chat/chat.component').then(m => m.ChatComponent), canActivate: [authGuard] },
  { path: 'explore', loadComponent: () => import('./explore/explore.component').then(m => m.ExploreComponent), canActivate: [authGuard] },
  { path: 'quiz-practice', loadComponent: () => import('./quiz-practice/quiz-practice.component').then(m => m.QuizPracticeComponent), canActivate: [authGuard] },
  { path: 'quiz-practice/:subjectId/:docId', loadComponent: () => import('./quiz-practice/quiz-practice.component').then(m => m.QuizPracticeComponent), canActivate: [authGuard] },
  
  // Arena & PvP
  { path: 'arena', loadComponent: () => import('./arena/arena.component').then(m => m.ArenaComponent), canActivate: [authGuard] },
  { path: 'pvp', loadChildren: () => import('./pvp/pvp.routes').then(m => m.PVP_ROUTES), canActivate: [authGuard] },
  
  // Diagnostic Test (Chapter-based) & Learning Path
  { path: 'select-subject', loadComponent: () => import('./select-subject/select-subject').then(m => m.SelectSubject), canActivate: [authGuard] },
  { path: 'select-chapter/:subjectId', loadComponent: () => import('./select-chapter/select-chapter').then(m => m.SelectChapter), canActivate: [authGuard] },
  { path: 'chapter-test/:subjectId/:chapterId', loadComponent: () => import('./chapter-test/chapter-test').then(m => m.ChapterTest), canActivate: [authGuard] },
  // pre-test-result được tái sử dụng làm trang polling chờ AI sau khi nộp chapter-test
  { path: 'pre-test-result/:submissionId', loadComponent: () => import('./pre-test-result/pre-test-result').then(m => m.PreTestResult), canActivate: [authGuard] },
  { path: 'post-test-result/:submissionId', loadComponent: () => import('./post-test-result/post-test-result').then(m => m.PostTestResult), canActivate: [authGuard] },
  { path: 'learning-path/:pathId', loadComponent: () => import('./learning-path/learning-path').then(m => m.LearningPathView), canActivate: [authGuard] },
  { path: 'roadmap/:subjectId/:pathId', redirectTo: 'learning-path/:pathId', pathMatch: 'full' },
  { path: 'roadmap/:pathId', redirectTo: 'learning-path/:pathId', pathMatch: 'full' },
  { path: 'learning-path/:pathId/lesson/:itemId', loadComponent: () => import('./lesson-view/lesson-view').then(m => m.LessonView), canActivate: [authGuard] },
  { path: 'learning-path/:pathId/quiz/:itemId', loadComponent: () => import('./post-test/post-test').then(m => m.PostTest), canActivate: [authGuard] },

  {
    path: 'admin',
    canActivate: [authGuard, adminGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./admin/admin-dashboard.component/admin-dashboard.component').then(m => m.AdminDashboardComponent)
      },
      {
        path: 'analytics',
        loadComponent: () => import('./admin/analytics.component/analytics.component').then(m => m.AnalyticsComponent)
      },
      {
        path: 'user-management',
        loadComponent: () => import('./admin/user-management/user-management.component').then(m => m.UserManagementComponent)
      },
      {
        path: 'question-management',
        loadComponent: () => import('./admin/question-management/question-management.component').then(m => m.QuestionManagementComponent)
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  }
];