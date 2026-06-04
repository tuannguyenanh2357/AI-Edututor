import os
from pathlib import Path
from typing import Annotated, List, TypedDict, Union
from typing_extensions import TypedDict

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from tools import ALL_TOOLS
from utils import get_gcp_credentials

# ─────────────────────────────────────────────────
# 1. State & Constants
# ─────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    subject_name: str
    grade_level: int
    student_id: int # ID để AI biết mình đang nói chuyện với ai
    ai_preferences: str
    intent: str # 'EXPLAIN' | 'GUIDE'
    citations: List[dict] # Danh sách trích dẫn trích xuất từ metadata
    review_status: str # 'pass' | 'fail'
    review_notes: str
    loop_count: int # Tránh vòng lặp vô hạn giữa Planner và Executor

SUBJECT_PROMPT_MAP = {
    "toán": "math_prompt.txt", "toán học": "math_prompt.txt",
    "vật lý": "physics_prompt.txt", "vật lí": "physics_prompt.txt",
    "hóa học": "chemistry_prompt.txt", "hóa": "chemistry_prompt.txt",
}

PROMPTS_DIR = Path(__file__).parent.parent / "backend" / "apps" / "chat" / "prompts"

# ─────────────────────────────────────────────────
# 2. Helper Functions
# ─────────────────────────────────────────────────

