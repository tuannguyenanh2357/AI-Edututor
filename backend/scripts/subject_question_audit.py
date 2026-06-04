import os
import django
import sys

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Fix Unicode for Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apps.subjects.models import Subject
from apps.curriculum.models import Chapter, Topic
from apps.quiz.models import Question

def run_subject_audit():
    subjects = Subject.objects.all().order_by('grade_level', 'name')
    
    print("\n" + "="*80)
    print(f"{'ID':<4} | {'Subject Name':<20} | {'Grade':<6} | {'Topics':<8} | {'Questions':<10}")
    print("-" * 80)
    
    total_q = 0
    empty_subjects = []
    
    for s in subjects:
        topics_count = Topic.objects.filter(lesson__chapter__subject=s).count()
        # Questions are linked to Topic
        total_subject_q = Question.objects.filter(topic__lesson__chapter__subject=s).count()
        
        print(f"{s.id:<4} | {s.name:<20} | {s.grade_level:<6} | {topics_count:<8} | {total_subject_q:<10}")
        
        total_q += total_subject_q
        if total_subject_q == 0:
            empty_subjects.append(f"{s.name} (Lớp {s.grade_level})")
            
    print("-" * 80)
    print(f"TOTAL QUESTIONS IN DB: {total_q}")
    print(f"SUBJECTS WITH 0 QUESTIONS: {len(empty_subjects)}")
    for name in empty_subjects:
        print(f"  - {name}")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_subject_audit()
