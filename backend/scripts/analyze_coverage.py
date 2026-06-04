import os
import django
import sys

# Set up Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.curriculum.models import Topic
from django.db.models import Count

def analyze():
    print("\nKIEM TRA DO PHU CAU HOI TREN TUNG BAI HOC (TOPIC):")
    print("-" * 60)
    
    subjects = Topic.objects.values_list('lesson__chapter__subject_id', flat=True).distinct()
    
    for sid in subjects:
        topics = Topic.objects.filter(lesson__chapter__subject_id=sid).annotate(q_count=Count('questions'))
        total_topics = topics.count()
        empty = topics.filter(q_count=0).count()
        low = topics.filter(q_count__gt=0, q_count__lt=5).count()
        
        if total_topics > 0:
            first_topic = topics.first()
            subject = first_topic.lesson.chapter.subject
            print(f"Subject: {subject.name} {subject.grade_level}")
            print(f"   - Total Topics: {total_topics}")
            print(f"   - Empty Topics: {empty}")
            print(f"   - Low Count Topics (< 5): {low}")
            if empty == 0 and low == 0:
                print(f"   [OK] Covered 5 questions per topic.")
            print("-" * 30)

if __name__ == "__main__":
    analyze()
