from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database - можно указать либо DATABASE_URL, либо компоненты
    DATABASE_URL: str = ""  # Если указан, будет использован напрямую
    POSTGRES_USER: str = "kiselevas"
    POSTGRES_PASSWORD: str = "qwerty"
    POSTGRES_DB: str = "hh_data"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    
    def get_database_url(self) -> str:
        """Получает DATABASE_URL - либо из переменной, либо формирует из компонентов"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # JWT (секретные ключи не должны быть в .env, используются значения по умолчанию)
    SECRET_KEY: str = "hahabest-secret-key-change-in-production-2025"
    REFRESH_SECRET_KEY: str = "hahabest-refresh-secret-key-change-in-production-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # OAuth Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """Преобразует строку CORS_ORIGINS в список"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # Frontend URL для OAuth redirect
    FRONTEND_URL: str = "http://localhost:3000"
    
    # AI Providers
    AI_PROVIDER: str = "nebius"  # или "azure"
    NEBius_API_KEY: str = ""
    NEBius_API_URL: str = "https://api.studio.nebius.ai/v1/chat/completions"
    NEBius_MODEL: str = "Qwen/Qwen3-235B-A22B-Thinking-2507"
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Позволяем переопределить через переменные окружения
        extra = "allow"


settings = Settings()

