from django.core.management.base import BaseCommand
from apps.gamification.models import Badge

class Command(BaseCommand):
    help = 'Seed 30 diverse badges into the database'

    def handle(self, *args, **options):
        badges = [
            # NHÓM HỌC TẬP (LEARNING)
            {
                "name": "Lính mới tò te",
                "code": "FIRST_LESSON",
                "description": "Hoàn thành bài học đầu tiên của bạn.",
                "category": "LEARNING",
                "criteria_type": "lessons_completed",
                "requirement_value": 1,
                "icon_url": "fas fa-baby"
            },
            {
                "name": "Người học chăm chỉ",
                "code": "STUDY_10",
                "description": "Hoàn thành 10 bài học.",
                "category": "LEARNING",
                "criteria_type": "lessons_completed",
                "requirement_value": 10,
                "icon_url": "fas fa-book-reader"
            },
            {
                "name": "Bậc thầy kiến thức",
                "code": "STUDY_50",
                "description": "Hoàn thành 50 bài học.",
                "category": "LEARNING",
                "criteria_type": "lessons_completed",
                "requirement_value": 50,
                "icon_url": "fas fa-graduation-cap"
            },
            {
                "name": "Điểm tuyệt đối",
                "code": "PERFECT_SCORE",
                "description": "Đạt điểm 100% trong một bài kiểm tra.",
                "category": "LEARNING",
                "criteria_type": "perfect_quizzes",
                "requirement_value": 1,
                "icon_url": "fas fa-star"
            },
            {
                "name": "Thủ khoa vạn năng",
                "code": "PERFECT_10",
                "description": "Đạt điểm 100% trong 10 bài kiểm tra.",
                "category": "LEARNING",
                "criteria_type": "perfect_quizzes",
                "requirement_value": 10,
                "icon_url": "fas fa-medal"
            },
            {
                "name": "Tân binh XP",
                "code": "XP_100",
                "description": "Đạt được 100 XP đầu tiên.",
                "category": "LEARNING",
                "criteria_type": "total_xp",
                "requirement_value": 100,
                "icon_url": "fas fa-bolt"
            },
            {
                "name": "Đại gia XP",
                "code": "XP_1000",
                "description": "Tích lũy tổng cộng 1000 XP.",
                "category": "LEARNING",
                "criteria_type": "total_xp",
                "requirement_value": 1000,
                "icon_url": "fas fa-crown"
            },
            
            # NHÓM ĐẤU TRƯỜNG (ARENA)
            {
                "name": "Chiến thắng đầu tay",
                "code": "FIRST_WIN",
                "description": "Giành chiến thắng đầu tiên trong đấu trường PvP.",
                "category": "ARENA",
                "criteria_type": "pvp_wins",
                "requirement_value": 1,
                "icon_url": "fas fa-trophy"
            },
            {
                "name": "Chiến binh kiên cường",
                "code": "PVP_10",
                "description": "Giành 10 chiến thắng PvP.",
                "category": "ARENA",
                "criteria_type": "pvp_wins",
                "requirement_value": 10,
                "icon_url": "fas fa-sword"
            },
            {
                "name": "Độc cô cầu bại",
                "code": "PVP_100",
                "description": "Giành 100 chiến thắng PvP.",
                "category": "ARENA",
                "criteria_type": "pvp_wins",
                "requirement_value": 100,
                "icon_url": "fas fa-dragon"
            },
            {
                "name": "Chuỗi thắng ấn tượng",
                "code": "STREAK_5",
                "description": "Đạt chuỗi 5 trận thắng liên tiếp.",
                "category": "ARENA",
                "criteria_type": "max_win_streak",
                "requirement_value": 5,
                "icon_url": "fas fa-fire"
            },
            {
                "name": "Người leo tháp",
                "code": "TOWER_10",
                "description": "Chinh phục tầng 10 của Tháp Thử Thách.",
                "category": "ARENA",
                "criteria_type": "tower_floor_reached",
                "requirement_value": 10,
                "icon_url": "fas fa-gopuram"
            },
            {
                "name": "Đỉnh cao danh vọng",
                "code": "TOWER_50",
                "description": "Chinh phục tầng 50 của Tháp Thử Thách.",
                "category": "ARENA",
                "criteria_type": "tower_floor_reached",
                "requirement_value": 50,
                "icon_url": "fas fa-mountain"
            },

            # NHÓM CHUYÊN CẦN (CONSISTENCY)
            {
                "name": "Kiên trì 3 ngày",
                "code": "LOGIN_3",
                "description": "Đăng nhập học tập 3 ngày liên tiếp.",
                "category": "CONSISTENCY",
                "criteria_type": "login_streak",
                "requirement_value": 3,
                "icon_url": "fas fa-calendar-day"
            },
            {
                "name": "Tuần lễ vàng",
                "code": "LOGIN_7",
                "description": "Duy trì chuỗi học tập trong 7 ngày.",
                "category": "CONSISTENCY",
                "criteria_type": "login_streak",
                "requirement_value": 7,
                "icon_url": "fas fa-calendar-check"
            },
            {
                "name": "Thói quen thép",
                "code": "LOGIN_30",
                "description": "Duy trì chuỗi học tập trong 30 ngày.",
                "category": "CONSISTENCY",
                "criteria_type": "login_streak",
                "requirement_value": 30,
                "icon_url": "fas fa-calendar-alt"
            },

            # NHÓM TƯƠNG TÁC AI (AI)
            {
                "name": "Bạn đồng hành AI",
                "code": "AI_CHAT_10",
                "description": "Trò chuyện với AI Tutor 10 lần.",
                "category": "AI",
                "criteria_type": "chat_messages_count",
                "requirement_value": 10,
                "icon_url": "fas fa-robot"
            },
            {
                "name": "Tri kỷ nhân tạo",
                "code": "AI_CHAT_100",
                "description": "Trò chuyện với AI Tutor 100 lần.",
                "category": "AI",
                "criteria_type": "chat_messages_count",
                "requirement_value": 100,
                "icon_url": "fas fa-brain"
            },
            {
                "name": "Ham học hỏi",
                "code": "AI_EXPLAIN_5",
                "description": "Yêu cầu AI giải thích 5 câu trả lời sai.",
                "category": "AI",
                "criteria_type": "ai_explanations_requested",
                "requirement_value": 5,
                "icon_url": "fas fa-lightbulb"
            },

            # NHÓM XÃ HỘI & TÀI CHÍNH (SOCIAL)
            {
                "name": "Triệu phú Gems",
                "code": "GEMS_1000",
                "description": "Sở hữu 1000 Gems.",
                "category": "SOCIAL",
                "criteria_type": "gems_earned",
                "requirement_value": 1000,
                "icon_url": "fas fa-gem"
            },
            {
                "name": "Nhà sưu tầm",
                "code": "GEMS_5000",
                "description": "Tích lũy tổng cộng 5000 Gems.",
                "category": "SOCIAL",
                "criteria_type": "gems_earned",
                "requirement_value": 5000,
                "icon_url": "fas fa-coins"
            },
        ]

        # Thêm các huy hiệu cấp độ cao cho đủ 30
        for i in range(1, 10):
            badges.append({
                "name": f"Học giả Bậc {i}",
                "code": f"STUDY_RANK_{i}",
                "description": f"Hoàn thành {i*20} bài học chuyên sâu.",
                "category": "LEARNING",
                "criteria_type": "lessons_completed",
                "requirement_value": i*20 + 50,
                "icon_url": "fas fa-scroll"
            })

        created_count = 0
        for b_data in badges:
            badge, created = Badge.objects.update_or_create(
                code=b_data['code'],
                defaults=b_data
            )
            if created:
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Hoàn tất! Đã nạp thêm {created_count} huy hiệu mới.'))
