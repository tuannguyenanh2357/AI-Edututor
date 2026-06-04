import os
import django
import sys

# Set up Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Unicode fix for Windows terminal
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apps.subjects.models import Subject

def seed_subjects():
    subjects_data = [
        {"name": "Toán học", "grade_level": 10, "icon_url": "fa-calculator", "page_offset": 4},
        {"name": "Vật lý", "grade_level": 10, "icon_url": "fa-atom", "page_offset": 4},
        {"name": "Hóa học", "grade_level": 10, "icon_url": "fa-flask", "page_offset": 4},
        {"name": "Lịch sử", "grade_level": 10, "icon_url": "fa-history", "page_offset": 4},
        {"name": "Địa lý", "grade_level": 10, "icon_url": "fa-globe", "page_offset": 4},
        {"name": "Giáo dục công dân", "grade_level": 10, "icon_url": "fa-balance-scale", "page_offset": 4},
        
        {"name": "Toán học", "grade_level": 11, "icon_url": "fa-calculator", "page_offset": 4},
        {"name": "Vật lý", "grade_level": 11, "icon_url": "fa-atom", "page_offset": 4},
        {"name": "Hóa học", "grade_level": 11, "icon_url": "fa-flask", "page_offset": 4},
        {"name": "Lịch sử", "grade_level": 11, "icon_url": "fa-history", "page_offset": 4},
        {"name": "Địa lý", "grade_level": 11, "icon_url": "fa-globe", "page_offset": 4},
        {"name": "Giáo dục công dân", "grade_level": 11, "icon_url": "fa-balance-scale", "page_offset": 4},
        
        {"name": "Toán học", "grade_level": 12, "icon_url": "fa-calculator", "page_offset": 4},
        {"name": "Vật lý", "grade_level": 12, "icon_url": "fa-atom", "page_offset": 4},
        {"name": "Hóa học", "grade_level": 12, "icon_url": "fa-flask", "page_offset": 4},
        {"name": "Lịch sử", "grade_level": 12, "icon_url": "fa-history", "page_offset": 4},
        {"name": "Địa lý", "grade_level": 12, "icon_url": "fa-globe", "page_offset": 4},
        {"name": "Giáo dục công dân", "grade_level": 12, "icon_url": "fa-balance-scale", "page_offset": 4},
    ]

    print("--- Khoi tao danh sach mon hoc ---")
    for data in subjects_data:
        subject, created = Subject.objects.get_or_create(
            name=data["name"],
            grade_level=data["grade_level"],
            defaults={
                "icon_url": data["icon_url"],
                "page_offset": data["page_offset"],
                "description": f"Chương trình {data['name']} lớp {data['grade_level']}"
            }
        )
        if created:
            print(f"✅ Da tao: {data['name']} {data['grade_level']}")
        else:
            print(f"ℹ️ Da ton tai: {data['name']} {data['grade_level']}")

def main():
    print("🚀 Bat dau khoi tao du lieu du phong...")
    seed_subjects()
    print("\n✅ Hoan tat khoi tao du lieu co ban!")
    print("💡 Luu y: Ban nen chay 'python manage.py sync_textbooks' de nap chapters.")

if __name__ == "__main__":
    main()
