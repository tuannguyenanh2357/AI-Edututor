import os
import sys
import django
import re

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Unicode fix for Windows terminal
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apps.quiz.models import Question
from apps.curriculum.models import Chapter, Topic

def self_heal():
    print("🛠️ Starting Database Self-Healing...")
    
    # 1. Fix questions with topic but no chapter_title
    print("\n[Step 1] Syncing chapter_title from Topic FK...")
    qs_to_sync = Question.objects.filter(topic__isnull=False, chapter_title__in=[None, ''])
    sync_count = 0
    for q in qs_to_sync:
        try:
            q.chapter_title = q.topic.lesson.chapter.title
            q.save()
            sync_count += 1
        except Exception:
            pass
    print(f"✅ Synced {sync_count} chapter_titles.")

    # Helper to normalize chapter titles (convert Roman to Arabic, etc.)
    def normalize_title(title):
        if not title: return ""
        t = title.upper().strip()
        # Mapping Roman to Arabic
        roman_map = {"VIII": "8", "VII": "7", "VI": "6", "IV": "4", "IX": "9", "III": "3", "II": "2", "I": "1", "V": "5", "X": "10"}
        for r, a in roman_map.items():
            t = t.replace(f"CHƯƠNG {r}", f"CHƯƠNG {a}")
        
        # Remove common stop words and punctuation
        import re
        t = re.sub(r'[.:-]', ' ', t)
        stop_words = ["THỜI", "CỦA", "VÀ", "CÁC", "MỘT", "SỐ", "PHẦN", "CHƯƠNG", "CHỦ", "ĐỀ"]
        for word in stop_words:
            t = re.sub(rf'\b{word}\b', '', t)
            
        t = " ".join(t.split())
        return t

    # 2. Fix questions with chapter_title but no Topic FK
    print("\n[Step 2] Linking Questions to Topics via chapter_title mapping...")
    qs_to_link = Question.objects.filter(topic__isnull=True).exclude(chapter_title__in=[None, ''])
    link_count = 0
    chapter_cache = {}

    for q in qs_to_link:
        if not q.chapter_title:
            continue
        
        subject = q.quiz.subject
        q_norm = normalize_title(q.chapter_title)
        
        # Original normalize for number extraction
        q_raw_norm = q.chapter_title.upper()
        q_num_match = re.search(r'(?:CHƯƠNG|CHỦ ĐỀ|PHẦN)\s*(?:[IVX]+|\d+)', q_raw_norm)
        q_num = q_num_match.group(0) if q_num_match else None

        cache_key = (subject.id, q_norm)
        chapter = chapter_cache.get(cache_key)
        
        if not chapter:
            chapters = Chapter.objects.filter(subject=subject)
            for c in chapters:
                c_norm = normalize_title(c.title)
                c_raw_norm = c.title.upper()
                c_num_match = re.search(r'(?:CHƯƠNG|CHỦ ĐỀ|PHẦN)\s*(?:[IVX]+|\d+)', c_raw_norm)
                c_num = c_num_match.group(0) if c_num_match else None
                
                # Match strategy 1: Direct normalized match or substring
                if q_norm and c_norm and (q_norm in c_norm or c_norm in q_norm):
                    chapter = c
                    break
                
                # Match strategy 2: Number match (e.g. "CHƯƠNG 3" == "CHƯƠNG III")
                if q_num and c_num and q_num.replace("III", "3").replace("II", "2").replace("I", "1") == c_num.replace("III", "3").replace("II", "2").replace("I", "1"):
                     chapter = c
                     break

            if chapter:
                chapter_cache[cache_key] = chapter
        
        if chapter:
            first_topic = Topic.objects.filter(lesson__chapter=chapter).first()
            if first_topic:
                q.topic = first_topic
                q.save()
                link_count += 1
                
    print(f"✅ Linked {link_count} questions to actual Curriculum Topics.")
    
    # 3. Sync difficulty_level with bloom_level
    print("\n[Step 3] Syncing difficulty_level with bloom_level for UI compatibility...")
    qs_to_fix_diff = Question.objects.all()
    diff_count = 0
    for q in qs_to_fix_diff:
        if q.difficulty_level != q.bloom_level:
            q.difficulty_level = q.bloom_level
            q.save()
            diff_count += 1
    print(f"✅ Synced {diff_count} questions difficulty levels.")

    # 4. Final Report
    remaining = Question.objects.filter(topic__isnull=True).count()
    print(f"\n--- SELF-HEAL SUMMARY ---")
    print(f"Fixed Mapping: {sync_count + link_count}")
    print(f"Fixed Difficulty: {diff_count}")
    print(f"Remaining Orphan Questions: {remaining}")

if __name__ == "__main__":
    self_heal()
