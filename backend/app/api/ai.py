from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.ai.services import ResumeService, CoverLetterService, AnalysisService

router = APIRouter()


class ImproveResumeRequest(BaseModel):
    resume_id: str
    focus_areas: Optional[list[str]] = None


class GenerateCoverLetterRequest(BaseModel):
    resume_id: str
    vacancy_id: int
    tone: Optional[str] = "professional"  # professional, friendly, formal


class AnalyzeMatchRequest(BaseModel):
    resume_id: str
    vacancy_id: int


@router.post("/improve-resume")
async def improve_resume(
    request: ImproveResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Улучшение резюме с помощью ИИ"""
    # Заготовка - будет реализовано позже
    return {
        "message": "AI service not implemented yet",
        "improved_resume": None,
        "suggestions": []
    }


@router.post("/generate-cover-letter")
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерация сопроводительного письма с помощью ИИ"""
    # Заготовка - будет реализовано позже
    return {
        "message": "AI service not implemented yet",
        "cover_letter": None
    }


@router.post("/analyze-match")
async def analyze_match(
    request: AnalyzeMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Анализ соответствия резюме вакансии"""
    # Заготовка - будет реализовано позже
    return {
        "message": "AI service not implemented yet",
        "match_score": 0,
        "recommendations": []
    }

