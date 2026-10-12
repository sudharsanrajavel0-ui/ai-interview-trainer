import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from backend.config import get_settings
from backend.database import engine, Base, SessionLocal
from backend.routes import auth, interview, dashboard, admin
from backend.models import SystemErrorEvent

logger = logging.getLogger("ai_interview")
logging.basicConfig(level=logging.INFO)

settings = get_settings()

Base.metadata.create_all(bind=engine)


def add_column_if_missing(table: str, column: str, ddl: str):
    from sqlalchemy import text

    with engine.connect() as conn:
        if conn.dialect.name == "sqlite":
            rows = conn.execute(
                text(f"PRAGMA table_info({table})")
            ).fetchall()
            names = {r[1] for r in rows}
        else:
            rows = conn.execute(
                text(
                    f"SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                ),
                {"t": table},
            ).fetchall()
            names = {r[0] for r in rows}

    if column not in names:
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info(f"Added column {table}.{column}")


add_column_if_missing(
    "questions",
    "question_type",
    "ALTER TABLE questions ADD COLUMN question_type VARCHAR(20) NOT NULL DEFAULT 'writing'",
)
add_column_if_missing(
    "questions",
    "options",
    "ALTER TABLE questions ADD COLUMN options TEXT NULL",
)
add_column_if_missing(
    "questions",
    "correct_answer",
    "ALTER TABLE questions ADD COLUMN correct_answer VARCHAR(10) NULL",
)

app = FastAPI(
    title="AI Interview Training System",
    description="Practice job interviews with AI-powered feedback",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    try:
        db = SessionLocal()
        try:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            error_event = SystemErrorEvent(
                path=request.url.path,
                method=request.method,
                status_code=500,
                error_type=type(exc).__name__,
                message=str(exc)[:500] if exc else None,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(error_event)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."},
    )

app.include_router(auth.router)
app.include_router(interview.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(frontend_dir, "login.html"))


@app.get("/register")
def serve_register():
    return FileResponse(os.path.join(frontend_dir, "register.html"))


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(os.path.join(frontend_dir, "dashboard.html"))


@app.get("/training")
@app.get("/interview")
def serve_interview():
    return FileResponse(os.path.join(frontend_dir, "interview.html"))


@app.get("/result")
def serve_result():
    return FileResponse(os.path.join(frontend_dir, "result.html"))


@app.get("/admin/login")
def serve_admin_login():
    return FileResponse(os.path.join(frontend_dir, "admin-login.html"))


@app.get("/admin")
def serve_admin(request: Request):
    if not admin.is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    return FileResponse(os.path.join(frontend_dir, "admin.html"))
