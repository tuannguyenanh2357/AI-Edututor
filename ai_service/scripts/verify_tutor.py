import asyncio
import os
import json
import httpx
import sys
import io
from dotenv import load_dotenv

# Fix Unicode for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load env from parent directory where .env is located
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

async def test_ai_flow(query: str, intent_expected: str = "EXPLAIN"):
    print(f"\n🚀 Testing AI Flow: {query} (Expected Intent: {intent_expected})")
    
    # Correct endpoint from main.py
    url = "http://localhost:8001/api/v1/chat"
    
    # API Key from .env
    api_key = os.environ.get("AI_SERVICE_KEY", "dev-ai-key-edututor-2024")
    
    headers = {
        "X-AI-Service-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Correct payload for ChatRequest in main.py
    payload = {
        "message": query,
        "subject_name": "Vật lý",
        "grade_level": 12,
        "chat_history": [],
        "ai_preferences": "Giải thích ngắn gọn",
        "thread_id": "verify_test_thread"
    }

    citations_found = []
    full_answer = ""
    detected_intent = "Unknown"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    print(f"❌ HTTP Error: {response.status_code} - {await response.aread()}")
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "): continue
                    
                    data_str = line.replace("data: ", "")
                    try:
                        data = json.loads(data_str)
                    except: continue

                    msg_type = data.get("type")
                    content = data.get("content")

                    if msg_type == "token":
                        full_answer += content
                    
                    if msg_type == "tool_start":
                        print(f"🛠️ {content}")
                    
                    if msg_type == "citations":
                        citations_found.extend(content)
                        print(f"📖 Citations revealed: {json.dumps(content, ensure_ascii=False)}")
                    
                    if msg_type == "intent":
                        detected_intent = content
                        print(f"🎯 Intent: {detected_intent}")

    except Exception as e:
        print(f"❌ Error during test: {e}")

    print("\n--- FINAL SUMMARY ---")
    print(f"Detected Intent: {detected_intent}")
    print(f"Citations count: {len(citations_found)}")
    answer_preview = full_answer.replace("\n", " ")[:200]
    print(f"Answer snippet: {answer_preview}...")
    
    if len(full_answer) > 20:
        print("✅ Response generation: OK")
    else:
        print("❌ Response generation: FAILED")
        
    if len(citations_found) > 0:
        print("✅ Citations/RAG: OK (Source-grounded!)")
    else:
        print("⚠️ Citations/RAG: Not found (Falling back to general knowledge or tool failed)")

if __name__ == "__main__":
    # Test case 1: Kịch bản 1 - Có trong sách (Expect: Flex + Cite tại cuối)
    print("--- CASE 1: CÓ TRONG SÁCH (Phân tử chất khí) ---")
    asyncio.run(test_ai_flow("Dựa vào trang 7 vật lý 12, hãy giải thích sự khác biệt giữa các thể rắn, lỏng, khí.", "EXPLAIN"))

    # Test case 2: Kịch bản 2 - Kiến thức chung (Expect: Trả lời thẳng, KHÔNG nhắc sách)
    print("\n--- CASE 2: KIẾN THỨC CHUNG (Bầu trời màu xanh) ---")
    asyncio.run(test_ai_flow("Tại sao bầu trời có màu xanh vậy AI?", "EXPLAIN"))
    
    # Test case 3: Kịch bản 3 - Hỏi đích danh (Expect: Thông tin chi tiết + Trích dẫn)
    print("\n--- CASE 3: HỎI ĐÍCH DANH (Trang 10 Sử 12) ---")
    asyncio.run(test_ai_flow("Nội dung trang 10 sách Lịch sử 12 nói về điều gì?", "EXPLAIN"))

