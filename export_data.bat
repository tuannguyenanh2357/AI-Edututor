@echo off
echo 📤 Dang xuat du lieu tu Database ra file JSON...
echo    (Vui long cho trong giay lat, he thong dang dong goi hon 2600+ cau hoi)

docker exec edututor-backend python manage.py dumpdata subjects curriculum quiz gamification battle --indent 2 --output mastery_data.json

if %errorlevel% equ 0 (
    move backend\mastery_data.json mastery_data.json > nul
    echo ✅ Xuat du lieu thanh cong!
    echo 📂 File: mastery_data.json da san sang de commit len GitHub.
) else (
    echo ❌ Loi: Khong the xuat du lieu. Vui long kiem tra xem Docker dang chay khong.
)

pause
