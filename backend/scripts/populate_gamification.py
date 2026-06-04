import os
import sys
import django
import random
from datetime import date, timedelta

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.gamification.models import Badge
from apps.subjects.models import Subject
from django.contrib.auth import get_user_model

User = get_user_model()

def populate():
    print("Starting gamification data seeding...")

    # 1. Create Subjects if not exist
    subjects_data = [
        {"name": "Toán học", "grade": 12},
        {"name": "Vật lý", "grade": 12},
        {"name": "Hóa học", "grade": 12},
    ]
    
    subjects = {}
    for item in subjects_data:
        subj, created = Subject.objects.get_or_create(
            name=item["name"], 
            grade_level=item["grade"]
        )
        subjects[item["name"]] = subj
        if created:
            print(f"Created subject: {item['name']}")

    # 3. Create Badges
    badges_data = [
        {"name": "Nhà Thông Thái", "code": "WISE_ONE", "desc": "Hoàn thành thử thách tất cả các đảo trong 1 ngày", "cat": "LEARNING", "type": "daily_complete"},
        {"name": "Kiên Trì", "code": "STREAK_7", "desc": "Đạt chuỗi 7 ngày học tập", "cat": "CONSISTENCY", "type": "streak_count", "val": 7},
        {"name": "Đại Phú Hào", "code": "RICH_KID", "desc": "Tích lũy được 500 LP", "cat": "ARENA", "type": "points_total", "val": 500},
    ]

    for b_data in badges_data:
        badge, created = Badge.objects.get_or_create(
            code=b_data["code"],
            defaults={
                "name": b_data["name"],
                "description": b_data["desc"],
                "category": b_data["cat"],
                "criteria_type": b_data["type"],
                "requirement_value": b_data.get("val", 0)
            }
        )
        if created:
            print(f"Created badge: {b_data['name']}")

    print("Seeding gamification base objects completed successfully!")

if __name__ == "__main__":
    populate()
