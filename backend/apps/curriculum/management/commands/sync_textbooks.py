import os
import re
import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.subjects.models import Subject, SubjectDocument
from apps.curriculum.models import Part, Chapter, Lesson, Topic, ContentChunk


def get_ai_service_url():
    base_url = getattr(settings, 'AI_SERVICE_URL', 'http://ai_service:8001').rstrip('/')
    return f"{base_url}/api/v1/extract-toc"


def extract_number_from_title(text: str) -> str:
    """
    Tách số thứ tự CẤP CHƯƠNG từ tiêu đề.
    Chỉ dùng cho chapter, KHÔNG dùng cho lesson (vì dễ bị nhầm với số trong tên bài).
    VD: 'Chương 1: Mệnh đề' -> '1' | 'Chủ đề I: ...' -> 'I'
    """
    match = re.search(r'(?:Chương|Chủ đề|Phần|Chapter|Part)\s+(\d+|[IVXivx]+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    # Thử pattern "số đứng đầu: ..." hoặc "số. ..."
    match2 = re.match(r'^(\d+|[IVXivx]{1,4})[\.:\s]', text.strip())
    return match2.group(1) if match2 else ''


class Command(BaseCommand):
    help = 'Sync textbook TOC (Part > Chapter/Theme > Lesson > Topic) from AI Service'

    def add_arguments(self, parser):
        parser.add_argument('--subject_id', type=int, help='Subject ID to sync')
        parser.add_argument('--force', action='store_true', help='Force re-sync even if chapters exist')
        parser.add_argument('--debug', action='store_true', help='Print raw AI JSON response for debugging')

    def handle(self, *args, **options):
        # Fix Unicode for Windows terminal
        import sys, io
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        subject_id = options.get('subject_id')
        force = options.get('force', False)
        debug = options.get('debug', False)

        subjects = Subject.objects.filter(id=subject_id) if subject_id else Subject.objects.all()

        for subject in subjects:
            self.stdout.write(f"\n=== Syncing: [{subject.id}] {subject.name} (Lop {subject.grade_level}) ===")

            existing = Chapter.objects.filter(subject=subject).count()
            if existing > 0 and not force:
                self.stdout.write(f"   Skip: {existing} chapters exist. Use --force to re-sync.")
                continue

            docs = SubjectDocument.objects.filter(subject=subject).order_by('id')
            if not docs.exists():
                self.stdout.write(f"   Skip: No PDF found for Subject {subject.id}.")
                continue

            # Xóa toàn bộ dữ liệu cũ theo thứ tự CASCADE
            Part.objects.filter(subject=subject).delete()
            Chapter.objects.filter(subject=subject).delete()
            self.stdout.write(f"   Cleared old data.")

            chapter_order = 0
            lesson_order_global = 0


            seen_chapters = set()
            for doc in docs:
                pdf_path = f"/app/media/{str(doc.pdf_file)}"
                self.stdout.write(f"\n   --- Processing PDF: {pdf_path} ---")

                extract_url = get_ai_service_url()
                pages_url = extract_url.replace("/extract-toc", "/extract-pages")
                headers = {"X-AI-Service-Key": settings.AI_SERVICE_KEY}

                try:
                    # ── 1. Trích xuất TOC từ AI ────────────────────────────────────────
                    res = requests.post(extract_url, json={"pdf_path": pdf_path}, headers=headers, timeout=120)
                    if res.status_code != 200:
                        self.stdout.write(f"   [ERROR] AI returned {res.status_code}: {res.text[:300]}")
                        continue

                    data = res.json()

                    # ── 2. Debug: In raw JSON để kiểm tra AI trả về gì ─────────────────
                    if debug:
                        self.stdout.write(f"\n   [DEBUG] Raw AI JSON:\n{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}\n")

                    pdf_offset = int(data.get('pdf_offset', 0))

                    # ── Normalize cả 2 format sang format chuẩn nội bộ ────────────
                    # Format mới: data['cau_truc'] với keys: phan/chu_de/chuong/bai
                    # Format cũ:  data['chapters'] với keys: chapter_title/lessons
                    raw_blocks = data.get('cau_truc') or []
                    if not raw_blocks:
                        old_chapters = data.get('chapters', [])
                        for old_ch in old_chapters:
                            ch_title = str(old_ch.get('chapter_title', '')).strip()
                            lessons_raw = old_ch.get('lessons', [])
                            
                            # Flatten nested lessons (some AIs return Part > Chapter > Lesson)
                            def flatten_lessons(l_list):
                                flat = []
                                for item in l_list:
                                    if 'lessons' in item and isinstance(item['lessons'], list):
                                        flat.extend(flatten_lessons(item['lessons']))
                                    else:
                                        flat.append(item)
                                return flat
                                
                            flat_lessons = flatten_lessons(lessons_raw)
                            
                            # Suy luận: nếu title viết hoa toàn bộ hoặc không có prefix "Chương" 
                            # -> đây là "Chủ đề" (sách mới)
                            is_theme = (
                                ch_title.isupper() or
                                not re.search(r'^(Chương|Chapter)\s', ch_title, re.IGNORECASE)
                            )
                            normalized_lessons = []
                            for i, l in enumerate(flat_lessons):
                                normalized_lessons.append({
                                    'so_bai': str(i + 1),  # dùng index vì format cũ không có so_bai
                                    'ten_bai': l.get('lesson_title') or l.get('title', ''),
                                    'trang': l.get('page_start') or l.get('trang', 0),
                                })
                            raw_blocks.append({
                                'phan': '',
                                'chu_de': ch_title if is_theme else '',
                                'chuong': '' if is_theme else ch_title,
                                'bai': normalized_lessons,
                            })

                    if debug:
                        self.stdout.write(f"   [DEBUG] Normalized blocks ({len(raw_blocks)}):\n"
                                          f"{json.dumps(raw_blocks[:2], ensure_ascii=False, indent=2)}\n")

                    subject.page_offset = pdf_offset
                    subject.save()
                    self.stdout.write(f"   PDF Offset: {pdf_offset} | Blocks: {len(raw_blocks)}")

                    for block in raw_blocks:
                        # ── 3. Cấp PHẦN (Part) ────────────────────────────────────────
                        phan_title = str(block.get('phan') or '').strip()
                        part_obj = None
                        if phan_title:
                            part_obj, _ = Part.objects.get_or_create(
                                subject=subject,
                                title=phan_title,
                                defaults={'order_num': chapter_order}
                            )

                        # ── 4. Cấp CHƯƠNG hoặc CHỦ ĐỀ ────────────────────────────────
                        raw_chuong = str(block.get('chuong') or '').strip()
                        raw_chu_de = str(block.get('chu_de') or '').strip()

                        if raw_chu_de:
                            chapter_type = 'THEME'
                            display_title = raw_chu_de
                        elif raw_chuong:
                            chapter_type = 'CHAPTER'
                            display_title = raw_chuong
                        elif phan_title:
                            # Nếu chỉ có Phần, kiểm tra xem có bài học đi kèm không
                            bai_list = block.get('bai', block.get('lessons', []))
                            if not bai_list:
                                self.stdout.write(f"   [PART ONLY] {phan_title}")
                                continue
                            chapter_type = 'THEME'
                            display_title = phan_title
                        else:
                            continue

                        # Chống trùng lặp
                        if display_title in seen_chapters:
                            if debug: self.stdout.write(f"   [SKIP DUPE] {display_title}")
                            continue
                        seen_chapters.add(display_title)

                        self.stdout.write(f"\n   [{chapter_type}] {display_title}")
                        
                        ten_chuong_val = display_title if chapter_type == 'CHAPTER' else None
                        ten_chu_de_val = display_title if chapter_type == 'THEME' else None
                        chapter_number = extract_number_from_title(display_title)

                        chapter_obj = Chapter.objects.create(
                            subject=subject,
                            part=part_obj,
                            chapter_type=chapter_type,
                            title=display_title,
                            ten_chuong=ten_chuong_val,
                            ten_chu_de=ten_chu_de_val,
                            chapter_number=chapter_number,
                            order_num=chapter_order,
                        )
                        chapter_order += 1

                        # ── 5. Các BÀI trong Chương/Chủ đề ──────────────────────────
                        bai_list = block.get('bai', block.get('lessons', []))
                        lesson_order_in_chapter = 0
                        seen_lessons_in_chapter = set()
                        last_page_in_chapter = 0

                        for l_info in bai_list:
                            l_title = str(l_info.get('ten_bai') or l_info.get('lesson_title') or '').strip()
                            
                            # Chống trùng lặp bài học trong cùng chương
                            if not l_title or l_title in seen_lessons_in_chapter:
                                continue
                            seen_lessons_in_chapter.add(l_title)

                            if any(kw in l_title.upper() for kw in ['CHƯƠNG', 'CHAPTER']):
                                continue

                            # Kiểm tra số trang để tránh AI nhảy ngược về đầu sách (Rác dữ liệu)
                            raw_trang = l_info.get('trang') or l_info.get('page_start') or 0
                            try:
                                p_start_printed = int(raw_trang)
                            except (ValueError, TypeError):
                                p_start_printed = 0

                            # Nếu trang bài sau nhỏ hơn trang bài trước quá nhiều (ví dụ > 50 trang) 
                            # thì khả năng cao là AI đang nạp nhầm bài của chương khác.
                            if last_page_in_chapter > 0 and p_start_printed < last_page_in_chapter - 5:
                                if debug: self.stdout.write(f"      [SKIP] Trang nhảy ngược: {l_title} (Trang {p_start_printed} < {last_page_in_chapter})")
                                continue
                            last_page_in_chapter = p_start_printed

                            raw_so_bai = str(l_info.get('so_bai') or '').strip()
                            l_number = raw_so_bai if raw_so_bai and raw_so_bai.isdigit() else str(lesson_order_in_chapter + 1)

                            pdf_page_start = p_start_printed + pdf_offset
                            pdf_page_end = pdf_page_start + 3

                            lesson_obj = Lesson.objects.create(
                                chapter=chapter_obj,
                                title=l_title,
                                lesson_number=l_number,
                                page_start=p_start_printed,
                                page_end=p_start_printed + 3,
                                content=f"[PAGE {pdf_page_start}-{pdf_page_end}]",
                                order_num=lesson_order_global,
                            )
                            lesson_order_in_chapter += 1
                            lesson_order_global += 1

                            self.stdout.write(
                                f"      [BAI {l_number}] {l_title} "
                                f"(Trang in: {p_start_printed}, PDF idx: {pdf_page_start})"
                            )

                            # ── 6. Trích xuất nội dung RAG ─────────────────────────
                            rag_content = ''
                            try:
                                r = requests.post(
                                    pages_url,
                                    json={"pdf_path": pdf_path, "start_page": pdf_page_start, "end_page": pdf_page_end},
                                    headers=headers, timeout=300
                                )
                                if r.status_code == 200:
                                    rag_content = r.json().get('content', '')
                                    if rag_content:
                                        rag_content = rag_content.strip()
                                        self.stdout.write(f"         RAG extracted ({len(rag_content)} chars)")
                            except Exception as e:
                                self.stdout.write(f"         RAG error: {e}")

                            # ── 7. Tạo Topic mặc định ──────────────────────────────
                            topic_obj = Topic.objects.create(
                                lesson=lesson_obj,
                                title=f"Nội dung: {l_title}",
                                content=rag_content[:500] + '...' if rag_content else 'Đang cập nhật...',
                                order_num=1,
                            )
                            if rag_content:
                                ContentChunk.objects.create(
                                    topic=topic_obj,
                                    raw_content=rag_content,
                                    page_number=pdf_page_start,
                                    chunk_index=1,
                                )

                except Exception as e:
                    self.stdout.write(f"   [ERROR] Sync failed for {pdf_path}: {e}")

            self.stdout.write(
                f"\n   SUCCESS: Subject {subject.id} synced — "
                f"{chapter_order} chapters/themes, {lesson_order_global} lessons."
            )


