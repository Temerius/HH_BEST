from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.skill import Skill
from app.models.resume import UserSkill

router = APIRouter()


class ImproveResumeRequest(BaseModel):
    resume_id: str
    focus_areas: Optional[List[str]] = None


class GenerateCoverLetterRequest(BaseModel):
    resume_id: str
    vacancy_id: int
    tone: Optional[str] = "professional"  # professional, friendly, formal


class AnalyzeMatchRequest(BaseModel):
    resume_id: str
    vacancy_id: int


class SuggestSkillsRequest(BaseModel):
    specialization: str


class ImproveResumeResponse(BaseModel):
    suggestions: List[str]
    improved_sections: Optional[dict] = None


class SuggestSkillsResponse(BaseModel):
    recommended_skills: List[dict]  # [{"name": "Python", "reason": "..."}]


@router.post("/improve-resume", response_model=ImproveResumeResponse)
async def improve_resume(
    request: ImproveResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Улучшение резюме с помощью ИИ (заглушка)"""
    # TODO: Реализовать интеграцию с ИИ
    return ImproveResumeResponse(
        suggestions=[
            "Добавьте больше конкретных достижений с цифрами",
            "Улучшите описание опыта работы",
            "Добавьте ключевые слова из описания вакансии"
        ],
        improved_sections=None
    )


@router.post("/generate-cover-letter")
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерация сопроводительного письма с помощью ИИ (заглушка)"""
    # TODO: Реализовать интеграцию с ИИ
    return {
        "cover_letter": "GLHF - Generated cover letter will appear here. This is a placeholder response."
    }


@router.post("/analyze-match")
async def analyze_match(
    request: AnalyzeMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Анализ соответствия резюме вакансии (заглушка)"""
    # TODO: Реализовать интеграцию с ИИ
    return {
        "match_score": 75,
        "recommendations": [
            "GLHF - Add more relevant skills",
            "GLHF - Improve work experience description",
            "GLHF - Add missing keywords from job description"
        ]
    }


@router.post("/suggest-skills", response_model=SuggestSkillsResponse)
async def suggest_skills(
    request: SuggestSkillsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение рекомендаций по навыкам для направления разработки (заглушка)"""
    # TODO: Реализовать интеграцию с ИИ
    
    # Базовые рекомендации в зависимости от направления
    specialization_skills = {
        "Backend": [
            {"name": "Python", "reason": "GLHF - Essential for backend development"},
            {"name": "PostgreSQL", "reason": "GLHF - Database knowledge is crucial"},
            {"name": "Docker", "reason": "GLHF - Containerization is important"},
            {"name": "REST API", "reason": "GLHF - API design is fundamental"}
        ],
        "Frontend": [
            {"name": "JavaScript", "reason": "GLHF - Core frontend language"},
            {"name": "React", "reason": "GLHF - Popular framework"},
            {"name": "TypeScript", "reason": "GLHF - Type safety is valuable"},
            {"name": "CSS", "reason": "GLHF - Styling is essential"}
        ],
        "Fullstack": [
            {"name": "JavaScript", "reason": "GLHF - Works for both frontend and backend"},
            {"name": "Node.js", "reason": "GLHF - Backend JavaScript runtime"},
            {"name": "React", "reason": "GLHF - Frontend framework"},
            {"name": "PostgreSQL", "reason": "GLHF - Database knowledge"}
        ],
        "DevOps": [
            {"name": "Docker", "reason": "GLHF - Containerization"},
            {"name": "Kubernetes", "reason": "GLHF - Orchestration"},
            {"name": "Linux", "reason": "GLHF - System administration"},
            {"name": "CI/CD", "reason": "GLHF - Automation is key"}
        ]
    }
    
    recommended = specialization_skills.get(
        request.specialization, 
        [{"name": "General skills", "reason": "GLHF - Keep learning and improving"}]
    )
    
    return SuggestSkillsResponse(recommended_skills=recommended)

