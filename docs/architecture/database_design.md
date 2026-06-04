# Database Design

## Entity Relationship Diagram

```
Users
├── id (PK)
├── username (UNIQUE)
├── email (UNIQUE)
├── password_hash
├── full_name
├── grade_level (7-9)
├── avatar_url
├── created_at
└── updated_at

Subjects
├── id (PK)
├── name
├── description
└── icon_url

Chapters
├── id (PK)
├── subject_id (FK -> Subjects)
├── title
├── description
└── order

Lessons
├── id (PK)
├── chapter_id (FK -> Chapters)
├── title
├── content
└── order

Messages
├── id (PK)
├── user_id (FK -> Users)
├── subject_id (FK -> Subjects)
├── role (user/assistant)
├── content
├── created_at

Quiz
├── id (PK)
├── subject_id (FK -> Subjects)
├── title
├── description

Questions
├── id (PK)
├── quiz_id (FK -> Quiz)
├── question_text
├── question_type (multiple_choice/essay)
└── order

Answers
├── id (PK)
├── question_id (FK -> Questions)
├── is_correct
├── answer_text
└── order

QuizSubmissions
├── id (PK)
├── user_id (FK -> Users)
├── quiz_id (FK -> Quiz)
├── score
├── submitted_at

LearningPath
├── id (PK)
├── user_id (FK -> Users)
├── current_chapter
├── progress_percentage
└── updated_at

Embeddings (Vector Store)
├── id (PK)
├── lesson_id (FK -> Lessons)
├── chunk_id
├── text_chunk
├── embedding (vector)
└── updated_at
```

## Tables

### Users Table
```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    grade_level INT CHECK (grade_level BETWEEN 7 AND 9),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Subjects Table
```sql
CREATE TABLE subjects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    icon_url TEXT,
    UNIQUE(name)
);

-- Insert default subjects
INSERT INTO subjects (name) VALUES
    ('Toán'),
    ('Vật lý'),
    ('Hóa học'),
    ('Lịch sử'),
    ('Địa lý'),
    ('Công dân');
```

### Messages Table (Chat History)
```sql
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES subjects(id),
    role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tokens_used INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_user_subject ON messages(user_id, subject_id);
```

### Quiz Tables
```sql
CREATE TABLE quiz (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL REFERENCES subjects(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE questions (
    id BIGSERIAL PRIMARY KEY,
    quiz_id BIGINT NOT NULL REFERENCES quiz(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    order_num INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quiz_submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quiz_id BIGINT NOT NULL REFERENCES quiz(id),
    score DECIMAL(5,2),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quiz_submissions_user ON quiz_submissions(user_id);
```

### Learning Path Table
```sql
CREATE TABLE learning_path (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_chapter BIGINT REFERENCES chapters(id),
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Indexing Strategy

```sql
-- Performance indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subjects_name ON subjects(name);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_quiz_submissions_user_quiz ON quiz_submissions(user_id, quiz_id);
```

## Constraints & Relationships

- Users → Messages (1:N)
- Users → Quiz Submissions (1:N)
- Users → Learning Path (1:1)
- Subjects → Messages (1:N)
- Subjects → Quiz (1:N)
- Quiz → Questions (1:N)
- Questions → Answers (1:N)
