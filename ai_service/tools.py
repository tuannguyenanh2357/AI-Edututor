import os
import httpx
import asyncio
from langchain_core.tools import tool
from pathlib import Path
from utils import get_gcp_credentials

# URL nội bộ của Django Backend
DJANGO_BACKEND_URL = os.environ.get("DJANGO_BACKEND_URL", "http://localhost:8000")

# ─────────────────────────────────────────────────
# Shared Search Client (Singleton)
# ─────────────────────────────────────────────────
_search_client = None

def get_search_client():
    global _search_client
    if _search_client is None:
        from google.cloud import discoveryengine
        creds = get_gcp_credentials()
        _search_client = discoveryengine.SearchServiceClient(credentials=creds)
    return _search_client

# ─────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────

@tool
def search_agent_builder(query: str) -> str:
    """Tìm kiếm kiến thức từ Sách giáo khoa (Vertex AI Search)."""
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("AGENT_BUILDER_LOCATION", "global")
    data_store_id = os.environ.get("DATA_STORE_ID")
    
    try:
        from google.cloud import discoveryengine
        client = get_search_client()
        serving_config = client.serving_config_path(
            project=project_id, location=location,
            data_store=data_store_id, serving_config="default_config"
        )
        request = discoveryengine.SearchRequest(serving_config=serving_config, query=query, page_size=10)
        response = client.search(request)
        
        results = []
        for res in response.results:
            doc = res.document
            struct_data = doc.derived_struct_data
            
            # Extract basic info
            title = struct_data.get("title", "Sách giáo khoa")
            link = struct_data.get("link", "")
            
            # Extract snippets and page numbers
            answers = struct_data.get("extractive_answers", [])
            for ans in answers:
                content = ans.get("content", "")
                page = ans.get("pageNumber", "N/A")
                if content:
                    results.append(f"[NGUỒN: {title}, TRANG: {page}]\n{content}\n(Liên kết: {link})")
            
        if not results: return f"Không tìm thấy tài liệu cho '{query}'."
        return "\n\n---\n\n".join(results[:3])
    except Exception as e:
        print(f"❌ [Search Error]: {e}")
        return f"Hiện không thể tra cứu dữ liệu từ sách giáo khoa do lỗi hệ thống: {str(e)}"