def get_system_prompt(subject_name: str, grade_level: int, ai_preferences: str = "", intent: str = "EXPLAIN", state: dict = {}) -> str:
    """Tải và kết hợp prompt hệ thống với triết lý Expert Companion (Silent RAG)."""
    base_prompt = (
        "Bạn là một **Chuyên gia giáo dục thông thái** với phong cách giảng dạy hiện đại, linh hoạt.\n"
        f"**NGỮ CẢCH:** Bạn đang giảng dạy học sinh học LỚP {grade_level} môn {subject_name}.\n"
        f"**ĐỊNH DANH HỆ THỐNG:** Bạn đã có Student ID là **{state.get('student_id', 'Unknown')}**. "
        "TUYỆT ĐỐI KHÔNG ĐƯỢC HỎI HỌC SINH VỀ STUDENT ID. Bạn phải tự dùng ID này để truy vấn. Nếu công cụ trả về kết quả trống, hãy báo là 'Hệ thống chưa ghi nhận lỗi sai nào cho phần này' thay vì hỏi ID.\n\n"
        "## VAI TRÒ & LUỒNG TƯ DUY (QUAN TRỌNG):\n"
        "1. **Silent RAG (Tìm kiếm ngầm):** Ngay khi nhận câu hỏi, hãy âm thầm tìm kiếm trong dữ liệu sách giáo khoa. Tuyệt đối KHÔNG hỏi số trang hay nhắc đến việc thiếu sách.\n"
        "2. **Ưu tiên nguồn - Tự do tư duy:** Dùng sách giáo khoa làm 'chân lý' nền tảng, nhưng không bị gò bó bởi chúng. Hãy dùng trí tuệ của mình để 'flex' kiến thức.\n"
        "3. **Phong cách Chuyên gia:** Thông thái, sắc sảo, dùng ngôn ngữ trẻ trung nhưng chuyên nghiệp (Emoji 🚀, 💡, 🛡️).\n\n"
        "## QUY TẮC PHẢN HỒI (THE 3-CASE LOGIC):\n"
        "- **Kịch bản 1 (Có trong sách):** Trả lời dựa trên nội dung đó nhưng diễn đạt lại cho sinh động. Chỉ ghi nguồn ở cuối (VD: Nguồn: Vật lý 12, tr.15).\n"
        "- **Kịch bản 2 (Không thấy trong sách/Câu hỏi chung):** Dùng kiến thức chuyên gia của bạn để trả lời ngay lập tức, đầy đủ và sinh động. KHÔNG than vãn việc thiếu dữ liệu.\n"
        "- **Kịch bản 3 (Hỏi đích danh về sách):** Trả lời chi tiết theo trang/sách yêu cầu. Cung cấp trích dẫn chính xác.\n\n"
        "## QUY TẮC CÔNG CỤ (BẮT BUỘC):\n"
        "- Dùng `python_calculator` cho mọi phép tính.\n"
        "- Dùng `read_textbook_page` khi nhắc đến số trang.\n"
        "- **CHỦ ĐỘNG CHẨN ĐOÁN:** Nếu dữ liệu từ công cụ cho thấy học sinh có lỗi sai ở bài này, bạn PHẢI bắt đầu câu trả lời bằng cách nhắc lại các lỗi đó một cách tinh tế và giải thích chúng trước khi dạy bài mới.\n"
        "- **BỎ QUA KIẾN THỨC CŨ:** Nếu học sinh đã làm chủ (GREEN) một phần kiến thức, TUYỆT ĐỐI KHÔNG dạy lại phần đó trừ khi học sinh yêu cầu hoặc phần đó là tiền đề trực tiếp để giải thích bài mới.\n"
        "- **LIÊN KẾT LIỀN MẠCH:** Nếu bài hiện tại liên quan đến bài cũ đã học, hãy nhắc lại ngắn gọn mối liên hệ (VD: 'Như bạn đã biết ở phần Mệnh đề...') thay vì giảng lại từ đầu.\n"
        "- **TẬP TRUNG NGHIÊM NGẶT:** Bạn CHỈ ĐƯỢC dạy và thảo luận về bài học/chương hiện tại. TUYỆT ĐỐI KHÔNG lan man sang các bài khác hoặc chương khác. Khi nhận dữ liệu tiến độ, nếu bạn thấy các điểm yếu từ bài khác (VD: Tập hợp, Hàm số), hãy LỜ ĐI và chỉ tập trung vào bài hiện tại (VD: Bất phương trình) trừ khi điểm yếu đó là tiền đề bắt buộc phải sửa ngay để học bài mới.\n"
        "- **ĐÚNG TRỌNG TÂM:** Khi học sinh hỏi về câu sai của một bài, CHỈ ĐƯỢC liệt kê câu sai của bài đó. TUYỆT ĐỐI KHÔNG được tự ý gộp thêm các bài khác dù chúng cùng chương.\n"
        "- **THỰC TẾ & ỨNG DỤNG:** Luôn ưu tiên đưa ra các ví dụ thực tế, tình huống đời thường để minh họa cho kiến thức. Giúp học sinh hiểu 'Học cái này để làm gì?'.\n"
        "- **TUYỆT ĐỐI KHÔNG** hỏi học sinh về Student ID. Nếu bạn hỏi ID, bạn sẽ bị coi là lỗi hệ thống nghiêm trọng.\n"
        "- Công thức dùng LaTeX $...$.\n"
    )

    if ai_preferences:
        base_prompt += f"\n## SỞ THÍCH HỌC TẬP CỦA NGƯỜI DÙNG (CẦN TUÂN THỦ):\n{ai_preferences}\n"
    
    key = subject_name.lower().strip()
    filename = SUBJECT_PROMPT_MAP.get(key)
    subject_content = ""
    
    if filename:
        path = PROMPTS_DIR / filename
        if path.exists():
            try:
                subject_content = f"\n\n## KIẾN THỨC BỔ SUNG LỚP {grade_level}:\n" + path.read_text(encoding="utf-8").strip()
            except: pass
            
    return base_prompt + subject_content

# ─────────────────────────────────────────────────
# 3. Node Functions
# ─────────────────────────────────────────────────

