import { Pipe, PipeTransform, inject, SecurityContext } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import * as katex from 'katex';

@Pipe({
  name: 'markdownRender',
  standalone: true
})
export class MarkdownRenderPipe implements PipeTransform {
  private sanitizer = inject(DomSanitizer);

  transform(value: string | null | undefined): SafeHtml {
    if (!value) return '';

    // 1. Xử lý KaTeX trước khi đưa qua Marked (để tránh Marked làm hỏng cú pháp LaTeX)
    let renderedContent = this.renderMath(value);

    // 2. Chuyển đổi Markdown sang HTML
    let html: string;
    try {
      html = marked.parse(renderedContent) as string;
    } catch (e) {
      console.error('Marked parse error:', e);
      html = renderedContent; // Fallback to raw text if marked fails
    }

    // 3. Sanitize và trả về SafeHtml
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  private renderMath(text: string): string {
    // Render Block Math: $$ ... $$
    text = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, formula) => {
      try {
        return `<div class="katex-block">${katex.renderToString(formula, { displayMode: true, throwOnError: false })}</div>`;
      } catch (e) {
        console.error('KaTeX error:', e);
        return match;
      }
    });

    // Render Inline Math: $ ... $
    text = text.replace(/\$([\s\S]+?)\$/g, (match, formula) => {
      try {
        return katex.renderToString(formula, { displayMode: false, throwOnError: false });
      } catch (e) {
        console.error('KaTeX error:', e);
        return match;
      }
    });

    return text;
  }
}
