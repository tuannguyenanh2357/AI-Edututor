import os
import django
import sys
from datetime import date

# 1. Setup Django Environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Unicode fix for Windows terminal
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apps.gamification.models import StoreItem

def seed_data():
    print("--- Seeding Arena & Shop Data ---")

    # 1. Seed Shop Items
    items = [
        {
            "name": "Băng nén chuỗi (Streak Freeze)",
            "slug": "streak-freeze",
            "description": "Giữ nguyên chuỗi ngày học của bạn ngay cả khi bạn nghỉ 1 ngày.",
            "price_gems": 50,
            "item_type": "STREAK_FREEZE",
            "icon_name": "fa-ice-cream"
        },
        {
            "name": "Gợi ý thông minh (Smart Hint)",
            "slug": "smart-hint",
            "description": "Nhận gợi ý từ AI cho các câu hỏi khó trong đấu trường.",
            "price_gems": 20,
            "item_type": "HINT",
            "icon_name": "fa-lightbulb"
        },
        {
            "name": "Tăng tốc XP (XP Boost)",
            "slug": "xp-boost",
            "description": "Nhận gấp đôi XP trong vòng 30 phút tiếp theo.",
            "price_gems": 100,
            "item_type": "XP_BOOST",
            "icon_name": "fa-rocket"
        }
    ]

    for item_data in items:
        item, created = StoreItem.objects.get_or_create(
            slug=item_data['slug'],
            defaults=item_data
        )
        if created:
            print(f"Created Shop Item: {item.name}")

    print("--- Seeding Completed Successfully! ---")

if __name__ == "__main__":
    seed_data()
