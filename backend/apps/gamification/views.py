from datetime import date, timedelta
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Badge, UserBadge, StoreItem, Inventory
from .serializers import (
    LeaderboardSerializer, UserBadgeSerializer,
    UserInventorySerializer, BadgeSerializer, StoreItemSerializer
)
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef

User = get_user_model()

class DailyQuestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        grade = request.query_params.get('grade', request.user.grade_level)
        
        from apps.quiz.models import Question
        import random

        # Lấy câu hỏi theo khối lớp
        base_qs = Question.objects.filter(
            topic__lesson__chapter__subject__grade_level=grade
        ).select_related('topic__lesson__chapter__subject').prefetch_related('answers')
        
        if not base_qs.exists():
            return Response({"error": f"Không có câu hỏi cho khối {grade}."}, status=status.HTTP_404_NOT_FOUND)

        # Cố định ngẫu nhiên theo ngày (để mọi học sinh thấy cùng 1 tháp trong ngày)
        seed = int(today.strftime('%Y%m%d'))
        random.seed(seed)
        
        # Chọn 10 câu hỏi để tạo 10 tầng tháp
        all_q_ids = list(base_qs.values_list('id', flat=True))
        if len(all_q_ids) > 10:
            selected_ids = random.sample(all_q_ids, 10)
        else:
            selected_ids = all_q_ids
            
        questions = list(base_qs.filter(id__in=selected_ids))
        random.shuffle(questions) # Shuffle lại
        
        completed_ids = request.user.completed_quests if request.user.last_quest_date == today else []
        
        data = []
        for i, q in enumerate(questions):
            floor = i + 1
            # Xây dựng options
            options = {}
            correct_ans = "A"
            for j, ans in enumerate(q.answers.all()):
                label = chr(65 + j)
                options[label] = ans.answer_text
                if ans.is_correct:
                    correct_ans = label
                    
            try:
                subject_name = q.topic.lesson.chapter.subject.name
            except AttributeError:
                subject_name = "Kiến thức chung"

            data.append({
                "id": q.id,
                "title": f"Thử thách Tầng {floor}",
                "question_text": q.question_text,
                "options": options,
                "correct_answer": correct_ans,
                "explanation": q.explanation or "Không có giải thích chi tiết.",
                "grade_level": grade,
                "date": today.isoformat(),
                "subject_name": subject_name,
                "floor_level": floor,
                "completed": q.id in completed_ids
            })
            
        return Response(data)

