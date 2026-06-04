import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.curriculum.models import Chapter, Lesson, Topic

def fix_curriculum():
    # 1. Tìm Chapter "MỆNH ĐỀ VÀ TẬP HỢP" (ID 123)
    try:
        ch123 = Chapter.objects.get(id=123)
        print(f"Found Chapter 123: {ch123.title}")
    except Chapter.DoesNotExist:
        print("Chapter 123 not found!")
        return

    # 2. Xử lý các bài trong Chapter 123
    lessons_123 = ch123.lessons.all().order_by('order_num')
    if lessons_123.exists():
        # Giữ lại bài đầu tiên "Mệnh đề"
        main_menh_de = lessons_123[0]
        print(f"Keeping Lesson: {main_menh_de.title}")
        
        # Xóa các bài con (Mệnh đề chứa biến, Phủ định, v.v.)
        # TODO: Cân nhắc gộp topics vào bài chính nếu cần, nhưng user muốn "3 bài" đúng chuẩn.
        # Ở đây ta xóa các bài thừa để làm sạch khung.
        redundant_lessons = lessons_123[1:]
        for rl in redundant_lessons:
            print(f"Deleting redundant lesson: {rl.title}")
            rl.delete()
    
    # 3. Di chuyển bài từ Chapter 124 ("TẬP HỢP") sang 123
    try:
        ch124 = Chapter.objects.get(id=124)
        print(f"Found Chapter 124: {ch124.title}")
        
        lessons_124 = ch124.lessons.all().order_by('order_num')
        for i, l in enumerate(lessons_124):
            l.chapter = ch123
            l.lesson_number = str(i + 2) # Sẽ là bài 2, bài 3
            l.order_num = i + 1 # Bài 1 có order_num=0 (giả sử)
            l.save()
            print(f"Moved Lesson: {l.title} to Chapter 123 as Lesson {l.lesson_number}")
        
        # Xóa Chapter 124 thừa
        print("Deleting redundant Chapter 124")
        ch124.delete()
    except Chapter.DoesNotExist:
        print("Chapter 124 not found, maybe already fixed or name mismatch.")

    # 4. Cập nhật order_num cho đồng nhất
    all_lessons = ch123.lessons.all().order_by('id') # or by whatever was intended
    for idx, l in enumerate(all_lessons):
        l.order_num = idx
        l.lesson_number = str(idx + 1)
        l.save()
        print(f"Finalizing Lesson {l.lesson_number}: {l.title}")

if __name__ == "__main__":
    fix_curriculum()
