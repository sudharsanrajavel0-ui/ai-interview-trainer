from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/ai_interview"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "ai_interview"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"

    SECRET_KEY: str = "change-this-to-a-random-secret-string"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def effective_gemini_key(self) -> str:
        return self.GEMINI_API_KEY

    @property
    def effective_gemini_model(self) -> str:
        return self.GEMINI_MODEL


@lru_cache()
def get_settings() -> Settings:
    return Settings()
