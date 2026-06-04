import os
import random
import json
import asyncio
from pathlib import Path
from agent import AgentFactory
from langchain_core.messages import SystemMessage, HumanMessage

class PreTestGenerator:
    """
    Engine chuyên dụng để tạo bài thi Đánh giá đầu vào (Pre-test).
    Mục tiêu: Tạo bộ đề bao quát toàn bộ kiến thức của một môn học/khối lớp.
    """
    
    @staticmethod
    async def generate_pretest_suite(subject: str, grade_level: int, chapters_list: list):
        """
        Sinh bộ đề Pre-test gồm nhiều chương.
        chapters_list: Danh sách tên các chương cần bao phủ.
        """
        print(f"🎯 Đang khởi tạo bài thi đầu vào môn {subject} - Lớp {grade_level}...")
        
        llm = AgentFactory.get_llm()
        
        # Chúng ta yêu cầu AI tạo 2-3 câu hỏi cho mỗi chương để tạo thành bài test tổng hợp
        all_questions = []
        
        for chapter_name in chapters_list:
            print(f"   + Đang soạn câu hỏi cho chương: {chapter_name}")
            
            prompt = (
                f"Ban la chuyen gia khao thi. Tao 3 CAU HOI TRAC NGHIEM danh gia dau vao cho chuong nay.\n"
                f"MON: {subject} | KHOI: {grade_level} | CHUONG: {chapter_name}\n"
                "YEU CAU:\n"
                "- 1 câu Dễ (Nhận biết), 1 câu Trung bình (Thông hiểu), 1 câu Khó (Vận dụng).\n"
                "- Sử dụng LaTeX cho công thức.\n"
                "- Trình bày kết quả dưới dạng JSON list.\n"
                "[\n"
                "  {\n"
                "    \"question_text\": \"...\",\n"
                "    \"options\": [{\"text\": \"...\", \"is_correct\": true}, ...],\n"
                "    \"explanation\": \"...\",\n"
                "    \"difficulty\": 1\n"
                "  }\n"
                "]"
            )
            
            try:
                response = await llm.ainvoke([
                    SystemMessage(content="Return pure JSON list of questions."),
                    HumanMessage(content=prompt)
                ])
                raw_text = response.content.replace("```json", "").replace("```", "").strip()
                chapter_qs = json.loads(raw_text)
                
                # Gán thêm thông tin chương để Backend biết học sinh sai ở đâu
                for q in chapter_qs:
                    q['chapter_name'] = chapter_name
                    all_questions.append(q)
            except Exception as e:
                print(f"   X Lỗi khi sinh câu hỏi cho {chapter_name}: {e}")
                
        return all_questions

# Hướng dẫn tích hợp: 
# File này sẽ được gọi bởi một Management Command trong Backend để nạp dữ liệu Pre-test xịn.
