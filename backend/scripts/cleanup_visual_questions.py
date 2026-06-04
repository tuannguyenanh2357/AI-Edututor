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

from apps.quiz.models import Question

def cleanup():
    visual_keywords = [
        'hình bên', 'hình dưới', 'hình vẽ', 'quan sát hình', 
        'nhìn hình', 'hình 1.', 'hình 2.', 'hình 3.', 'hình 4.', 
        'bản đồ', 'sơ đồ bên', 'biểu đồ bên'
    ]
    
    total_deleted = 0
    print("Starting cleanup of visual-dependent questions...")
    
    for key in visual_keywords:
        qs = Question.objects.filter(question_text__icontains=key)
        count = qs.count()
        if count > 0:
            print(f"🗑️ Deleting {count} questions containing: '{key}'")
            # Log some examples before deleting
            for q in qs[:2]:
                print(f"   Sample: {q.question_text[:100]}...")
            
            qs.delete()
            total_deleted += count
            
    print(f"\n✨ DONE: Removed {total_deleted} visual-dependent questions.")

if __name__ == "__main__":
    cleanup()
