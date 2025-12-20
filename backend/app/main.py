from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from urllib.parse import unquote
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

# Статические файлы для wait_gifs
wait_gifs_dir = Path("img/wait_gifs")
wait_gifs_dir.mkdir(parents=True, exist_ok=True)

# Создаем отдельный роутер для гифок, чтобы правильно обрабатывать имена с пробелами и скобками
wait_gifs_router = APIRouter()

@wait_gifs_router.get("/{filename:path}")
async def get_wait_gif(filename: str):
    """Получение гифки по имени файла"""
    # Декодируем имя файла
    filename = unquote(filename)
    
    # Безопасность: проверяем, что filename не содержит путь
    if '/' in filename or '..' in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )
    
    gif_path = wait_gifs_dir / filename
    
    if not gif_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"GIF not found: {filename}"
        )
    
    return FileResponse(
        gif_path,
        media_type="image/gif"
    )

app.include_router(wait_gifs_router, prefix="/api/wait-gifs", tags=["wait-gifs"])


@app.get("/")
async def root():
    return {"message": "HAHABEST API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