class SubmitQuestView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        today = date.today()
        user = request.user
        
        quest_id = int(request.data.get('quest_id'))
        answer = request.data.get('answer') # A, B, C, or D
        grade = request.data.get('grade', user.grade_level)
        
        # Reset completed_quests list if it's a new day
        if user.last_quest_date != today:
            user.completed_quests = []
            
        if quest_id in user.completed_quests:
            return Response({"error": "You have already completed this quest today!"}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.quiz.models import Question
        import random

        # Lấy lại cùng 1 tập câu hỏi của ngày hôm nay để xác định floor_level
        base_qs = Question.objects.filter(
            topic__lesson__chapter__subject__grade_level=grade
        ).prefetch_related('answers')

        seed = int(today.strftime('%Y%m%d'))
        random.seed(seed)
        
        all_q_ids = list(base_qs.values_list('id', flat=True))
        if len(all_q_ids) > 10:
            selected_ids = random.sample(all_q_ids, 10)
        else:
            selected_ids = all_q_ids
            
        questions = list(base_qs.filter(id__in=selected_ids))
        random.shuffle(questions)
        
        try:
            quest = next(q for q in questions if q.id == quest_id)
            floor_level = questions.index(quest) + 1
        except StopIteration:
            return Response({"error": "Quest not found in today's challenge"}, status=status.HTTP_404_NOT_FOUND)

        # Tìm đáp án đúng (A, B, C, D)
        correct_ans = "A"
        for j, ans in enumerate(quest.answers.all()):
            if ans.is_correct:
                correct_ans = chr(65 + j)
                break
                
        is_correct = correct_ans.upper() == answer.upper()
        
        if is_correct:
            # Enforce floor completion sequence
            if floor_level > 1:
                completed_today_ids = user.completed_quests if user.last_quest_date == today else []
                # Check if previous floor was completed
                prev_floor_completed = False
                for prev_idx in range(floor_level - 1):
                    if questions[prev_idx].id in completed_today_ids:
                        prev_floor_completed = True
                        break # Note: if we want strict sequential, we check if questions[floor_level-2].id in completed_today_ids
                
                strict_prev_id = questions[floor_level - 2].id
                if strict_prev_id not in completed_today_ids:
                    return Response({"error": f"Bạn phải hoàn thành Tầng {floor_level - 1} trước!"}, status=status.HTTP_400_BAD_REQUEST)

            # Scaling rewards based on floor
            xp_reward = 10 + (floor_level * 2)
            gem_reward = 5 + floor_level
            
            # Floor 10 Bonus
            if floor_level == 10:
                gem_reward += 50
                bonus_msg = "🏆 PHÁ ĐẢO THÁP TRI THỨC! +50 Gems Bonus!"
            else:
                bonus_msg = None

            user.total_xp += xp_reward
            user.gems += gem_reward
            
            # Update completion tracking with full re-assignment for JSONField persistence
            if user.last_quest_date != today:
                user.completed_quests = [int(quest_id)]
            else:
                current_completed = list(user.completed_quests)
                if int(quest_id) not in current_completed:
                    current_completed.append(int(quest_id))
                user.completed_quests = current_completed
            
            # ─────────────────────────────────────────────────
            # STREAK ENGINE
            # ─────────────────────────────────────────────────
            if user.last_quest_date == today - timedelta(days=1):
                if len(user.completed_quests) == 1:
                    user.current_streak += 1
            elif user.last_quest_date == today:
                pass
            else:
                freeze_item = Inventory.objects.filter(user=user, item__item_type='STREAK_FREEZE', quantity__gt=0).first()
                if freeze_item:
                    freeze_item.quantity -= 1
                    freeze_item.save()
                    user.current_streak += 1
                else:
                    user.current_streak = 1
            
            if user.current_streak > user.max_streak:
                user.max_streak = user.current_streak
            
            user.last_quest_date = today
            
            # Update Rank using centralized logic
            user.update_rank(commit=False)
            
            user.save()
            
            return Response({
                "status": "correct",
                "xp_earned": xp_reward,
                "gems_earned": gem_reward,
                "current_xp": user.total_xp,
                "current_gems": user.gems,
                "streak": user.current_streak,
                "rank": user.rank,
                "floor": floor_level,
                "bonus_message": bonus_msg,
                "explanation": quest.explanation
            })
        else:
            return Response({
                "status": "incorrect",
                "explanation": quest.explanation
            })

class LeaderboardView(generics.ListAPIView):
    serializer_class = LeaderboardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        grade = self.request.query_params.get('grade')
        if grade:
            return User.objects.filter(grade_level=grade).order_by('-total_xp')[:10]
        return User.objects.order_by('-total_xp')[:10]

class UserBadgesView(generics.ListAPIView):
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user).order_by('-earned_at')

class AllBadgesView(generics.ListAPIView):
    """
    Trả về tất cả huy hiệu hiện có trong hệ thống.
    """
    queryset = Badge.objects.all().order_by('category', 'requirement_value')
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecentBadgesView(generics.ListAPIView):
    """
    Trả về các huy hiệu mới đạt được trong 1 phút qua.
    Dùng cho thông báo toast ở frontend.
    """
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        one_minute_ago = date.today() # Placeholder, we need timezone-aware datetime
        from django.utils import timezone
        now = timezone.now()
        one_minute_ago = now - timedelta(minutes=1)
        return UserBadge.objects.filter(user=self.request.user, earned_at__gte=one_minute_ago)

# ─────────────────────────────────────────────────
# STORE & PURCHASE (Gamification 2.0)
# ─────────────────────────────────────────────────

class StoreItemListView(generics.ListAPIView):
    queryset = StoreItem.objects.filter(is_active=True)
    serializer_class = StoreItemSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserInventoryListView(generics.ListAPIView):
    serializer_class = UserInventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Inventory.objects.filter(user=self.request.user, quantity__gt=0)

class PurchaseItemView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        item_id = request.data.get('item_id')
        
        try:
            item = StoreItem.objects.get(id=item_id, is_active=True)
        except StoreItem.DoesNotExist:
            return Response({"error": "Vật phẩm không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
            
        if user.gems < item.price_gems:
            return Response({"error": "Bạn không đủ Gem để mua vật phẩm này."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Quay vòng thanh toán
        user.gems -= item.price_gems
        user.save()
        
        # Thêm vào kho đồ
        inventory_item, created = Inventory.objects.get_or_create(
            user=user,
            item=item,
            defaults={'quantity': 1}
        )
        if not created:
            inventory_item.quantity += 1
            inventory_item.save()
            
        return Response({
            "status": "success",
            "message": f"Đã mua thành công {item.name}!",
            "remaining_gems": user.gems,
            "item_name": item.name
        })