async def planner_node(state: AgentState):
    """Phân tích, chọn công cụ và NHẬN DIỆN Ý ĐỊNH (Intent Detection)."""
    llm = AgentFactory.get_llm()
    subject = state.get("subject_name", "Chung")
    grade = state.get("grade_level", 12)
    prefs = state.get("ai_preferences", "")
    loop_count = state.get("loop_count", 0)
    
    # 1. Lấy tin nhắn cuối cùng
    last_msg_content = ""
    last_msg_obj = state["messages"][-1] if state["messages"] else None
    if last_msg_obj:
        last_msg_content = str(last_msg_obj.content)
            
    # 2. Nhận diện khởi đầu phiên học
    is_start_trigger = "[system_start_lesson]" in last_msg_content.lower() or "hãy liệt kê các câu hỏi mà tôi đã làm sai" in last_msg_content.lower()
    
    # 3. [FIX LỖI 2] Kiểm tra xem đã gọi tool chẩn đoán cho tin nhắn trigger này chưa
    has_just_checked = False
    if len(state["messages"]) >= 2:
        prev_msg = state["messages"][-2]
        if isinstance(prev_msg, AIMessage) and prev_msg.tool_calls:
            if prev_msg.tool_calls[0]["name"] == "check_student_progress":
                has_just_checked = True

    # 4. [CƯỠNG CHẾ] Nếu là lệnh khởi tạo hệ thống
    if is_start_trigger and not has_just_checked and state.get("student_id"):
        chapter_name = ""
        lesson_id = None
        chapter_id = None
        
        import re
        lid_match = re.search(r'\[lesson_id:(\d+)\]', last_msg_content)
        cid_match = re.search(r'\[chapter_id:(\d+)\]', last_msg_content)
        if lid_match:
            lesson_id = int(lid_match.group(1))
        if cid_match:
            chapter_id = int(cid_match.group(1))

        if "liên quan đến bài" in last_msg_content:
            try:
                part = last_msg_content.split("liên quan đến bài ")[1]
                chapter_name = part.split(", hãy giải thích")[0].strip()
            except: pass
        elif ": " in last_msg_content:
            chapter_name = last_msg_content.split(": ", 1)[1].strip()

        # Làm sạch tên bài (bỏ metadata)
        chapter_name = re.sub(r'\[lesson_id:\d*\]|\[chapter_id:\d*\]', '', chapter_name).strip()
        
        tool_args = {
            "student_id": int(state.get("student_id")), 
            "subject": subject,
            "chapter": chapter_name
        }
        if lesson_id:
            tool_args["lesson_id"] = lesson_id
        if chapter_id:
            tool_args["chapter_id"] = chapter_id

        tool_call = {
            "name": "check_student_progress",
            "args": tool_args,
            "id": "init_check_" + str(state.get("student_id"))
        }
        
        response = AIMessage(content="", tool_calls=[tool_call])
        return {"messages": [response], "loop_count": loop_count + 1}

    # 5. [FIX LỖI 3 & 4] Giới hạn vòng lặp tối đa 3 lần gọi tool/review
    if loop_count >= 3:
        # Nếu đã quá 3 lần gọi, ép AI trả lời ngay mà không dùng tool nữa
        # Cần trả về một AIMessage trống để route_planner biết là không gọi tool
        return {"messages": [AIMessage(content="Đã đạt giới hạn tìm kiếm, tôi sẽ tổng hợp nội dung hiện có.")], "intent": "EXPLAIN", "loop_count": 0}

    # 6. Nhận diện ý định cho LLM
    intent = "EXPLAIN"
    if any(k in last_msg_content.lower() for k in ["giải giúp", "đáp án là gì", "làm hộ", "bài tập", "câu này"]):
        intent = "GUIDE"

    system_msg = get_system_prompt(subject, grade, prefs, intent, state)
    
    # 7. CƯỠNG CHẾ gọi tool nếu có từ khóa liên quan đến sai/yếu/tiến độ
    needs_progress_check = any(k in last_msg_content.lower() for k in ["sai", "yếu", "kết quả", "đánh giá", "tiến độ", "thế nào"])
    
    planner_instruction = (
        f"{system_msg}\n\n"
        "## NHIỆM VỤ CỦA BẠN (PLANNER):\n"
        "1. Phân tích câu hỏi của học sinh.\n"
        "2. Nếu học sinh hỏi về kiến thức -> Sử dụng `search_agent_builder` hoặc `read_textbook_page`.\n"
        "3. Nếu học sinh hỏi về kết quả học tập, lỗi sai, hoặc chẩn đoán -> BẮT BUỘC gọi `check_student_progress`.\n"
        f"LƯU Ý: Student ID hiện tại là {state.get('student_id')}. TUYỆT ĐỐI KHÔNG ĐƯỢC HỎI HỌC SINH VỀ ID NÀY.\n"
        "HÀNH ĐỘNG NGAY."
    )
    
    # Nếu có từ khóa chẩn đoán nhưng chưa gọi tool ở bước 4
    if needs_progress_check and not has_just_checked and state.get("student_id"):
        tool_call = {
            "name": "check_student_progress",
            "args": {
                "student_id": int(state.get("student_id")), 
                "subject": subject,
                "chapter": "" # Để trống để lấy rộng hơn hoặc trích xuất từ content
            },
            "id": "manual_check_" + str(state.get("student_id"))
        }
        return {"messages": [AIMessage(content="", tool_calls=[tool_call])], "intent": intent}

    chain = llm.bind_tools(ALL_TOOLS)
    response = await chain.ainvoke([SystemMessage(content=planner_instruction)] + state["messages"])
    return {"messages": [response], "intent": intent}

