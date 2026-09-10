# AI Interview Training System

A professional web application that allows users to practice job interviews with an AI-powered interviewer. Get instant feedback, scores, and improvement tips for any job role.

## Features

- **AI-Powered Questions** — Interview questions generated for your target role, type, and difficulty
- **Instant Scoring** — Immediate scores and detailed feedback on each answer (strengths, weaknesses, suggestions)
- **Model Answers** — Expert model answers to understand what interviewers expect
- **Performance Reports** — Detailed performance summaries after each interview
- **Multiple Job Roles** — Software Developer, Python Developer, Java Developer, Web Developer, Data Analyst
- **Adjustable Difficulty** — Beginner, Intermediate, or Advanced
- **Interview Types** — Technical, HR / Behavioral, or Mixed
- **Dashboard** — Track total interviews, average score, highest score, and history
- **Mock AI Mode** — Fully functional without an external AI API key

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3, FastAPI, Uvicorn |
| Database | MySQL (with SQLite fallback) |
| ORM | SQLAlchemy |
| AI | OpenAI-compatible API (configurable) |
| Auth | JWT (python-jose), bcrypt (passlib) |

## Architecture

```
Browser
    |
HTML/CSS/JavaScript
    |
FastAPI REST API
    |
    +-- AI Service
    |       |
    |   External AI API (or Mock Mode)
    |
    +-- Database Layer
            |
        MySQL / SQLite
```

## Project Structure

```
ai-interview-trainer/
├── backend/
│   ├── main.py              # FastAPI application entrypoint
│   ├── config.py             # Pydantic Settings configuration
│   ├── database.py           # SQLAlchemy engine + session
│   ├── models.py             # ORM models
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── routes/
│   │   ├── auth.py           # Registration, login, profile
│   │   ├── interview.py      # Interview CRUD, questions, answers
│   │   └── dashboard.py      # Dashboard statistics
│   ├── services/
│   │   └── ai_service.py     # AI question generation + evaluation
│   └── utils/
│       └── security.py       # JWT auth, password hashing
├── frontend/
│   ├── index.html            # Landing page
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── dashboard.html        # User dashboard
│   ├── interview.html        # Interview setup + live interview
│   ├── result.html           # Post-interview results
│   ├── css/style.css         # Complete CSS design system
│   └── js/
│       ├── api.js            # HTTP client + token management
│       ├── auth.js           # Login/register form handlers
│       ├── dashboard.js      # Dashboard data loading
│       ├── interview.js      # Interview flow orchestration
│       └── result.js         # Results page rendering
├── database/
│   └── schema.sql            # MySQL schema reference
├── .env.example              # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10+
- MySQL 8.0+ (or SQLite for development)
- Node.js not required (vanilla JS frontend)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-interview-trainer.git
cd ai-interview-trainer
```

### 2. Create virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
copy .env.example .env
```

Edit `.env` with your actual values.

### 5. MySQL setup (optional — SQLite works automatically)

```bash
mysql -u root -p < database/schema.sql
```

Or let SQLAlchemy create tables automatically on first run.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `mysql+pymysql://root:password@localhost:3306/ai_interview` |
| `MYSQL_HOST` | MySQL host | `localhost` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_USER` | MySQL username | `root` |
| `MYSQL_PASSWORD` | MySQL password | `password` |
| `MYSQL_DATABASE` | MySQL database name | `ai_interview` |
| `AI_API_KEY` | AI provider API key | `sk-placeholder` |
| `AI_MODEL` | AI model name | `gpt-3.5-turbo` |
| `AI_BASE_URL` | AI API base URL (OpenAI-compatible) | `https://api.openai.com/v1` |
| `SECRET_KEY` | JWT signing secret | — |
| `AI_MOCK_MODE` | Use mock AI (no API key needed) | `true` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:8000,http://127.0.0.1:8000` |

## How to Run

### Backend

```bash
cd ai-interview-trainer
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

The frontend is served automatically by FastAPI as static files. Once the backend is running, open:

```
http://localhost:8000
```

All pages are accessible directly through FastAPI routes.

## API Documentation

Once the server is running, visit:

```
http://localhost:8000/docs
```

### Endpoints

**Authentication:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and receive JWT token |
| GET | `/api/auth/me` | Get current user profile |

**Dashboard:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Get dashboard statistics |

**Interviews:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/interviews` | Create a new interview |
| GET | `/api/interviews` | List all user interviews |
| GET | `/api/interviews/{id}` | Get interview details with Q&A |
| POST | `/api/interviews/{id}/questions` | Get next AI-generated question |
| POST | `/api/interviews/{id}/answers` | Submit answer and get evaluation |
| POST | `/api/interviews/{id}/complete` | Complete interview and get overall feedback |

## AI Configuration

The system supports any OpenAI-compatible API. Configure via environment variables:

- **OpenAI**: Set `AI_API_KEY` to your OpenAI key
- **Azure OpenAI**: Set `AI_BASE_URL` to your Azure endpoint
- **Local LLM (Ollama)**: Set `AI_BASE_URL` to `http://localhost:11434/v1`
- **Other providers**: Any OpenAI-compatible endpoint works

When `AI_MOCK_MODE=true`, the system uses built-in questions and evaluations without calling any external API. This is ideal for development and demonstrations.

## Screenshots

> Add screenshots of the landing page, dashboard, interview screen, and results page here.

## Future Enhancements

- [ ] Voice-based interviews with speech-to-text
- [ ] Per-question timer
- [ ] Interview deletion and resume
- [ ] User profile editing
- [ ] Email verification and password reset
- [ ] Admin panel
- [ ] Pagination for interview history
- [ ] Docker deployment
- [ ] Unit and integration tests

## License

This project is built for learning and interview preparation purposes.
