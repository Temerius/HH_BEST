from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.resume import Resume, UserSkill, ResumeText
from app.models.skill import Skill
from app.models.vacancy import Vacancy, VacancySkill, vacancy_skills
from app.services.ai_service import ai_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ImproveResumeRequest(BaseModel):
    vacancy_id: int


class GenerateCoverLetterRequest(BaseModel):
    vacancy_id: int
    tone: Optional[str] = "professional"  # professional, friendly, formal


class AnalyzeMatchRequest(BaseModel):
    resume_id: str
    vacancy_id: int


class SuggestSkillsRequest(BaseModel):
    specialization: str


class ImproveResumeResponse(BaseModel):
    recommendations: str  # Полный текст рекомендаций от AI


class SuggestSkillsResponse(BaseModel):
    recommended_skills: List[dict]  # [{"name": "Python", "reason": "..."}]


@router.post("/improve-resume", response_model=ImproveResumeResponse)
async def improve_resume(
    request: ImproveResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Улучшение резюме с помощью ИИ для конкретной вакансии"""
    try:
        # Получаем вакансию
        vacancy = db.query(Vacancy).filter(Vacancy.id == request.vacancy_id).first()
        if not vacancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vacancy not found"
            )
        
        # Получаем резюме пользователя с файлом (основное)
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_active == True,
            Resume.file_path.isnot(None)
        ).order_by(Resume.is_primary.desc(), Resume.created_at.desc()).first()
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found. Please upload your resume first."
            )
        
        # Получаем навыки пользователя
        user_skills = db.query(UserSkill, Skill).join(
            Skill, UserSkill.skill_id == Skill.id
        ).filter(UserSkill.user_id == current_user.id).all()
        
        skills_list = [{"name": skill.name, "level": us.level} for us, skill in user_skills]
        
        # Получаем текст резюме из PDF
        resume_text_record = db.query(ResumeText).filter(ResumeText.user_id == current_user.id).first()
        pdf_text = resume_text_record.text if resume_text_record and resume_text_record.text else ""
        
        # Формируем данные резюме
        resume_data = {
            "first_name": current_user.first_name or "",
            "last_name": current_user.last_name or "",
            "position": resume.position or "",
            "experience_years": resume.experience_years,
            "about": resume.about or "",
            "education": resume.education or "",
            "skills": skills_list,
            "work_experience": resume.work_experience or [],
            "pdf_text": pdf_text  # Текст из PDF файла
        }
        
        # Получаем навыки вакансии (используем тот же подход, что и в vacancies.py)
        vacancy_skills_list = []
        try:
            # Пробуем получить через relationship
            if hasattr(vacancy, 'skills_rel') and vacancy.skills_rel:
                vacancy_skills_list = [skill.name for skill in vacancy.skills_rel]
            else:
                # Fallback: прямой запрос через join
                skills_query = db.query(VacancySkill).join(vacancy_skills).filter(
                    vacancy_skills.c.vacancy_id == vacancy.id
                ).all()
                vacancy_skills_list = [skill.name for skill in skills_query]
        except Exception as e:
            logger.warning(f"Could not fetch vacancy skills: {e}")
            vacancy_skills_list = []
        
        vacancy_data = {
            "name": vacancy.name,
            "employer_name": vacancy.employer.name if vacancy.employer else "",
            "description": vacancy.description_html or vacancy.description_text or "",
            "experience_name": vacancy.experience_name or "",
            "employment_name": vacancy.employment_name or "",
            "skills": vacancy_skills_list
        }
        
        # Генерируем рекомендации через AI
        logger.info(f"Generating resume improvements for user {current_user.id} and vacancy {request.vacancy_id}")
        recommendations = ai_service.improve_resume(resume_data, vacancy_data)
        
        return ImproveResumeResponse(recommendations=recommendations)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error improving resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.post("/generate-cover-letter")
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерация сопроводительного письма с помощью ИИ на основе резюме и вакансии"""
    try:
        # Получаем вакансию
        vacancy = db.query(Vacancy).filter(Vacancy.id == request.vacancy_id).first()
        if not vacancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vacancy not found"
            )
        
        # Получаем резюме пользователя с файлом (основное)
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_active == True,
            Resume.file_path.isnot(None)
        ).order_by(Resume.is_primary.desc(), Resume.created_at.desc()).first()
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found. Please upload your resume first."
            )
        
        # Получаем навыки пользователя
        user_skills = db.query(UserSkill, Skill).join(
            Skill, UserSkill.skill_id == Skill.id
        ).filter(UserSkill.user_id == current_user.id).all()
        
        skills_list = [{"name": skill.name, "level": us.level} for us, skill in user_skills]
        
        # Получаем текст резюме из PDF
        resume_text_record = db.query(ResumeText).filter(ResumeText.user_id == current_user.id).first()
        pdf_text = resume_text_record.text if resume_text_record and resume_text_record.text else ""
        
        # Формируем данные резюме
        resume_data = {
            "first_name": current_user.first_name or "",
            "last_name": current_user.last_name or "",
            "position": resume.position or "",
            "experience_years": resume.experience_years,
            "about": resume.about or "",
            "education": resume.education or "",
            "skills": skills_list,
            "work_experience": resume.work_experience or [],
            "pdf_text": pdf_text  # Текст из PDF файла
        }
        
        # Получаем навыки вакансии (используем тот же подход, что и в vacancies.py)
        vacancy_skills_list = []
        try:
            # Пробуем получить через relationship
            if hasattr(vacancy, 'skills_rel') and vacancy.skills_rel:
                vacancy_skills_list = [skill.name for skill in vacancy.skills_rel]
            else:
                # Fallback: прямой запрос через join
                skills_query = db.query(VacancySkill).join(vacancy_skills).filter(
                    vacancy_skills.c.vacancy_id == vacancy.id
                ).all()
                vacancy_skills_list = [skill.name for skill in skills_query]
        except Exception as e:
            logger.warning(f"Could not fetch vacancy skills: {e}")
            vacancy_skills_list = []
        
        vacancy_data = {
            "name": vacancy.name,
            "employer_name": vacancy.employer.name if vacancy.employer else "",
            "description": vacancy.description_html or vacancy.description_text or "",
            "experience_name": vacancy.experience_name or "",
            "employment_name": vacancy.employment_name or "",
            "skills": vacancy_skills_list
        }
        
        # Генерируем сопроводительное письмо через AI
        logger.info(f"Generating cover letter for user {current_user.id} and vacancy {request.vacancy_id}")
        cover_letter = ai_service.generate_cover_letter(resume_data, vacancy_data, request.tone)
        
        return {
            "cover_letter": cover_letter
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating cover letter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating cover letter: {str(e)}"
        )


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

