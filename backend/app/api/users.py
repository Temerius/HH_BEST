from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import os
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.core.config import settings

router = APIRouter()

# Директория для хранения аватарок
AVATAR_DIR = Path("img")
AVATAR_DIR.mkdir(exist_ok=True)
DEFAULT_AVATAR = AVATAR_DIR / "ava.png"


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление профиля текущего пользователя"""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Загрузка аватарки пользователя"""
    # Проверяем тип файла
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Генерируем имя файла
    file_extension = Path(file.filename).suffix if file.filename else '.png'
    avatar_filename = f"{current_user.id}{file_extension}"
    avatar_path = AVATAR_DIR / avatar_filename
    
    # Сохраняем файл
    try:
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Обновляем URL аватарки в базе данных
        # В продакшене здесь должен быть полный URL, пока используем относительный путь
        current_user.avatar_url = f"/api/users/avatar/{avatar_filename}"
        db.commit()
        db.refresh(current_user)
        
        return current_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving avatar: {str(e)}"
        )


@router.get("/avatar/{filename}")
async def get_avatar(filename: str):
    """Получение аватарки по имени файла"""
    # Безопасность: проверяем, что filename не содержит путь
    if '/' in filename or '..' in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    avatar_path = AVATAR_DIR / filename
    
    if not avatar_path.exists():
        # Возвращаем аватарку по умолчанию
        if DEFAULT_AVATAR.exists():
            return FileResponse(DEFAULT_AVATAR)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found"
        )
    
    return FileResponse(avatar_path)