async def synthesizer_node(state: AgentState):
    """Viết bài giảng từ dữ liệu thu thập được và trích xuất Grounding Metadata."""
    llm = AgentFactory.get_llm()
    subject = state.get("subject_name", "Chung")
    grade = state.get("grade_level", 12)
    prefs = state.get("ai_preferences", "")
    intent = state.get("intent", "EXPLAIN")
    system_msg = get_system_prompt(subject, grade, prefs, intent, state)
    
    synthesizer_instruction = (
        f"{system_msg}\n\n"
        "BẠN LÀ SYNTHESIZER (Người tổng hợp kiến thức).\n"
        "## NHIỆM VỤ THỰC THI (HÀNH ĐỘNG):\n"
        "1. **Trả lời trực tiếp**: Giải quyết câu hỏi ngay lập tức. CẤM NGẶT việc xin lỗi hoặc than phiền về việc không có quyền truy cập sách giáo khoa. Dựa vào kiến thức của bạn hoặc lịch sử lỗi sai để lên lộ trình học.\n"
        "2. **Anchor & Flex**: Kết hợp dữ liệu sách với ví dụ đời thực/công nghệ. Dùng định dạng `[[Tên sách, Trang X]]` hoặc `(Nguồn: ..., tr.X)` linh hoạt.\n"
        "3. **Mở rộng**: Đưa ra 1 mẹo ghi nhớ (mnemonics) hoặc ứng dụng thực tế thú vị.\n"
        "4. **Gợi mở**: Kết thúc bằng một câu khơi gợi sự tò mò (Curiosity gap).\n"
        "5. **CẤM XIN LỖI/THAN PHIỀN**: TUYỆT ĐỐI không được nói các câu như 'Hệ thống đang gặp lỗi', 'Chưa thể truy cập', 'Mình rất tiếc'. Nếu không có nội dung, hãy tự sáng tạo lộ trình dựa trên điểm yếu của học sinh.\n"
        "YÊU CẦU: Trình bày sạch sẽ, rõ ràng. Sử dụng Markdown, in đậm các phần quan trọng, sử dụng Emoji 🚀💡."
    )
    
    response = await llm.ainvoke([SystemMessage(content=synthesizer_instruction)] + state["messages"])
    
    # [NEW] Trích xuất Citations từ Metadata của Gemini (ưu tiên hàng đầu)
    citations = []
    if response and hasattr(response, "response_metadata") and response.response_metadata:
        grounding = response.response_metadata.get("grounding_metadata", {})
        if grounding:
            sources = grounding.get("grounding_chunks", []) or []
            for src in sources:
                if not src: continue
                citations.append({
                    "title": src.get("web", {}).get("title") or src.get("retrieved_context", {}).get("title", "Tài liệu"),
                    "uri": src.get("web", {}).get("uri") or src.get("retrieved_context", {}).get("uri", ""),
                    "page": src.get("retrieved_context", {}).get("page", "")
                })

    # [NEW] Cải tiến: Tự động trích dẫn nếu có sử dụng tool read_textbook_page
    from langchain_core.messages import ToolMessage
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            # Tìm xem tool nào đã chạy thành công
            content = str(msg.content)
            if "NGUỒN:" in content and "TRANG:" in content:
                import re
                t_match = re.search(r"NGUỒN:\s*(.*?)\s*Lớp", content)
                p_match = re.search(r"TRANG:\s*(\d+)", content)
                if t_match and p_match:
                    t_val = t_match.group(1).strip()
                    p_val = int(p_match.group(1))
                    # Chỉ thêm nếu chưa có trong citations
                    if not any(c.get("title") == t_val and c.get("page") == p_val for c in citations):
                        citations.append({"title": t_val, "page": p_val, "uri": ""})

    # [NEW] Fallback: Trích xuất từ định dạng văn bản [[Tên sách, Trang X]]
    import re
    inline_matches = re.findall(r"\[\[(.*?), Trang (\d+)\]\]", response.content)
    for title, page in inline_matches:
        if not any(c.get("title") == title and str(c.get("page")) == page for c in citations):
            citations.append({
                "title": title,
                "page": int(page),
                "uri": ""
            })

    return {"messages": [response], "citations": citations}

