from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pathlib import Path
import shutil
import os
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeResponse

router = APIRouter()

# Директория для хранения PDF резюме
RESUME_DIR = Path("resumes")
RESUME_DIR.mkdir(exist_ok=True)


@router.get("", response_model=List[ResumeResponse])
async def get_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение списка резюме текущего пользователя"""
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).order_by(Resume.is_primary.desc(), Resume.created_at.desc()).all()
    
    return resumes


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    resume_data: ResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание нового резюме"""
    # Если это основное резюме, снимаем флаг с других
    if resume_data.is_primary:
        db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_primary == True
        ).update({"is_primary": False})
    
    db_resume = Resume(
        user_id=current_user.id,
        **resume_data.dict()
    )
    
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    
    return db_resume


@router.get("/file", response_class=FileResponse)
async def get_resume_file(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение PDF файла резюме текущего пользователя"""
    print(f"🔍 [GET /file] User ID: {current_user.id}")
    
    # Находим резюме с файлом
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True,
        Resume.file_path.isnot(None)
    ).first()
    
    print(f"🔍 [GET /file] Resume found: {resume is not None}")
    if resume:
        print(f"🔍 [GET /file] Resume file_path: {resume.file_path}")
    
    if not resume or not resume.file_path:
        print(f"❌ [GET /file] Resume or file_path not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found"
        )
    
    # Файл хранится как {user_id}.pdf
    resume_filename = f"{current_user.id}.pdf"
    resume_path = RESUME_DIR / resume_filename
    
    print(f"🔍 [GET /file] Looking for file: {resume_path}")
    print(f"🔍 [GET /file] File exists: {resume_path.exists()}")
    print(f"🔍 [GET /file] RESUME_DIR: {RESUME_DIR}")
    print(f"🔍 [GET /file] RESUME_DIR absolute: {RESUME_DIR.absolute()}")
    
    if not resume_path.exists():
        print(f"❌ [GET /file] File not found on disk: {resume_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found on disk"
        )
    
    print(f"✅ [GET /file] Returning file: {resume_path}")
    return FileResponse(
        resume_path,
        media_type="application/pdf",
        filename="resume.pdf"
    )


@router.delete("/file", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume_file(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление PDF файла резюме текущего пользователя"""
    print(f"🔍 [DELETE /file] User ID: {current_user.id}")
    
    # Находим резюме с файлом
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True,
        Resume.file_path.isnot(None)
    ).first()
    
    print(f"🔍 [DELETE /file] Resume found: {resume is not None}")
    if resume:
        print(f"🔍 [DELETE /file] Resume file_path: {resume.file_path}")
    
    if not resume or not resume.file_path:
        print(f"❌ [DELETE /file] Resume or file_path not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file not found"
        )
    
    # Удаляем файл
    resume_filename = f"{current_user.id}.pdf"
    resume_path = RESUME_DIR / resume_filename
    
    print(f"🔍 [DELETE /file] Looking for file: {resume_path}")
    print(f"🔍 [DELETE /file] File exists: {resume_path.exists()}")
    
    if resume_path.exists():
        try:
            resume_path.unlink()
            print(f"✅ [DELETE /file] File deleted: {resume_path}")
        except Exception as e:
            print(f"❌ [DELETE /file] Error deleting file: {e}")
    
    # Удаляем путь к файлу из базы данных
    resume.file_path = None
    db.commit()
    print(f"✅ [DELETE /file] File path removed from DB")
    
    return None


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение резюме по ID"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: UUID,
    resume_update: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление резюме"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    update_data = resume_update.dict(exclude_unset=True)
    
    # Если устанавливаем основное резюме, снимаем флаг с других
    if update_data.get("is_primary") == True:
        db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_primary == True,
            Resume.id != resume_id
        ).update({"is_primary": False})
    
    for field, value in update_data.items():
        setattr(resume, field, value)
    
    db.commit()
    db.refresh(resume)
    
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление резюме (мягкое удаление)"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    resume.is_active = False
    db.commit()
    
    return None


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Загрузка PDF резюме. Если у пользователя уже есть резюме с файлом, оно будет заменено."""
    print(f"🔍 [POST /upload] User ID: {current_user.id}")
    print(f"🔍 [POST /upload] File name: {file.filename}")
    print(f"🔍 [POST /upload] File content_type: {file.content_type}")
    
    # Проверяем тип файла
    if not file.content_type or file.content_type != 'application/pdf':
        print(f"❌ [POST /upload] Invalid file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    # Проверяем размер файла (максимум 10 МБ)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    print(f"🔍 [POST /upload] File size: {file_size} bytes")
    if file_size > 10 * 1024 * 1024:  # 10 МБ
        print(f"❌ [POST /upload] File too large: {file_size} bytes")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 10 MB"
        )
    
    # Находим существующее резюме пользователя с файлом или создаем новое
    existing_resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True,
        Resume.file_path.isnot(None)
    ).first()
    
    print(f"🔍 [POST /upload] Existing resume found: {existing_resume is not None}")
    if existing_resume:
        print(f"🔍 [POST /upload] Existing resume file_path: {existing_resume.file_path}")
    
    # Если есть старое резюме с файлом, удаляем старый файл
    if existing_resume and existing_resume.file_path:
        old_resume_filename = f"{current_user.id}.pdf"
        old_file_path = RESUME_DIR / old_resume_filename
        if old_file_path.exists():
            try:
                old_file_path.unlink()
                print(f"✅ [POST /upload] Old file deleted: {old_file_path}")
            except Exception as e:
                print(f"❌ [POST /upload] Error deleting old file: {e}")
    
    # Генерируем имя файла: user_id.pdf
    resume_filename = f"{current_user.id}.pdf"
    resume_path = RESUME_DIR / resume_filename
    
    print(f"🔍 [POST /upload] Saving file to: {resume_path}")
    print(f"🔍 [POST /upload] RESUME_DIR: {RESUME_DIR}")
    print(f"🔍 [POST /upload] RESUME_DIR absolute: {RESUME_DIR.absolute()}")
    
    # Сохраняем файл
    try:
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"✅ [POST /upload] File saved: {resume_path}")
        print(f"🔍 [POST /upload] File exists after save: {resume_path.exists()}")
        
        # Обновляем или создаем резюме
        if existing_resume:
            # Обновляем существующее резюме
            existing_resume.file_path = f"/api/resumes/file"
            db.commit()
            db.refresh(existing_resume)
            print(f"✅ [POST /upload] Resume updated, file_path: {existing_resume.file_path}")
            return existing_resume
        else:
            # Создаем новое резюме
            new_resume = Resume(
                user_id=current_user.id,
                title="Резюме",
                file_path=f"/api/resumes/file",
                is_primary=True,
                is_active=True
            )
            db.add(new_resume)
            db.commit()
            db.refresh(new_resume)
            print(f"✅ [POST /upload] New resume created, file_path: {new_resume.file_path}")
            return new_resume
    except Exception as e:
        print(f"❌ [POST /upload] Error saving file: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving resume file: {str(e)}"
        )

