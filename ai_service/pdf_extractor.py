import os
import base64
import json
import asyncio
from pathlib import Path

# Add path for ai_service imports
import sys
sys.path.append(str(Path(__file__).parent))

import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage
from agent import AgentFactory
import requests

BACKEND_URL = "http://edututor_backend:8000"

async def extract_toc_from_pdf(pdf_path: str):
    """
    Uses Gemini Multimodal to read PDF pages as images 
    and extract Chapter/Lesson structure.
    """
    print(f"--- Processing PDF: {pdf_path} ---")
    if not os.path.exists(pdf_path):
        print("[Error] File does not exist!")
        return None

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"[Error] Failed to open PDF: {e}")
        return None

    num_pages_to_check = min(20, len(doc))
    content_parts = [{
        "type": "text",
        "text": (
            "BẠN LÀ CHUYÊN GIA CẤU TRÚC DỮ LIỆU GIÁO DỤC VIỆT NAM.\n"
            "Hãy đọc nội dung mục lục của cuốn sách qua các hình ảnh bên dưới.\n"
            "Trả về ĐÚNG định dạng JSON sau, KHÔNG giải thích thêm:\n\n"
            "{\n"
            "  \"ten_sach\": \"Tên đầy đủ của cuốn sách\",\n"
            "  \"lop\": \"Số lớp (ví dụ: 10, 11, 12)\",\n"
            "  \"pdf_offset\": \"Số nguyên: số trang trắng/lời nói đầu trước khi trang nội dung số 1 xuất hiện\",\n"
            "  \"cau_truc\": [\n"
            "    {\n"
            "      \"phan\": \"Tên Phần/Khối nếu có (ví dụ: Giáo dục Kinh tế, Phần 1). Nếu không có để trống: ''\",\n"
            "      \"chu_de\": \"Tên Chủ đề nếu sách dùng Chủ đề thay Chương. Nếu không có để trống: ''\",\n"
            "      \"chuong\": \"Tên Chương nếu sách dùng Chương (ví dụ: Chương 1: Mệnh đề). Nếu không có để trống: ''\",\n"
            "      \"bai\": [\n"
            "        {\n"
            "          \"so_bai\": \"Số thứ tự bài (ví dụ: 1, 2, 3)\",\n"
            "          \"ten_bai\": \"Tên đầy đủ bài học\",\n"
            "          \"trang\": \"Số trang bắt đầu IN TRÊN SÁCH (không phải trang PDF vật lý)\"\n"
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "- CHỈ liệt kê các đề mục là 'BÀI' chính thức (ví dụ: Bài 1, Bài 2...). KHÔNG liệt kê các mục nhỏ (1., 2., a), b)...) bên trong bài.\n"
            "- Nếu sách dùng 'Chủ đề' thay 'Chương' => điền 'chu_de', để 'chuong' là ''.\n"
            "- Nếu sách có cấp 'Phần' lớn hơn Chương => điền 'phan', và điền 'chuong' hoặc 'chu_de' bên trong.\n"
            "- Nếu không có cấp nào => để trống '' — KHÔNG được bỏ trường đó khỏi JSON.\n"
            "- Liệt kê ĐẦY ĐỦ tất cả các bài, không bỏ sót. TUYỆT ĐỐI KHÔNG ĐƯỢC TÓM TẮT HAY CẮT BỚT.\n"
            "- Phải bám sát số bài (so_bai) in trên sách. Ví dụ: Nếu sách ghi 'Bài 1. Mệnh đề' thì so_bai là '1'.\n"
            "- BỎ QUA: Lời nói đầu, Hướng dẫn sử dụng, Phụ lục, Thuật ngữ, Tài liệu tham khảo.\n"
            "- 'pdf_offset' là số NGUYÊN, ví dụ: 4 (không phải chuỗi).\n"
            "- Chỉ trả về JSON thuần, không có markdown code block (``` ```)."
        )
    }]

    for i in range(num_pages_to_check):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_data = pix.tobytes("png")
        img_b64 = base64.b64encode(img_data).decode("utf-8")
        
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    
    if len(doc) > 15:
        for i in range(max(15, len(doc) - 5), len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_data = pix.tobytes("png")
            img_b64 = base64.b64encode(img_data).decode("utf-8")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })

    llm = AgentFactory.get_llm()
    msg = HumanMessage(content=content_parts)
    
    print("--- Sending images to Gemini for TOC scanning ---")
    result = await asyncio.to_thread(llm.invoke, [msg])
    
    raw_text = result.content
    try:
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
        json_str = json_match.group(1) if json_match else raw_text
        start_curly = json_str.find('{')
        start_bracket = json_str.find('[')
        
        # Tìm vị trí bắt đầu thực sự (là { hoặc [)
        if start_curly != -1 and (start_bracket == -1 or start_curly < start_bracket):
            start = start_curly
            end = json_str.rfind('}')
        else:
            start = start_bracket
            end = json_str.rfind(']')

        if start != -1 and end != -1:
            data = json.loads(json_str[start:end+1])
            return data
        else:
            print("[Error] No valid JSON found in response.")
            return None
    except Exception as e:
        print(f"[Error] Failed to parse JSON: {e}")
        return None

async def extract_pages_content(pdf_path: str, start_page: int, end_page: int, fast_mode: bool = False):
    """
    Extracts text content from PDF pages using vision.
    """
    if not os.path.exists(pdf_path):
        return None

    doc = fitz.open(pdf_path)
    content_parts = [{"type": "text", "text": "Extract ALL text, formulas, and concepts from these pages into a detailed Markdown summary."}]

    max_idx = len(doc) - 1
    s_idx = max(start_page, 0)
    e_idx = min(end_page, max_idx)

    zoom = 1.0 if fast_mode else 1.5
    fmt  = "jpeg" if fast_mode else "png"
    mime = "image/jpeg" if fast_mode else "image/png"

    for i in range(s_idx, e_idx + 1):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img_data = pix.tobytes(fmt)
        img_b64 = base64.b64encode(img_data).decode("utf-8")
        
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{img_b64}"}
        })

    llm = AgentFactory.get_llm()
    msg = HumanMessage(content=content_parts)
    print(f"--- Sending pages {s_idx} to {e_idx} to Gemini... [Mode: {'FAST' if fast_mode else 'HQ'}] ---")
    result = await asyncio.to_thread(llm.invoke, [msg])
    
    return result.content

if __name__ == "__main__":
    import asyncio
    test_pdf = "/app/media/books/pdfs/Dia_10.pdf"
    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(extract_toc_from_pdf(test_pdf))
    print(json.dumps(data, indent=2, ensure_ascii=False))
