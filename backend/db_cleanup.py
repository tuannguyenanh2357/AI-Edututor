from django.db import connection
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def cleanup():
    with connection.cursor() as cursor:
        print("Bắt đầu dọn dẹp Database...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        # 1. Danh sách môn muốn giữ (Tên chuẩn)
        to_keep = ['Toán học', 'Vật lý', 'Hóa học', 'Địa lý', 'Lịch sử', 'Giáo dục công dân', 
                   'Toán', 'Lý', 'Hóa', 'Địa', 'Sử', 'GDCD']
        
        # 2. Xóa các môn không nằm trong danh sách (Bao gồm Sinh học và các môn ASCII rác)
        # Sử dụng tham số %s để an toàn
        query = "DELETE FROM subjects WHERE name NOT IN %s OR name LIKE %s"
        cursor.execute(query, [tuple(to_keep), '%Sinh%'])
        print(f"Đã dọn dẹp bảng subjects. Rows affected: {cursor.rowcount}")

        # 3. Đổi tên về định dạng ngắn gọn
        replacements = {
            'Toán học': 'Toán',
            'Vật lý': 'Lý',
            'Hóa học': 'Hóa',
            'Địa lý': 'Địa',
            'Lịch sử': 'Sử',
            'Giáo dục công dân': 'GDCD'
        }
        for old, new in replacements.items():
            cursor.execute("UPDATE subjects SET name = %s WHERE name = %s", [new, old])
            
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        connection.commit()
        
        # 4. Show kết quả
        cursor.execute("SELECT name, grade_level FROM subjects ORDER BY name, grade_level")
        rows = cursor.fetchall()
        print("\nDANH SÁCH MÔN HỌC HIỆN TẠI:")
        for r in rows:
            print(f"- {r[0]} {r[1]}")

if __name__ == '__main__':
    cleanup()
