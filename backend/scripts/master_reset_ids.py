import os
import django
import sys

# Unicode fix for Windows terminal
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Set up Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.subjects.models import Subject, SubjectDocument
from apps.curriculum.models import Part, Chapter, Lesson, Topic
from apps.quiz.models import Quiz, Question, Answer
from django.db import connection

def master_reset():
    print("--- BAT DAU RESET TOAN BO HE THONG (MYSQL MODE) ---")
    
    # 1. Tat kiem tra khoa ngoai de xoa sạch du lieu ma khong bi loi
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        tables = [
            'answers', 'questions', 'quizzes',
            'topics', 'lessons', 'chapters', 'parts',
            'subject_documents', 'subjects'
        ]
        
        for table in tables:
            print(f"Làm sạch bảng {table}...")
            cursor.execute(f"TRUNCATE TABLE {table};")
            
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    
    print("✅ Da xoa sach va reset ID (TRUNCATE).")

    # 2. Tao lai danh sach mon hoc theo thu tu dep
    subjects_data = [
        # Lop 10
        ('Toán học', 10, 'Toan_10.pdf'),
        ('Vật lý', 10, 'Ly_10.pdf'),
        ('Hóa học', 10, 'Hoa_10.pdf'),
        ('Lịch sử', 10, 'Su_10.pdf'),
        ('Địa lý', 10, 'Dia_10.pdf'),
        ('Giáo dục công dân', 10, 'GDCD_10.pdf'),
        
        # Lop 11
        ('Toán học', 11, 'Toan_11.pdf'),
        ('Vật lý', 11, 'Ly_11.pdf'),
        ('Hóa học', 11, 'Hoa_11.pdf'),
        ('Lịch sử', 11, 'Su_11.pdf'),
        ('Địa lý', 11, 'Dia_11.pdf'),
        ('Giáo dục công dân', 11, 'GDCD_11.pdf'),
        
        # Lop 12
        ('Toán học', 12, 'Toan_12.pdf'),
        ('Vật lý', 12, 'Ly_12.pdf'),
        ('Hóa học', 12, 'Hoa_12.pdf'),
        ('Lịch sử', 12, 'Su_12.pdf'),
        ('Địa lý', 12, 'Dia_12.pdf'),
        ('Giáo dục công dân', 12, 'GDCD_12.pdf'),
    ]

    for name, grade, pdf in subjects_data:
        s = Subject.objects.create(
            name=name, 
            grade_level=grade, 
            icon_url='fa-book', 
            page_offset=4,
            description=f"Chương trình {name} lớp {grade}"
        )
        SubjectDocument.objects.create(
            subject=s,
            title=f"Sách giáo khoa {name} {grade}",
            pdf_file=f"books/pdfs/{pdf}"
        )
        print(f"OK: Created ID {s.id} - Grade {grade}")

    print("\n--- MASTER RESET COMPLETE ---")
    print("Everything is ready! Now you can run the sync and seed commands.")

if __name__ == "__main__":
    master_reset()
