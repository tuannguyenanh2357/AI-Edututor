import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  // Routes có tham số động -> Client-side rendering
  { path: 'select-chapter/:subjectId', renderMode: RenderMode.Client },
  { path: 'chapter-test/:subjectId/:chapterId', renderMode: RenderMode.Client },
  { path: 'pre-test-result/:submissionId', renderMode: RenderMode.Client },
  { path: 'post-test-result/:submissionId', renderMode: RenderMode.Client },
  { path: 'learning-path/:pathId', renderMode: RenderMode.Client },
  { path: 'learning-path/:pathId/lesson/:itemId', renderMode: RenderMode.Client },
  { path: 'learning-path/:pathId/quiz/:itemId', renderMode: RenderMode.Client },
  { path: 'chat/:id', renderMode: RenderMode.Client },
  { path: 'quiz-practice', renderMode: RenderMode.Client },
  { path: 'quiz-practice/:subjectId/:docId', renderMode: RenderMode.Client },
  { path: 'pvp/battle/:id', renderMode: RenderMode.Client },
  { path: 'pvp/result/:id', renderMode: RenderMode.Client },
  { path: 'roadmap/:subjectId/:pathId', renderMode: RenderMode.Client },
  { path: 'roadmap/:pathId', renderMode: RenderMode.Client },
  // Tất cả các route còn lại -> Prerender
  {
    path: '**',
    renderMode: RenderMode.Prerender
  }
];
