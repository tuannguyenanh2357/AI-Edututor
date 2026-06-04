# 📓 EduTutor Lessons Learned

Đây là nơi lưu trữ các bài học kinh nghiệm để AI tự cải thiện và giảm lỗi theo thời gian.

## 🎓 Kiến thức Bloom & Mastery
- *2026-05-07:* 
    - Cấu trúc Bloom chuẩn gồm 6 mức: 1. Nhận biết, 2. Thông hiểu, 3. Vận dụng, 4. Phân tích, 5. Đánh giá, 6. Sáng tạo.
    - Ngưỡng Mastery học tập tinh thông là **80%**. Dưới ngưỡng này phải học lại/remediation.
    - **Logic Skip:** Nếu Chapter Test >= 80%, tự động đánh dấu toàn bộ bài học trong chương là `COMPLETED` và mở khóa chương tiếp theo.

## 🛠️ Kỹ thuật & Hệ thống
- *2026-05-07:*
    - Khi sync PDF, cần chia nhỏ thành `ContentChunk` để AI xử lý RAG chính xác hơn, tránh bị tràn context window.
    - **Cảnh báo Tool:** Cẩn thận khi dùng `multi_replace_file_content` với các khối mã lớn hoặc range lân cận nhau. Tool có thể gây hỏng code nếu so khớp không chính xác. Ưu tiên dùng `replace_file_content` cho các hàm quan trọng.
    - **Bloom Analysis:** Luôn khởi tạo `bloom_stats` với đủ 6 mức (1-6) để tránh lỗi khi tính toán tỷ lệ phần trăm cho các mức không có câu hỏi nào.

## ⚠️ Quy trình & Kỷ luật (Protocol Adherence)
...
- *2026-05-11:*
    - **Database Migration vs Data Integrity:** Việc thay đổi Schema (như tách `Topic` từ `Lesson`) yêu cầu cập nhật lại toàn bộ scripts `sync` và `seed`. Nếu không có cơ chế "Fallback" (tạo placeholder Topic), dữ liệu phía sau (Questions) sẽ bị mất mắt xích liên kết.
    - **Redundant Fields:** Khi remote branch thêm trường mới (`difficulty_level`) thay thế trường cũ (`bloom_level`), phải chạy script đồng bộ hóa ngay sau khi migrate để tránh lỗi hiển thị trên Frontend.

- *2026-05-14:*
    - **AI JSON Robustness:** Raw json parsing requires aggressive regex escaping to handle LaTeX (\\). with_structured_output may fail internally with json.loads if the LLM output is not perfect.
    - **Polling Stability:** For background AI tasks, ALWAYS create a PENDING record upfront and add timeout checks in the polling endpoint to prevent infinite UI hangs.
# 📓 EduTutor Lessons Learned

Đây là nơi lưu trữ các bài học kinh nghiệm để AI tự cải thiện và giảm lỗi theo thời gian.

## 🎓 Kiến thức Bloom & Mastery
- *2026-05-07:* 
    - Cấu trúc Bloom chuẩn gồm 6 mức: 1. Nhận biết, 2. Thông hiểu, 3. Vận dụng, 4. Phân tích, 5. Đánh giá, 6. Sáng tạo.
    - Ngưỡng Mastery học tập tinh thông là **80%**. Dưới ngưỡng này phải học lại/remediation.
    - **Logic Skip:** Nếu Chapter Test >= 80%, tự động đánh dấu toàn bộ bài học trong chương là `COMPLETED` và mở khóa chương tiếp theo.

## 🛠️ Kỹ thuật & Hệ thống
- *2026-05-07:*
    - Khi sync PDF, cần chia nhỏ thành `ContentChunk` để AI xử lý RAG chính xác hơn, tránh bị tràn context window.
    - **Cảnh báo Tool:** Cẩn thận khi dùng `multi_replace_file_content` với các khối mã lớn hoặc range lân cận nhau. Tool có thể gây hỏng code nếu so khớp không chính xác. Ưu tiên dùng `replace_file_content` cho các hàm quan trọng.
    - **Bloom Analysis:** Luôn khởi tạo `bloom_stats` với đủ 6 mức (1-6) để tránh lỗi khi tính toán tỷ lệ phần trăm cho các mức không có câu hỏi nào.

