# EduTutor AI - System Architecture

## Overview
EduTutor AI is a cloud-based intelligent tutoring system that leverages Google Vertex AI to provide personalized learning experiences.

## Architecture Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    Client Layer                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  React Frontend (Web App)                       │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         ▼                    ▼
     HTTPS/REST         WebSocket
         │                  │
┌────────┴──────────────────┴────────────────────────────┐
│              Nginx Reverse Proxy                       │
│  (Load Balancing, SSL/TLS, Static Files)             │
└────────┬──────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
┌────────────────────────┐  ┌──────────────────┐
│  Django REST API       │  │  WebSocket       │
│  ┌────────────────┐    │  │  Server          │
│  │ Auth Service   │    │  │ (Real-time Chat) │
│  │ Chat Service   │────┼──┤                  │
│  │ Quiz Service   │    │  │                  │
│  │ Learning Path  │    │  └──────────────────┘
│  └────────────────┘    │
└────┬─────────────┬─────┘
     │             │
     ▼             ▼
┌──────────────┐  ┌─────────────────────────┐
│ PostgreSQL   │  │ AI Integration Layer    │
│ Database     │  │ ┌─────────────────────┐ │
│              │  │ │ Vertex AI Client    │ │
│ ┌──────────┐ │  │ │ RAG Pipeline        │ │
│ │ Users    │ │  │ │ Embeddings Engine   │ │
│ │ Quiz     │ │  │ │ Learning Path Gen   │ │
│ │ Messages │ │  │ └─────────────────────┘ │
│ └──────────┘ │  └──────────┬──────────────┘
└──────────────┘             │
                    ┌────────┴────────┐
                    ▼                 ▼
              ┌──────────────┐  ┌─────────────┐
              │   Redis      │  │ Google Cloud│
              │   Cache      │  │ ┌─────────┐ │
              └──────────────┘  │ │Vertex AI│ │
                                │ │Models   │ │
                                │ └─────────┘ │
                                │ ┌─────────┐ │
                                │ │ Storage │ │
                                │ │ (PDFs)  │ │
                                │ └─────────┘ │
                                └─────────────┘
```

## Core Components

### 1. Frontend (React.js)
- Modern responsive UI
- Real-time chat interface
- Quiz/Assessment pages
- Learning dashboard
- Admin panel

### 2. Backend (Django REST Framework)
- RESTful APIs
- User authentication & authorization
- Business logic for all features
- Database models
- Integration with AI services

### 3. AI Integration Layer
- **Vertex AI Client**: Manages connections to Google Vertex AI
- **RAG Pipeline**: Retrieval-Augmented Generation from SGK database
- **Embeddings Engine**: Text vectorization using sentence-transformers
- **Learning Path Generator**: Creates personalized learning paths

### 4. Data Layer
- **PostgreSQL**: Main relational database
- **Redis**: Caching and real-time data
- **Cloud Storage**: PDF files and embeddings

### 5. Infrastructure
- **Docker**: Containerization
- **Nginx**: Reverse proxy and load balancer
- **GCP**: Cloud hosting and AI services

## Data Flow

### Chat Flow
```
User Message
    ↓
REST API
    ↓
Django View (Chat App)
    ↓
Check Redis Cache
    ↓ (if miss)
Extract Embeddings
    ↓
Search Vector DB (RAG)
    ↓
Build Prompt with Context
    ↓
Call Vertex AI Model
    ↓
Process Response
    ↓
Cache Result
    ↓
Return to Frontend
```

### Quiz Submission Flow
```
Submit Quiz
    ↓
Validate Answers
    ↓
Calculate Score
    ↓
Evaluate Performance
    ↓
Generate Feedback (via AI)
    ↓
Update Learning Path
    ↓
Save Results to DB
    ↓
Return Score & Recommendations
```

## Scalability Considerations

1. **Horizontal Scaling**
   - Run multiple Django instances behind Nginx
   - Connection pooling for database
   - Redis cluster for caching

2. **Optimization**
   - Async tasks with Celery
   - Query optimization with Django ORM
   - Index frequently accessed tables
   - Caching strategy for embeddings

3. **Performance**
   - CDN for static assets
   - Batch processing for embeddings
   - Database replication
   - API rate limiting

## Security

- JWT authentication
- HTTPS/SSL encryption
- CORS policy enforcement
- Input validation & sanitization
- SQL injection protection (Django ORM)
- Rate limiting per user/IP
- Service account key management

## Deployment

See `infrastructure/` directory for Docker and deployment configs.
