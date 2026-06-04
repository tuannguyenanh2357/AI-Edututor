# EduTutor AI - Hệ Thống Gia Sư AI Thông Minh

Một nền tảng học tập thông minh sử dụng AI, cung cấp gia sư ảo cho 6 môn học trung học cơ sở.

## Tính Năng Chính

- **Chatbot AI Tutor**: Gia sư ảo tương tác cho 6 môn học (Toán, Vật lý, Hóa học, Lịch sử, Địa lý, Công dân)
- **RAG Pipeline**: Kỹ thuật Retrieval-Augmented Generation tự các sách giáo khoa
- **Personalized Learning Path**: Lộ trình học tập cá nhân hóa theo trình độ từng học sinh
- **Quiz & Assessment**: Hệ thống kiểm tra và đánh giá thành tích
- **Admin Dashboard**: Bảng điều khiển quản trị

## Công Nghệ

### Backend
- Django 4.x
- Django REST Framework
- MySQL
- Vertex AI / Google Cloud

### Frontend
- Angular

### Infrastructure
- Docker & Docker Compose
- Nginx
- GCP

## Cài Đặt Nhanh

### Yêu Cầu
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Bước 1: Clone và Setup
```bash
git clone <repo-url>
cd Capstone2---C2SE.07
cp .env.example .env
```

### Bước 2: Chỉnh Sửa .env
Chỉnh sửa các giá trị trong file `.env`:
- `GCP_PROJECT_ID`
- `VERTEX_API_KEY`
- Database settings

### Bước 3: Khởi Động với Docker Compose
```bash
docker-compose up -d --build
```

### Bước 4: Khởi Tạo Tự Động (Migration & Data)
Chạy lệnh setup để tự động migrate database và nạp dữ liệu sách giáo khoa:

**Dành cho Windows:**
```powershell
./setup.bat
```

**Dành cho Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

---

## 🧠 AI Service - Elite Upgrade (Multi-Agent)

Hệ thống AI đã được nâng cấp lên kiến trúc **Multi-Agent StateGraph** mạnh mẽ hơn, bao gồm các thành phần:

1.  **Planner**: Phân tích yêu cầu và chọn công cụ phù hợp (Python, Search, PDF Reader).
2.  **Executor**: Thực thi các công cụ kỹ thuật.
3.  **Synthesizer**: Tổng hợp bài giảng sư phạm từ dữ liệu thu được.
4.  **Reviewer**: Tự động kiểm duyệt lỗi và đảm bảo chất lượng phản hồi.

### Các tính năng "Elite":
- **Python Code Interpreter**: Thực hiện các phép tính toán học/vật lý phức tạp với độ chính xác 100%.
- **Smart PDF Reader**: Đọc chính xác nội dung trang sách nhờ hệ thống `books_metadata.json` (tự động xử lý độ lệch trang).
- **Mermaid Diagrams**: Tự động vẽ sơ đồ, biểu đồ minh họa hiện diện ngay trong khung chat.

### Cấu hình AI:
Nếu AI đọc lệch trang sách, hãy điều chỉnh thông số `offset` trong file:
`ai_service/books_metadata.json`

---

## Cấu Trúc Dự Án

```
Capstone2---C2SE.07/
├── backend/          # Django REST API (Python)
├── frontend/         # Angular Application (TypeScript)
├── ai_service/       # AI Logic & RAG Service (Python)
├── database/         # SQL initialization scripts
├── infrastructure/    # Nginx & GCP configurations
├── docs/              # Project documentation
├── setup.bat         # Windows setup automation
└── setup.sh          # Linux/macOS setup automation
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Đăng ký
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/logout` - Đăng xuất

### Chat
- `POST /api/chat/message` - Gửi tin nhắn tới AI tutor
- `GET /api/chat/history` - Lấy lịch sử trò chuyện

### Quiz
- `GET /api/quiz/` - Danh sách quiz
- `POST /api/quiz/submit` - Nộp bài làm

### Learning Path
- `GET /api/learning/path` - Lấy lộ trình học

## Hướng Dẫn Phát Triển

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Testing

```bash
# Backend
cd backend
python manage.py test

# Frontend
cd frontend
npm test
```

## Deployment

Xem tài liệu chi tiết trong `docs/deployment.md`

## Contributing

Vui lòng đọc `CONTRIBUTING.md` trước khi submit pull request.

## License

MIT License - xem `LICENSE` file chi tiết

## Liên Hệ

Để câu hỏi hoặc đóng góp, vui lòng tạo issue hoặc liên hệ qua email.
