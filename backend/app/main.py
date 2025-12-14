from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from app.api import vacancies, users, auth, resumes, favorites, ai, metadata, skills, areas, metro
from app.core.config import settings

app = FastAPI(
    title="HAHABEST API",
    description="API для платформы поиска работы с ИИ-помощником",
    version="1.0.0"
)

# Session middleware для OAuth (должен быть перед CORS)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=3600,  # 1 час
    same_site="lax"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(vacancies.router, prefix="/api/vacancies", tags=["vacancies"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["favorites"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])
app.include_router(areas.router, prefix="/api/areas", tags=["areas"])
app.include_router(metro.router, prefix="/api/metro", tags=["metro"])

# Статические файлы для аватарок
img_dir = Path("img")
img_dir.mkdir(exist_ok=True)
app.mount("/api/users/avatar", StaticFiles(directory=str(img_dir)), name="avatars")


@app.get("/")
async def root():
    return {"message": "HAHABEST API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