## ⚠️ Quy trình & Kỷ luật (Protocol Adherence)
...
- *2026-05-11:*
    - **Database Migration vs Data Integrity:** Việc thay đổi Schema (như tách `Topic` từ `Lesson`) yêu cầu cập nhật lại toàn bộ scripts `sync` và `seed`. Nếu không có cơ chế "Fallback" (tạo placeholder Topic), dữ liệu phía sau (Questions) sẽ bị mất mắt xích liên kết.
    - **Redundant Fields:** Khi remote branch thêm trường mới (`difficulty_level`) thay thế trường cũ (`bloom_level`), phải chạy script đồng bộ hóa ngay sau khi migrate để tránh lỗi hiển thị trên Frontend.

- *2026-05-14:*
    - **AI JSON Robustness:** Raw json parsing requires aggressive regex escaping to handle LaTeX (\\). with_structured_output may fail internally with json.loads if the LLM output is not perfect.
    - **Polling Stability:** For background AI tasks, ALWAYS create a PENDING record upfront and add timeout checks in the polling endpoint to prevent infinite UI hangs.
    - **Batch Script Syntax:** Trong file .bat, các dấu ngoặc đơn ( hoặc ) nằm trong lệnh echo bên trong khối lệnh if/else SẼ LÀM GÃY KHỐI LỆNH VÀ CRASH SCRIPT NGAY LẬP TỨC. Luôn phải dùng ^( và ^) để escape.

- *2026-05-14 (Curriculum Hierarchy Refactor):*
    - Schema 4 cap: Part (Phan) > Chapter (chapter_type=CHAPTER|THEME) > Lesson (Bai) > Topic (Muc).
    - AI TOC Prompt moi trong pdf_extractor.py: tra ve cac truong phan, chu_de, chuong, bai.
    - sync_textbooks da cap nhat xu ly ca 2 format cu va moi (backward compatible).
    - Lesson co them page_start va page_end chinh thuc.

- *2026-05-15 (Question Bank Design):*
    - **Anti-Repeat Pattern:** Tách câu hỏi thành `unseen` + `seen_q` pools trước khi random → ưu tiên `unseen` → đảm bảo học sinh không bị lặp lại câu cũ khi làm lại.
    - **Post-Test Targeting:** Khi có LearningPath, dùng `LearningProgress.mastery_level=RED/YELLOW` để xác định weak topics → 70% slot dành cho weak topics → bài kiểm tra lại tập trung đúng điểm yếu.
    - **Answer Shuffle is Display-only:** Shuffle `answers[]` ở frontend dùng Fisher-Yates, nhưng submit vẫn dùng `ans.id` gốc → không cần thay đổi DB hay backend. Tuyệt đối không shuffle lại khi user đã select 1 đáp án (chỉ shuffle khi load).
    - **Mode Param Pattern:** Dùng `?mode=post_test` làm query param để phân biệt 2 luồng test trên cùng 1 endpoint → tránh tạo endpoint mới không cần thiết.

- *2026-05-16 (Refactoring Debug):*
    - **ImportError / Empty Response:** Nếu Frontend báo `ERR_EMPTY_RESPONSE`, 90% là Backend crash do `ImportError` hoặc Syntax Error sau khi refactor. Luôn check `docker logs` đầu tiên.
    - **Class Definition Safety:** Khi dùng `replace_file_content` trên các file lớn (>1000 lines), hãy đảm bảo không xóa nhầm dòng khai báo `class` hoặc `def` ngay phía trên khối code cần sửa. Luôn chạy `manage.py check` sau khi sửa logic phức tạp.
    - **Angular SSR Routing:** Khi dự án dùng Angular SSR (có file `app.routes.server.ts`), các route động có tham số (như `:submissionId`) BẮT BUỘC phải được khai báo trong `serverRoutes` với `RenderMode.Client`. Nếu không, Angular sẽ cố gắng Prerender route đó và trả về lỗi "Cannot match any routes" trên trình duyệt.
