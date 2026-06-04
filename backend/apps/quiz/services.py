import httpx
import threading
import os
from django.conf import settings

AI_SERVICE_URL = settings.AI_SERVICE_URL
AI_SERVICE_KEY = settings.AI_SERVICE_KEY
AI_HEADERS = {"X-AI-Service-Key": AI_SERVICE_KEY}

class AIEvaluatorService:
    """
    Service chuyên trách xử lý giao tiếp với AI Service cho hệ thống Learning Path.
    Đảm bảo tách biệt hoàn toàn với logic của hệ thống PvP/DailyQuest.
    """
    
    @staticmethod
    def trigger_pretest_evaluation(user_id, subject_id, subject_name, grade_level, score, wrong_chapters, chapter_scores=None):
        """
        Gửi kết quả bài thi đầu vào cho AI để phân tích và tạo lộ trình học tập.
        Chạy không đồng bộ (fire-and-forget) để không làm treo UI.
        """
        def _call_ai_worker():
            try:
                # Timeout dài (120s) vì AI phân tích và tạo lộ trình mất nhiều thời gian
                with httpx.Client(timeout=120.0) as client:
                    client.post(
                        f"{AI_SERVICE_URL}/api/v1/evaluate-pretest",
                        json={
                            "user_id": user_id,
                            "subject_id": subject_id,
                            "subject_name": subject_name,
                            "grade_level": grade_level,
                            "score": score,
                            "wrong_chapters": wrong_chapters,
                            "chapter_scores": chapter_scores or {}
                        },
                        headers=AI_HEADERS
                    )
            except Exception as e:
                print(f"⚠️ [AIEvaluatorService] Lỗi khi gọi AI Service: {str(e)}")

        # Chạy task trong thread riêng để tránh block Django process chính
        thread = threading.Thread(target=_call_ai_worker, daemon=True)
        thread.start()

    @staticmethod
    def trigger_chapter_evaluation(user_id: int, subject_id: int, chapter_id: int, chapter_title: str, subject_name: str, grade_level: str, score: float, wrong_details: list):
        """
        Gọi sang AI Service để phân tích Đánh giá đầu vào theo chương.
        """
        def _call_ai_worker():
            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(
                        f"{AI_SERVICE_URL}/api/v1/evaluate-chapter-test",
                        json={
                            "user_id": user_id,
                            "subject_id": subject_id,
                            "chapter_id": chapter_id,
                            "chapter_title": chapter_title,
                            "subject_name": subject_name,
                            "grade_level": grade_level,
                            "score": float(score),
                            "wrong_details": wrong_details
                        },
                        headers=AI_HEADERS
                    )
                    print(f"[AIEvaluatorService] Chapter eval response: {resp.status_code} - {resp.text[:200]}")
            except Exception as e:
                print(f"⚠️ [AIEvaluatorService] Lỗi Chapter Eval: {str(e)}")

        thread = threading.Thread(target=_call_ai_worker, daemon=True)
        thread.start()

    @staticmethod
    def trigger_post_test_evaluation(user_id: int, subject_id: int, chapter_id: int, chapter_title: str, subject_name: str, grade_level: int, pre_test_score: float, post_test_score: float, wrong_details: list):
        """
        Gửi kết quả bài kiểm tra đầu ra (Post-test) cho AI để so sánh tiến bộ.
        """
        def _call_ai_worker():
            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(
                        f"{AI_SERVICE_URL}/api/v1/evaluate-post-test",
                        json={
                            "user_id": user_id,
                            "subject_id": subject_id,
                            "chapter_id": chapter_id,
                            "chapter_title": chapter_title,
                            "subject_name": subject_name,
                            "grade_level": grade_level,
                            "pre_test_score": float(pre_test_score),
                            "post_test_score": float(post_test_score),
                            "wrong_details": wrong_details
                        },
                        headers=AI_HEADERS
                    )
                    print(f"[AIEvaluatorService] Post-test eval response: {resp.status_code}")
            except Exception as e:
                print(f"⚠️ [AIEvaluatorService] Lỗi Post-test Eval: {str(e)}")

        thread = threading.Thread(target=_call_ai_worker, daemon=True)
        thread.start()
