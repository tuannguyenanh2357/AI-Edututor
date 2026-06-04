@echo off
setlocal enabledelayedexpansion

echo 🛠️  Dang thiet lap moi truong EduTutor...

:: 1. Kiem tra file .env (Rat quan trong cho Docker)
if not exist .env (
    echo ⚠️  Canh bao: Khong tim thay file .env
    if exist .env.example (
        echo    Dang tao file .env tu .env.example...
        copy .env.example .env
        echo ✅ Da tao file .env. Vui long kiem tra va chinh sua thong tin neu can.
    ) else (
        echo ❌ Loi: Khong tim thay file .env hoac .env.example.
        echo Vui long dam bao ban co file .env o thu muc goc.
        pause
        exit /b
    )
)

:: 2. Kiem tra Docker daemon dang chay
echo 🔍 Dang kiem tra Docker daemon...
docker info >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ Loi: Khong the ket noi voi Docker. Vui long dam bao:
    echo    1. Docker Desktop dang chay.
    echo    2. Neu dung Windows, hay thu switch context: 'docker context use default'
    pause
    exit /b
)

:: 2b. Kiem tra Docker Compose
set DOCKER_CMD=docker compose
%DOCKER_CMD% version >nul 2>&1
if !errorlevel! neq 0 (
    set DOCKER_CMD=docker-compose
    %DOCKER_CMD% version >nul 2>&1
    if !errorlevel! neq 0 (
        echo ❌ Loi: Khong tim thay Docker Compose. Vui long dam bao:
        echo    1. Docker Desktop dang chay.
        echo    2. Da cai dat Docker Compose.
        pause
        exit /b
    )
)

echo 🐳 Dang su dung: %DOCKER_CMD%
echo 🐳 Dang khoi dong cac Docker containers...
echo    (Luu y: Neu dung o buoc nay qua lau, hay kiem tra xem co ung dung nao dang dung cong 4200, 8000 hoac 3307 khong)
%DOCKER_CMD% up -d

:: 3. Kiem tra container backend co dang chay khong
echo 🔍 Dang kiem tra trang thai Backend...
timeout /t 5 >nul
%DOCKER_CMD% ps --filter "status=running" | findstr "backend" >nul
if !errorlevel! neq 0 (
    echo ❌ Loi: Container Backend khong khoi dong duoc. 
    echo    Thu chay 'docker compose up -d' thu cong de xem thong bao loi chi tiet.
    pause
    exit /b
)


echo ⏳ Dang cho Database san sang (khoang 20-30 giay)...
:wait_db
%DOCKER_CMD% exec db mysqladmin ping -h localhost -u user -ppassword --silent >nul 2>&1
if !errorlevel! neq 0 (
    echo    ...Database dang khoi tao, vui long cho...
    timeout /t 5 >nul
    goto wait_db
)
echo ✅ Database da san sang!

echo 📦 Dang chay database migrations...
%DOCKER_CMD% exec backend python manage.py migrate

if exist mastery_data.json (
    echo 📥 Phat hien file du lieu backup ^(mastery_data.json^).
    echo    Dang nạp du lieu tu file backup, vui long cho...
    docker cp mastery_data.json edututor-backend:/app/mastery_data.json
    %DOCKER_CMD% exec backend python manage.py loaddata mastery_data.json
    echo ✅ Da nạp du lieu tu file backup thanh cong!
) else (
    echo 💾 Dang nap du lieu khoi tao ^(Mon hoc, Danh muc ^& Sach giao khoa^)...
    %DOCKER_CMD% exec backend python scripts/init_data.py

    echo 🔄 Dang dong bo cau truc sach giao khoa ^(Chapters/Lessons^)...
    %DOCKER_CMD% exec backend python manage.py sync_textbooks
    
    echo 🧠 Dang nạp câu hỏi phân tầng Bloom ^(Đảm bảo 20 câu/chương^)...
    %DOCKER_CMD% exec backend python manage.py topup_questions --min_questions 20
)

echo 🧹 Dang don dep cau hoi yeu cau hinh anh (Khong ho tro UI)...
%DOCKER_CMD% exec backend python scripts/cleanup_visual_questions.py

echo 🚀 Dang nang cap cau hoi cu sang chuan Bloom Taxonomy...
%DOCKER_CMD% exec backend python scripts/fix_legacy_bloom.py

echo 🛠️  Dang tu sua lỗi du lieu (Self-healing Orphan Questions)...
%DOCKER_CMD% exec backend python scripts/db_self_heal.py

echo 🏰 Dang nap du lieu Dau truong ^& Cua hang (Shop Items)...
%DOCKER_CMD% exec backend python scripts/seed_arena.py

echo 🏅 Dang nap danh sach Huy hieu ^& Quests...
%DOCKER_CMD% exec backend python scripts/populate_gamification.py

echo 📈 Đảm bảo mọi chương đều có tối thiểu 20 câu hỏi...
%DOCKER_CMD% exec backend python manage.py topup_questions --min_questions 20

echo 📊 Kiem tra tong the chat luong va do phu ngan hang cau hoi...
%DOCKER_CMD% exec backend python scripts/subject_question_audit.py

echo ✨ HE THONG DA SAN SANG! 
echo 📚 Ngan bank voi hon 4000+ cau hoi da duoc kich hoat.
echo 🌐 Truy cap: http://localhost:4200
pause
