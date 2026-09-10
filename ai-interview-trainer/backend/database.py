import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import get_settings

settings = get_settings()

db_url = settings.DATABASE_URL

if db_url.startswith("mysql"):
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
        )
        conn.close()
    except Exception:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "interview.db")
        db_url = f"sqlite:///{db_path}"
        print(f"MySQL not available. Using SQLite: {db_path}")

if db_url.startswith("sqlite"):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
