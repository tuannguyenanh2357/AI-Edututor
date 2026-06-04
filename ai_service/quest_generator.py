import os
import random
import json
import asyncio
import httpx
from pathlib import Path
from pdf_extractor import extract_pages_content
from agent import AgentFactory
from langchain_core.messages import SystemMessage, HumanMessage

# Config paths and URL
BACKEND_URL = os.environ.get("DJANGO_BACKEND_URL", "http://localhost:8000")
BOOKS_PATH = Path(os.environ.get("BOOKS_PATH", "d:/Capstone2---C2SE.07/backend/media/books/pdfs"))

SUBJECT_LIST = ["Toan hoc", "Vat ly", "Hoa hoc", "Sinh hoc", "Lich su", "Dia ly", "Tieng Anh"]

async def generate_single_quest(grade_level: int, floor_level: int = 1, subject: str = None):
    """
    Creates a tower challenge using AI.
    - Randomize Source: Textbook PDF vs General Knowledge.
    - Style: Academic vs Boss Battle (Tricky).
    - Difficulty: Scales with floor_level (1-10).
    """
    if not subject:
        subject = random.choice(SUBJECT_LIST)
    
    source_type = random.choice(["TEXTBOOK", "GENERAL"])
    print(f"--- Generating Floor {floor_level} | Subject: {subject} | Source: {source_type} ---", flush=True)

    content = ""
    if source_type == "TEXTBOOK":
        subject_map = {"Toan hoc": "Toan", "Vat ly": "Ly", "Hoa hoc": "Hoa", "Sinh hoc": "Sinh", "Lich su": "Su", "Dia ly": "Dia"}
        file_prefix = subject_map.get(subject, "Toan")
        search_pattern = f"{file_prefix}_{grade_level}*.pdf"
        matches = list(BOOKS_PATH.glob(search_pattern))
        
        if matches:
            pdf_path = str(matches[0])
            page_num = random.randint(20, 150)
            content = await extract_pages_content(pdf_path, page_num - 1, page_num - 1, fast_mode=False)
        else:
            source_type = "GENERAL"

    difficulty_desc = ""
    if floor_level <= 3:
        difficulty_desc = "De: Kien thuc co ban, nhan biet."
    elif floor_level <= 7:
        difficulty_desc = "Trung binh: Can suy luan, tinh toan."
    else:
        difficulty_desc = "Kho (BOSS MODE): Danh do, lat leo, yeu cau tu duy logic cao."

    style_desc = "Phong cach Boss Battle (hack nao, lat leo)" if floor_level > 7 else "Phong cach Hoc thuat (chuan xac, su pham)"

    llm = AgentFactory.get_llm()
    prompt = (
        f"Ban la chuyen gia soan thao de thi cao cap cho Dau truong Tri Thuc.\n"
        f"NHIEM VU: Tao 1 CAU HOI TRAC NGHIEM chat luong cao cho TANG {floor_level}.\n"
        f"MON HOC: {subject} | KHOI: {grade_level}\n"
        f"DO KHO: {difficulty_desc}\n"
        f"PHONG CACH: {style_desc}\n\n"
        "YEU CAU NOI DUNG (BAT BUOC):\n"
        "- PHONG CACH: TRUC TIEP, NGAY VAO VAN DE, KHONG VIET VAN HOA, KHONG KE CHUYEN (ROLEPLAY).\n"
        "- NGON NGU: 100% TIENG VIET CO DAU CHUAN SU PHAM.\n"
        "- DINH DANG TOAN HOC: SU DUNG LATEX (Dinh dang $...$ hoac $$...$$) CHO TAT CA CONG THUC, KY HIEU, SO MU, PHAN SO.\n"
        "- XAO TRON DAP AN: VI TRI DAP AN DUNG PHAI DUOC THAY DOI NGAU NHIEN (A, B, C, hoac D) CHO MOI CAU HOI.\n"
        f"{'- Su dung kien thuc tong quat phong phu ve ' + subject + ' (Lich su, Van hoa, Thuc tien).' if source_type == 'GENERAL' else '- Dua tren kien thuc hoc thuat chuan xac.'}\n"
        "- Co 4 dap an A, B, C, D.\n"
        "- Loi giai thich phai sau sac, khoa hoc.\n"
        "- Dinh dang tra ve: JSON nguyen ban (khong dung markdown block).\n\n"
        "{\n"
        "  \"title\": \"[PVP] {Ten chu de}\",\n"
        "  \"question_text\": \"...\",\n"
        "  \"options\": {\"A\": \"...\", \"B\": \"...\", \"C\": \"...\", \"D\": \"...\"},\n"
        "  \"correct_answer\": \"X\",\n"
        "  \"explanation\": \"...\"\n"
        "}\n\n"
    )
    if content:
        prompt += f"SOURCE MATERIAL:\n{content}"

    try:
        response = await llm.ainvoke([SystemMessage(content="Return pure JSON without markdown code blocks."), HumanMessage(content=prompt)])
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        quest_data = json.loads(raw_text)
        quest_data["floor_level"] = floor_level
        quest_data["grade_level"] = grade_level
        return quest_data
    except Exception as e:
        print(f"Exception calling AI: {e}")
        return None

async def sync_to_backend(quest_data, subject_id: int):
    payload = {
        **quest_data,
        "subject": subject_id
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            url = f"{BACKEND_URL}/api/gamification/daily-quest/"
            response = await client.post(url, json=payload)
            return response.status_code in [200, 201]
        except Exception as e: 
            print(f"Backend sync error: {e}")
            return False