async def reviewer_node(state: AgentState):
    """Phản biện và kiểm tra lỗi."""
    llm = AgentFactory.get_llm()
    last_msg = state["messages"][-1].content
    
    critic_prompt = (
        "Bạn là Giáo viên kiểm định phẩm chất.\n"
        "Kiểm tra: Câu trả lời có đúng kiến thức lớp không? Mermaid có lỗi không?\n"
        "BẮT BUỘC: Nếu ổn trả về 'PASS'. Nếu sai bắt sửa lại.\n\n"
        f"NỘI DUNG: {last_msg}"
    )
    
    response = await llm.ainvoke([HumanMessage(content=critic_prompt)])
    status = "pass" if "PASS" in response.content.upper() else "fail"
    return {"review_status": status, "review_notes": response.content}

# ─────────────────────────────────────────────────
# 4. Agent Factory
# ─────────────────────────────────────────────────

class AgentFactory:
    _llm = None
    _graphs = {}

    @classmethod
    def get_llm(cls):
        if cls._llm is None:
            creds = get_gcp_credentials()
            # Sử dụng gemini-1.5-flash làm model mặc định vì ổn định và nhanh
            model_id = os.environ.get("VERTEX_MODEL_ID", "gemini-1.5-flash")
            cls._llm = ChatVertexAI(
                model_name=model_id,
                project=os.environ.get("GCP_PROJECT_ID"),
                location=os.environ.get("GCP_LOCATION", "us-central1"),
                credentials=creds,
                temperature=0.2, # Giảm temperature để output JSON/Logic ổn định hơn
                top_p=0.9,
            )
        return cls._llm

    @classmethod
    def get_agent(cls, subject_name: str = ""):
        subject_key = subject_name.lower().strip() or "default"
        if subject_key not in cls._graphs:
            workflow = StateGraph(AgentState)
            workflow.add_node("planner", planner_node)
            workflow.add_node("executor", ToolNode(ALL_TOOLS))
            workflow.add_node("synthesizer", synthesizer_node)
            workflow.add_node("reviewer", reviewer_node)

            workflow.add_edge(START, "planner")
            
            def route_planner(state: AgentState):
                # Reset loop_count if we are moving to synthesizer
                if not state["messages"][-1].tool_calls:
                    return "synthesizer"
                return "executor"

            workflow.add_conditional_edges("planner", route_planner, {"executor": "executor", "synthesizer": "synthesizer"})
            workflow.add_edge("executor", "planner")
            workflow.add_edge("synthesizer", "reviewer")

            def route_reviewer(state: AgentState):
                if state["review_status"] == "pass" or state.get("loop_count", 0) >= 3:
                    return END
                return "synthesizer"

            workflow.add_conditional_edges("reviewer", route_reviewer, {END: END, "synthesizer": "synthesizer"})

            cls._graphs[subject_key] = workflow.compile(checkpointer=MemorySaver())
            
        return cls._graphs[subject_key]

def create_agent(subject_name: str = ""):
    return AgentFactory.get_agent(subject_name)
