"""
main.py — Điểm vào (Entry Point) của AI Service.
"""

import os
import json
import asyncio
import httpx
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from pdf_extractor import extract_toc_from_pdf, extract_pages_content

# ─────────────────────────────────────────────────
# Shared Utilities
# ─────────────────────────────────────────────────

def robust_json_parse(text: str) -> dict:
    """Trích xuất và làm sạch JSON từ phản hồi của AI, xử lý lỗi LaTeX/Unicode."""
    import re
    import json
    try:
        # 1. Tìm khối JSON bằng regex
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return None
        
        raw_json = json_match.group(0)
        
        # 2. Sanitize: Thoát các dấu backslash không hợp lệ (thường gặp ở LaTeX \frac, \sqrt...)
        # Chỉ thoát nếu nó không phải là các ký tự escape JSON chuẩn
        sanitized_json = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw_json)
        
        # 3. Parse JSON
        return json.loads(sanitized_json)
    except Exception as e:
        print(f"⚠️ [Robust JSON Parse Failed]: {e}")
        return None

# Load environment variables
load_dotenv(override=True)

from agent import AgentFactory
from langchain_core.messages import HumanMessage, AIMessage

# Initialize LLM early
_llm_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo tài nguyên khi app start."""
    global _llm_ready
    try:
        AgentFactory.get_llm()
        _llm_ready = True
        print("✅ [AI Service] Gemini LLM đã sẵn sàng.")
    except Exception as e:
        print(f"❌ [AI Service] Lỗi khởi tạo LLM: {e}")
    yield

app = FastAPI(lifespan=lifespan, title="EduTutor AI Service")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Middleware
AI_SERVICE_KEY = os.environ.get("AI_SERVICE_KEY", "dev-ai-key-edututor-2024")

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method != "OPTIONS":
        key = request.headers.get("X-AI-Service-Key", "")
        if key != AI_SERVICE_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid or missing API key."}
            )
    return await call_next(request)

# ─────────────────────────────────────────────────
# Endpoint 1: Chat Streaming (Agentic Loop)
# ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: str = None
    ai_preferences: str = ""
    chat_history: list = []
    subject_name: str = "Chung" # Thêm để AI biết đang học môn nào
    subject_id: int = None
    grade_level: int = 10
    student_id: int = None # Thêm ID học sinh để AI truy vấn tiến độ
    image_data: str = None # Base64 data URL

def _format_sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest):
    if not _llm_ready:
        raise HTTPException(status_code=503, detail="AI Service is starting up...")

    async def event_generator():
        try:
            # Lấy đồ thị agent (Multi-Agent StateGraph)
            agent_graph = AgentFactory.get_agent(request.subject_name)
            
            # Cấu hình bộ nhớ phiên học
            # Tạo UUID ngẫu nhiên để tránh lỗi ghi đè/nhân bản lịch sử của MemorySaver in-memory
            import uuid
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            from langchain_core.messages import HumanMessage, AIMessage
            
            print(f"🚀 [Chat] User: {request.student_id}, Subject: {request.subject_name}, Msg: {request.message[:50]}...")
            
            # Khôi phục toàn bộ lịch sử từ frontend truyền lên (không phụ thuộc vào RAM)
            messages_list = []
            for msg in request.chat_history:
                role = msg.get('role', 'human')
                content = msg.get('content', '')
                if role in ['human', 'user']:
                    messages_list.append(HumanMessage(content=content))
                else:
                    messages_list.append(AIMessage(content=content))

            # Chuẩn bị tin nhắn hiện tại
            if request.image_data:
                user_content = [
                    {"type": "text", "text": request.message},
                    {"type": "image_url", "image_url": {"url": request.image_data}}
                ]
                messages_list.append(HumanMessage(content=user_content))
            else:
                messages_list.append(HumanMessage(content=request.message))

            # Thực thi đồ thị dưới dạng stream
            async for event in agent_graph.astream_events(
                {
                    "messages": messages_list, 
                    "subject_name": request.subject_name,
                    "grade_level": request.grade_level,
                    "student_id": request.student_id,  # TRUYỀN ID HỌC SINH VÀO GRAPH
                    "ai_preferences": request.ai_preferences
                },
                config=config,
                version="v1"
            ):
                event_type = event["event"]

                # 1. Stream nội dung từ AI (Lọc bỏ Reviewer)
                if event_type == "on_chat_model_stream":
                    if not event or not isinstance(event, dict): continue
                    
                    # Lấy tên node hiện tại từ metadata
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    
                    # Chỉ cho phép stream từ Planner và Synthesizer
                    if node_name != "reviewer":
                        chunk = event.get("data", {}).get("chunk", {})
                        if chunk:
                            content = getattr(chunk, "content", "") or ""
                            if content:
                                yield _format_sse({"type": "token", "content": content})

                # 2. Thông báo khi các Tool đang chạy
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "")
                    status_text = "Đang tính toán..." if tool_name == "python_calculator" else f"Đang tra cứu: {tool_name}..."
                    yield _format_sse({"type": "tool_start", "content": status_text})

                # 3. Thông báo khi Reviewer đang phản biện (Elite Feature)
                elif event_type == "on_chain_start" and event.get("name") == "reviewer":
                    yield _format_sse({"type": "tool_start", "content": "🔍 Đang kiểm tra độ chính xác..."})

                # 4. Phát hiện và gửi Trích dẫn (Citations)
                elif event_type == "on_chain_end" and event.get("name") == "synthesizer":
                    citations = event.get("data", {}).get("output", {}).get("citations", [])
                    if citations:
                        yield _format_sse({"type": "citations", "content": citations})
                
                # 5. Thông báo Ý định (Intent) ngay khi Planner hoàn tất
                elif event_type == "on_chain_end" and event.get("name") == "planner":
                    intent = event.get("data", {}).get("output", {}).get("intent", "EXPLAIN")
                    yield _format_sse({"type": "intent", "content": intent})

            yield _format_sse({"type": "done", "content": ""})

        except Exception as exc:
            print(f"❌ [Chat Error]: {exc}")
            yield _format_sse({"type": "error", "content": str(exc)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ─────────────────────────────────────────────────
# Endpoint 2: Generate Granular AI Quiz
# ─────────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    subject_name: str
    grade_level: int = 10
    chapter_title: str
    num_questions: int = 5
    lesson_id: int = None

from pydantic import BaseModel, Field
from typing import List

class QuizQuestion(BaseModel):
    question: str = Field(..., description="Nội dung câu hỏi")
    options: List[str] = Field(..., description="Danh sách 4 lựa chọn")
    correct_index: int = Field(..., description="Chỉ số đáp án đúng (0-3)")
    explanation: str = Field(..., description="Giải thích chi tiết lý do đáp án đó đúng")
    bloom_level: int = Field(..., description="Cấp độ Bloom (1-6)")
    difficulty_score: float = Field(..., description="Độ khó chi tiết (1.0 - 10.0)")
    is_boss_question: bool = Field(default=False, description="Đánh dấu nếu đây là câu hỏi khó/chốt hạ")

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

@app.post("/api/v1/generate-quiz")
async def generate_quiz(request: QuizGenerateRequest):
    llm = AgentFactory.get_llm()
    lesson_content = ""
    target_topic = request.chapter_title

    # 1. RAG Logic (Giữ nguyên phần đọc PDF)
    if request.lesson_id:
        try:
            backend_url = os.environ.get("DJANGO_BACKEND_URL", "http://backend:8000")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{backend_url}/api/curriculum/lessons/{request.lesson_id}/", timeout=10)
                if resp.status_code == 200:
                    lesson_data = resp.json()
                    raw_content = lesson_data.get("content") or ""
                    
                    if not raw_content:
                        print(f"⚠️ Lesson {request.lesson_id} has no content tags.")
                        # Fallback: target_topic vẫn được lấy từ lesson_data
                        target_topic = lesson_data.get('title', target_topic)
                    else:
                        import re
                    page_match = re.search(r'\[PAGE\s+(\d+)-(\d+)\]', raw_content)
                    if not page_match:
                         page_match = re.search(r'\[PAGE_START:(\d+)\]', raw_content)
                    
                    page_start = int(page_match.group(1)) if page_match else 0
                    page_end = int(page_match.group(2)) if (page_match and len(page_match.groups()) > 1) else page_start + 2
                    
                    media_path = Path("/app/media/books/pdfs")
                    prefix_map = {
                        "toán": "Toan", "vật lý": "Ly", "hóa học": "Hoa", 
                        "địa lý": "Dia", "lịch sử": "Su", "giáo dục công dân": "GDCD", "gdcd": "GDCD"
                    }
                    sub_name = (request.subject_name or "Toán").lower()
                    prefix = "Toan" # Default
                    for key, val in prefix_map.items():
                        if key in sub_name:
                            prefix = val
                            break
                    
                    matches = list(media_path.glob(f"{prefix}_{request.grade_level}*.pdf"))
                    if matches:
                        pdf_file = str(matches[0])
                        lesson_content = await extract_pages_content(pdf_file, page_start, page_end)
                        target_topic = lesson_data['title']
        except Exception as e:
            print(f"⚠️ RAG failed: {e}")

    # 2. Xây dựng Prompt Dynamic dựa trên môn học
    custom_context = getattr(request, 'context', '')
    
    # Định nghĩa phong cách riêng cho từng nhóm môn
    subject_instructions = ""
    sub_name = request.subject_name.lower()
    
    if any(m in sub_name for m in ["toán", "vật lý", "hóa học"]):
        subject_instructions = (
            "PHONG CÁCH TỰ NHIÊN: Tập trung vào tính toán, công thức và suy luận logic.\n"
            "- Công thức BẮT BUỘC dùng LaTeX ($...$).\n"
            "- Giải thích phải có các bước biến đổi toán học/vật lý/hóa học rõ ràng.\n"
            "- Tránh các câu hỏi lý thuyết suông hoặc hỏi về lệnh phần mềm."
        )
    elif any(m in sub_name for m in ["lịch sử", "địa lý"]):
        subject_instructions = (
            "PHONG CÁCH XÃ HỘI: Tập trung vào sự kiện, mốc thời gian, nguyên nhân và bản chất vấn đề.\n"
            "- Câu hỏi phải yêu cầu học sinh phân tích thay vì chỉ nhớ máy móc.\n"
            "- Giải thích phải liên kết các sự kiện/hiện tượng theo logic thực tế."
        )
    elif "giáo dục công dân" in sub_name or "gdcd" in sub_name:
        subject_instructions = (
            "PHONG CÁCH TÌNH HUỐNG: Tập trung vào các câu chuyện thực tế (Case study).\n"
            "- Ưu tiên các câu hỏi về hành vi, đạo đức và áp dụng quy định pháp luật.\n"
            "- Giải thích phải nêu rõ hành vi đó đúng hay sai theo quy định nào."
        )
    else:
        subject_instructions = "Hãy soạn câu hỏi chuẩn sư phạm, bám sát nội dung cung cấp."

    prompt_text = (
        f"BẠN LÀ CHUYÊN GIA KHẢO THÍ CHIẾN LƯỢC THEO PHƯƠNG PHÁP MASTERY LEARNING & BLOOM TAXONOMY.\n"
        f"Mục tiêu: Thiết kế bộ câu hỏi phân hóa cực tốt cho bài: \"{target_topic}\" (Lớp {request.grade_level}).\n\n"
        f"BẮT BUỘC TUÂN THỦ TỶ LỆ PHÂN TẦNG (Với {request.num_questions} câu):\n"
        f"1. Mức 1 & 2 (Nhận biết/Thông hiểu): Chiếm 60% (Ví dụ: 3/5 câu). Bloom: 1-2. Difficulty: 1-4.\n"
        f"2. Mức 3 (Vận dụng): Chiếm 20% (Ví dụ: 1/5 câu). Bloom: 3. Difficulty: 5-7. Yêu cầu áp dụng công thức/tình huống.\n"
        f"3. Mức 4 & 5 (Phân tích/Đánh giá): Chiếm 20% (Ví dụ: 1/5 câu). Bloom: 4-5. Difficulty: 8-10. Yêu cầu suy luận phức tạp.\n\n"
        f"--- NỘI DUNG GỐC (BẮT BUỘC BÁM SÁT) ---\n"
        f"{custom_context if custom_context else lesson_content}\n"
        f"--- KẾT THÚC ---\n\n"
        f"YÊU CẦU RIÊNG MÔN {request.subject_name.upper()}:\n"
        f"{subject_instructions}\n\n"
        f"LƯU Ý QUAN TRỌNG:\n"
        f"- KHÔNG được để tất cả câu hỏi đều ở Bloom 1.\n"
        f"- 'bloom_level' phải là số nguyên từ 1 đến 6.\n"
        f"- 'difficulty_score' phải tương ứng với mức Bloom (Ví dụ: Bloom 4 thì Difficulty phải >= 7)."
    )

    try:
        # Ép mô hình trả về đúng cấu trúc QuizResponse
        structured_llm = llm.with_structured_output(QuizResponse)
        
        # Thử gọi AI tối đa 2 lần nếu trả về None
        result = None
        for attempt in range(2):
            result = await asyncio.to_thread(structured_llm.invoke, prompt_text)
            if result and result.questions:
                break
            print(f"⚠️ [Quiz Gen] Attempt {attempt+1} returned None, retrying...")

        if not result or not result.questions:
            print("❌ [Quiz Gen] AI failed to generate structured output after retries.")
            raise HTTPException(status_code=500, detail="AI failed to generate structured quiz data.")
            
        # Sử dụng model_dump() (Pydantic v2) để đảm bảo JSON serializable
        questions_list = []
        for q in result.questions:
            questions_list.append({
                "question": q.question,
                "options": q.options,
                "correct_index": q.correct_index,
                "explanation": q.explanation,
                "bloom_level": q.bloom_level,
                "difficulty_score": q.difficulty_score,
                "is_boss_question": q.is_boss_question
            })
            
        return {"questions": questions_list, "count": len(questions_list)}
    except Exception as e:
        print(f"❌ [Quiz Structured Error]: {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────
# Endpoint 3: Generate Diagnostic Pre-Test
# ─────────────────────────────────────────────────

class PreTestGenerateRequest(BaseModel):
    subject_name: str
    grade_level: int = 10
    num_questions: int = 10

class PreTestQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str
    chapter_title: str # Bắt buộc để biết câu hỏi thuộc chương nào

class PreTestResponse(BaseModel):
    questions: List[PreTestQuestion]

@app.post("/api/v1/generate-pretest")
async def generate_pretest(request: PreTestGenerateRequest):
    llm = AgentFactory.get_llm()
    prompt_text = (
        f"Bạn là chuyên gia khảo thí môn {request.subject_name} lớp {request.grade_level} tại Việt Nam.\n"
        f"Hãy soạn một bài kiểm tra đầu vào (Pre-test) gồm đúng {request.num_questions} câu hỏi.\n"
        "Các câu hỏi phải bao phủ nhiều chương/chủ đề khác nhau của chương trình học.\n"
        "Mọi công thức toán học BẮT BUỘC phải bọc trong cặp dấu $...$.\n"
        "Ghi rõ 'chapter_title' cho từng câu hỏi."
    )

    try:
        structured_llm = llm.with_structured_output(PreTestResponse)
        result = await asyncio.to_thread(structured_llm.invoke, prompt_text)
        
        return {"questions": [q.model_dump() for q in result.questions]}
    except Exception as e:
        print(f"❌ [PreTest Gen Error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────
# Endpoint 4: Evaluate Pre-Test Results
# ─────────────────────────────────────────────────

class PreTestEvaluateRequest(BaseModel):
    user_id: int
    subject_id: int
    subject_name: str
    grade_level: int
    score: float
    wrong_chapters: List[str]
    chapter_scores: dict = {}

@app.post("/api/v1/evaluate-pretest")
async def evaluate_pretest(request: PreTestEvaluateRequest):
    llm = AgentFactory.get_llm()
    
    # ── [NÂNG CẤP] Xử lý dữ liệu chẩn đoán chi tiết ──
    chapter_performance = ""
    if request.chapter_scores:
        chapter_performance = "\nĐIỂM CHI TIẾT THEO CHƯƠNG:\n"
        for ch, s in request.chapter_scores.items():
            chapter_performance += f"- {ch}: {s}%\n"

    prompt_text = (
        f"BẠN LÀ CHUYÊN GIA GIÁO DỤC CÁ NHÂN HÓA.\n"
        f"Học sinh (Lớp {request.grade_level}) vừa hoàn thành bài Pre-test môn {request.subject_name}.\n"
        f"TỔNG ĐIỂM: {request.score}%\n"
        f"{chapter_performance}\n"
        f"Dựa trên dữ liệu trên, hãy thực hiện:\n"
        f"1. Phân loại Mastery (Đỏ/Vàng/Xanh) cho từng chương:\n"
        f"   - RED (Đỏ - <50%): Hổng kiến thức nặng, cần học lại từ đầu.\n"
        f"   - YELLOW (Vàng - 50-84%): Nắm được cơ bản nhưng còn nhầm lẫn, cần luyện tập thêm.\n"
        f"   - GREEN (Xanh - >=85%): Đã làm chủ, có thể bỏ qua.\n"
        f"2. Xác định 'Root Cause' (Nguyên nhân): Học sinh đang gặp vấn đề gì? (ẩu, hổng nền tảng, hay tư duy chưa tới).\n"
        f"3. Đề xuất Strategy: 'foundation', 'standard', hoặc 'advanced'.\n\n"
        f"TRẢ VỀ JSON DUY NHẤT: \n"
        f"{{\n"
        f"  \"strategy\": \"...\",\n"
        f"  \"feedback\": \"... (viết ngắn gọn, khích lệ)\",\n"
        f"  \"mastery_map\": {{\"Tên chương\": \"RED/YELLOW/GREEN\", ...}},\n"
        f"  \"error_analysis\": [\"tag1\", \"tag2\", ...]\n"
        f"}}\n"
        f"LƯU Ý VỀ FORMAT: TRẢ VỀ CHUẨN JSON. KHÔNG SỬ DỤNG BACKSLASH (\) TRONG NHẬN XÉT, HOẶC NẾU CÓ PHẢI ESCAPE ĐẦY ĐỦ (\\\\)."
    )

    try:
        resp = await asyncio.to_thread(llm.invoke, prompt_text)
        data = robust_json_parse(resp.content)
        if not data:
            data = {"strategy": "standard", "feedback": "Đã ghi nhận kết quả."}

        # ── QUAN TRỌNG: Gửi Mastery Map về Backend ──
        backend_url = os.environ.get("DJANGO_BACKEND_URL", "http://backend:8000")
        internal_key = os.environ.get("INTERNAL_API_KEY", "internal-service-key-2024")
        
        async with httpx.AsyncClient() as client:
            backend_resp = await client.post(
                f"{backend_url}/api/internal/create-learning-path/",
                json={
                    "user_id": request.user_id,
                    "subject_id": request.subject_id,
                    "score": request.score,
                    "strategy": data.get("strategy", "standard"),
                    "ai_feedback": data.get("feedback", ""),
                    "mastery_map": data.get("mastery_map", {}),
                    "error_tags": data.get("error_analysis", [])
                },
                headers={"X-Internal-Key": internal_key},
                timeout=30.0
            )
            
            if backend_resp.status_code == 200:
                data['learning_path_id'] = backend_resp.json().get('learning_path_id')

        return {"status": "ok", "analysis": data, "learning_path_id": data.get('learning_path_id')}
    except Exception as e:
        print(f"❌ [PreTest Eval Error]: {e}")
        return {"status": "error", "message": str(e)}

# ─────────────────────────────────────────────────
# Endpoint 5: Evaluate Chapter Test (MAIN FLOW)
# ─────────────────────────────────────────────────

class ChapterTestEvaluateRequest(BaseModel):
    user_id: int
    subject_id: int
    chapter_id: int
    chapter_title: str
    subject_name: str
    grade_level: int
    score: float
    wrong_details: List[dict] = []

class MasteryDetail(BaseModel):
    level: str = Field(..., description="RED, YELLOW, or GREEN")
    specific_errors: List[str] = Field(default_factory=list, description="Danh sách lỗi cụ thể")

class ChapterEvalResponse(BaseModel):
    strategy: str = Field(..., description="foundation, standard, or advanced")
    feedback: str = Field(..., description="Nhận xét ngắn gọn, khích lệ")
    mastery_map: Dict[str, MasteryDetail] = Field(..., description="Map tên phần kiến thức -> chi tiết mastery")

@app.post("/api/v1/evaluate-chapter-test")
async def evaluate_chapter_test(request: ChapterTestEvaluateRequest):
    """
    Đây là endpoint CHÍNH thay thế evaluate-pretest.
    Phân tích kết quả Chapter Test → tạo LearningPath theo chương.
    """
    llm = AgentFactory.get_llm()

    wrong_text = ""
    if request.wrong_details:
        wrong_text = "\nCHI TIẾT CÁC CÂU LÀM SAI CỦA HỌC SINH:\n"
        for detail in request.wrong_details:
            wrong_text += f"- Câu hỏi: {detail.get('question')}\n"
            wrong_text += f"  Phần kiến thức: {detail.get('topic')}\n"
            wrong_text += f"  Học sinh chọn: {detail.get('student_chose')} (Sai)\n"
            wrong_text += f"  Đáp án Đúng: {detail.get('correct_answer')}\n\n"

    prompt_text = (
        f"BẠN LÀ CHUYÊN GIA GIÁO DỤC CÁ NHÂN HÓA.\n"
        f"Học sinh (Lớp {request.grade_level}) vừa hoàn thành bài Đánh giá đầu vào Chương '{request.chapter_title}' môn {request.subject_name}.\n"
        f"TỔNG ĐIỂM: {request.score}%\n"
        f"{wrong_text}\n"
        f"Dựa trên dữ liệu chi tiết ở trên, hãy thực hiện:\n"
        f"1. Phân loại Mastery (Đỏ/Vàng/Xanh) cho từng phần kiến thức (dựa trên topic của các câu sai và đúng):\n"
        f"   - RED (Đỏ - <50%): Hổng kiến thức nặng, học sinh chọn các đáp án cho thấy sự sai lầm cơ bản. Cần học lại.\n"
        f"   - YELLOW (Vàng - 50-84%): Nắm được cơ bản nhưng còn nhầm lẫn (có thể tính toán sai, hoặc hiểu chưa sâu).\n"
        f"   - GREEN (Xanh - >=85%): Đã làm chủ.\n"
        f"2. Cho mỗi phần kiến thức (đặc biệt là RED và YELLOW), chỉ ra ĐÚNG LỖI SAI (specific_errors) dựa trên câu hỏi và đáp án học sinh đã chọn sai.\n"
        f"3. Đề xuất Strategy: 'foundation', 'standard', hoặc 'advanced'.\n\n"
        f"LƯU Ý QUAN TRỌNG: Hãy phân tích thật kỹ các câu sai để tìm ra lỗi hổng kiến thức thực sự.\n"
        f"LƯU Ý VỀ FORMAT: TRẢ VỀ CHUẨN JSON. KHÔNG SỬ DỤNG BACKSLASH (\) TRONG NHẬN XÉT, HOẶC NẾU CÓ PHẢI ESCAPE ĐẦY ĐỦ (\\\\)."
    )

    try:
        # Sử dụng raw invoke và tự sanitize JSON để tránh lỗi 'Invalid \escape' với công thức Toán/LaTeX
        resp = await asyncio.to_thread(llm.invoke, prompt_text)
        data = robust_json_parse(resp.content)
        if not data:
            # Fallback nếu parse vẫn lỗi
            data = {"strategy": "standard", "feedback": "Đã ghi nhận kết quả. Đang xử lý lộ trình...", "mastery_map": {}}

        # Gửi về Backend để tạo LearningPath chapter-based
        backend_url = os.environ.get("DJANGO_BACKEND_URL", "http://backend:8000")
        internal_key = os.environ.get("INTERNAL_API_KEY", "internal-service-key-2024")

        async with httpx.AsyncClient() as client:
            backend_resp = await client.post(
                f"{backend_url}/api/internal/create-chapter-learning-path/",
                json={
                    "user_id": request.user_id,
                    "subject_id": request.subject_id,
                    "chapter_id": request.chapter_id,
                    "score": request.score,
                    "strategy": data.get("strategy", "standard"),
                    "ai_feedback": data.get("feedback", ""),
                    "mastery_map": data.get("mastery_map", {})
                },
                headers={"X-Internal-Key": internal_key},
                timeout=30.0
            )
            if backend_resp.status_code == 200:
                data['learning_path_id'] = backend_resp.json().get('learning_path_id')

        return {"status": "ok", "analysis": data, "learning_path_id": data.get('learning_path_id')}
    except Exception as e:
        print(f"❌ [Chapter Eval Error]: {e}")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────
# Endpoint 6: Evaluate Post-Test (FINAL ASSESSMENT)
# ─────────────────────────────────────────────────

class PostTestEvaluateRequest(BaseModel):
    user_id: int
    subject_id: int
    chapter_id: int
    chapter_title: str
    subject_name: str
    grade_level: int
    pre_test_score: float   # Điểm bài đánh giá đầu vào
    post_test_score: float  # Điểm bài kiểm tra cuối chương
    wrong_details: List[dict] = []

@app.post("/api/v1/evaluate-post-test")
async def evaluate_post_test(request: PostTestEvaluateRequest):
    """
    Endpoint đánh giá bài kiểm tra cuối chương (Post-test).
    So sánh Pre-test vs Post-test → AI đưa ra nhận xét tiến bộ.
    """
    llm = AgentFactory.get_llm()

    improvement = request.post_test_score - request.pre_test_score
    improvement_text = f"+{improvement:.1f}%" if improvement >= 0 else f"{improvement:.1f}%"

    wrong_summary = ""
    if request.wrong_details:
        wrong_summary = "\nCÁC CÂU HỎI CÒN SAI TRONG BÀI KIỂM TRA CUỐI:\n"
        for d in request.wrong_details[:5]:  # Tối đa 5 câu để prompt không quá dài
            wrong_summary += f"- {d.get('question', '')}: chọn '{d.get('student_chose', '')}', đúng là '{d.get('correct_answer', '')}'\n"

    mastery_verdict = ""
    if request.post_test_score >= 80:
        mastery_verdict = "ĐẠT MASTERY: Học sinh đã thành thạo chương này."
    elif request.post_test_score >= 60:
        mastery_verdict = "GẦN ĐẠT: Học sinh đã tiến bộ rõ rệt nhưng cần cố gắng thêm."
    else:
        mastery_verdict = "CHƯA ĐẠT: Học sinh cần ôn lại một số phần kiến thức quan trọng."

    prompt_text = (
        f"BẠN LÀ GIA SƯ AI THÂN THIỆN, đang đánh giá kết quả học tập của học sinh lớp {request.grade_level}.\n"
        f"Chương: '{request.chapter_title}' — Môn: {request.subject_name}\n\n"
        f"KẾT QUẢ HỌC TẬP:\n"
        f"- Điểm trước khi học (Pre-test đầu vào): {request.pre_test_score:.1f}%\n"
        f"- Điểm sau khi học (Post-test cuối chương): {request.post_test_score:.1f}%\n"
        f"- Mức độ tiến bộ: {improvement_text}\n"
        f"- Đánh giá: {mastery_verdict}\n"
        f"{wrong_summary}\n"
        f"NHIỆM VỤ CỦA BẠN:\n"
        f"Viết một đoạn nhận xét NGẮN GỌN (3-5 câu), ẤM ÁP và CÁ NHÂN HÓA:\n"
        f"1. Ghi nhận sự tiến bộ của học sinh (dù nhiều hay ít).\n"
        f"2. Chỉ ra điểm mạnh cụ thể dựa trên điểm số.\n"
        f"3. Nếu chưa đạt 80%, gợi ý ngắn gọn cần chú ý thêm phần nào. Nếu đã đạt, hãy chúc mừng.\n"
        f"4. Kết thúc bằng lời động viên tích cực.\n\n"
        f"QUAN TRỌNG: Chỉ trả về đúng 1 đoạn văn nhận xét, KHÔNG có JSON, KHÔNG có tiêu đề, KHÔNG có dấu ngoặc kép bao ngoài."
    )

    try:
        resp = await asyncio.to_thread(llm.invoke, prompt_text)
        ai_feedback = resp.content.strip().strip('"').strip("'")

        # Gửi kết quả về Backend để lưu vào LearningPath
        backend_url = os.environ.get("DJANGO_BACKEND_URL", "http://backend:8000")
        internal_key = os.environ.get("INTERNAL_API_KEY", "internal-service-key-2024")

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{backend_url}/api/internal/save-post-test-result/",
                json={
                    "user_id": request.user_id,
                    "chapter_id": request.chapter_id,
                    "post_test_score": request.post_test_score,
                    "post_test_ai_feedback": ai_feedback,
                },
                headers={"X-Internal-Key": internal_key},
                timeout=30.0
            )

        return {
            "status": "ok",
            "ai_feedback": ai_feedback,
            "post_test_score": request.post_test_score,
            "pre_test_score": request.pre_test_score,
            "improvement": improvement,
            "mastery_verdict": mastery_verdict
        }
    except Exception as e:
        print(f"❌ [Post-Test Eval Error]: {e}")
        return {"status": "error", "message": str(e)}


class ExtractTocRequest(BaseModel):
    pdf_path: str = Field(..., description="Đường dẫn file PDF trong container")

@app.post("/api/v1/extract-toc")
async def extract_toc_endpoint(request: ExtractTocRequest):
    try:
        result_data = await extract_toc_from_pdf(request.pdf_path)
        if result_data is None:
            raise HTTPException(status_code=400, detail="Không thể trích xuất mục lục.")
        return {"status": "success", **result_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExtractPagesRequest(BaseModel):
    pdf_path: str = Field(..., description="Đường dẫn file PDF")
    start_page: int
    end_page: int

@app.post("/api/v1/extract-pages")
async def extract_pages_endpoint(request: ExtractPagesRequest):
    try:
        content = await extract_pages_content(request.pdf_path, request.start_page, request.end_page)
        if content is None:
            return {"status": "error", "message": "Không thể trích xuất nội dung từ PDF."}
        return {"status": "success", "content": content}
    except Exception as e:
        print(f"❌ [Extract Pages Error]: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Tắt reload trong docker để tránh lỗi Watchfiles I/O
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