@tool
async def check_student_progress(student_id: int, subject: str = "", chapter: str = "", lesson_id: int = None, chapter_id: int = None) -> str:
    """Lấy thông tin tiến độ học tập, điểm yếu và chẩn đoán năng lực của học sinh. 
    Truyền lesson_id (ID bài học) để lọc chính xác câu sai của bài đó. Truyền chapter_id để lọc theo chương."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"student_id": student_id, "subject": subject}
            if chapter: params["chapter"] = chapter
            # Ưu tiên lọc theo ID (đầu vào chính xác nhất)
            if lesson_id: params["lesson_id"] = lesson_id
            if chapter_id: params["chapter_id"] = chapter_id
            response = await client.get(f"{DJANGO_BACKEND_URL}/api/users/progress", params=params)
            data = response.json()
            progress = data.get("progress", {})
            
            # Xây dựng báo cáo chi tiết cho AI
            summary = [
                f"--- BÁO CÁO TIẾN ĐỘ HỌC SINH (ID: {student_id}) ---",
                f"Môn học: {subject if subject else 'Tất cả'}",
                f"Điểm trung bình: {progress.get('average_score', 0):.1f}",
                f"Tổng số bài đã làm: {progress.get('total_quizzes', 0)}",
                f"Chiến lược học tập: {progress.get('learning_strategy', 'N/A')}",
            ]
            
            if progress.get('ai_diagnostic'):
                summary.append(f"Chẩn đoán từ AI: {progress['ai_diagnostic']}")
            
            weak_topics = progress.get('weak_topics', [])
            if weak_topics:
                summary.append("\nCÁC PHẦN KIẾN THỨC YẾU/CẦN CẢI THIỆN:")
                for topic in weak_topics:
                    level = topic.get('level', 'N/A')
                    errors = ", ".join(topic.get('errors', []))
                    summary.append(f"- {topic['title']} ({level}): {errors if errors else 'Cần học lại nền tảng'}")
            
            mastered_topics = progress.get('mastered_topics', [])
            if mastered_topics:
                summary.append("\nCÁC PHẦN ĐÃ LÀM CHỦ (GREEN):")
                summary.append(", ".join(mastered_topics))
                
            wrong_history = progress.get('recent_wrong_answers', [])
            if wrong_history:
                summary.append("\n[DỮ LIỆU BẮT BUỘC NIÊM YẾT - KHÔNG ĐƯỢC TÓM TẮT]")
                summary.append("Dưới đây là danh sách chi tiết các câu hỏi học sinh đã làm sai. Bạn PHẢI liệt kê nguyên văn các câu này:")
                for i, item in enumerate(wrong_history, 1):
                    summary.append(f"CÂU SAI #{i}:")
                    summary.append(f"- Chương: {item.get('chapter', 'Chung')}")
                    summary.append(f"- Câu hỏi: {item['question']}")
                    summary.append(f"- Học sinh chọn: {item['user_answer']}")
                    summary.append(f"- Đáp án đúng: {item['correct_answer']}")
                    summary.append(f"- Giải thích: {item['explanation']}")
                    summary.append("---")
            else:
                if not weak_topics:
                    summary.append("\nChưa ghi nhận điểm yếu cụ thể hoặc học sinh đã làm chủ kiến thức.")
                
            return "\n".join(summary)
    except Exception as e: 
        return f"Hiện không thể truy cập dữ liệu tiến độ: {str(e)}"

@tool
def generate_quick_quiz(topic: str, num_questions: int = 3) -> str:
    """Tạo nhanh câu hỏi trắc nghiệm ôn tập (Dùng cho Chat)."""
    return f"Hệ thống đang chuẩn bị {num_questions} câu hỏi về {topic}..."

@tool
def python_calculator(code: str) -> str:
    """Sử dụng Python để tính toán chính xác 100%."""
    try:
        from langchain_experimental.utilities import PythonREPL
        repl = PythonREPL()
        result = repl.run(code)
        return f"=== KẾT QUẢ MÁY TÍNH ===\n{result}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
async def read_textbook_page(page_number: int, subject: str = "Toán", grade_level: int = 10) -> str:
    """Đọc và phân tích một trang cụ thể trong sách giáo khoa."""
    # Tự động tìm đường dẫn media
    base_dir = Path(__file__).parent.parent
    media_path = base_dir / "backend" / "media" / "books" / "pdfs"
    if not media_path.exists():
        media_path = Path("/app/media/books/pdfs")
    
    from pdf_extractor import extract_pages_content
    prefix_map = {
        "toán": "Toan", "vật lý": "Ly", "hóa học": "Hoa", 
        "địa lý": "Dia", "lịch sử": "Su", "giáo dục công dân": "GDCD", "gdcd": "GDCD"
    }
    prefix = "Toan"
    for key, val in prefix_map.items():
        if key in subject.lower():
            prefix = val
            break
    
    # 1. Lọc đúng sách theo Lớp học
    search_pattern = f"{prefix}_{grade_level}*.pdf"
    matches = list(media_path.glob(search_pattern))
    if not matches:
        return f"Không tìm thấy tài liệu {subject} lớp {grade_level} (Mẫu tìm: {search_pattern})."
    
    pdf_file = str(matches[0])
    
    # 2. Logic Offset - Lấy từ Backend Django thay vì file JSON tĩnh
    offset = 0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Tìm subject tương ứng để lấy page_offset
            resp = await client.get(f"{DJANGO_BACKEND_URL}/api/subjects/", params={"name": subject, "grade_level": grade_level})
            if resp.status_code == 200:
                subjects = resp.json()
                if subjects and len(subjects) > 0:
                    offset = subjects[0].get("page_offset", 0)
    except Exception as e:
        print(f"⚠️ Không thể lấy offset từ backend: {e}")

    idx = page_number + offset - 1
    try:
        content = await extract_pages_content(pdf_file, idx, idx, fast_mode=True)
        return (
            f"=== NỘI DUNG SÁCH {subject.upper()} LỚP {grade_level} (Trang in: {page_number}, Trang PDF: {idx + 1}) ===\n"
            f"{content}\n"
            f"[NGUỒN: {subject} Lớp {grade_level}, TRANG: {page_number}]"
        )
    except Exception as e: 
        print(f"❌ [PDF Read Error]: {e}")
        return f"Không thể đọc trang {page_number} của sách {subject}. Vui lòng thử lại hoặc tra cứu chung."

ALL_TOOLS = [search_agent_builder, check_student_progress, generate_quick_quiz, read_textbook_page, python_calculator]
