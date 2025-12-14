from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.favorite import FavoriteVacancy
from app.models.vacancy import Vacancy
from app.schemas.vacancy import VacancyResponse
from app.utils.text_processing import process_highlighttext

router = APIRouter()


@router.get("", response_model=List[VacancyResponse])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение списка избранных вакансий"""
    favorites = db.query(FavoriteVacancy).filter(
        FavoriteVacancy.user_id == current_user.id
    ).order_by(FavoriteVacancy.created_at.desc()).all()
    
    items = []
    for fav in favorites:
        vacancy = db.query(Vacancy).filter(Vacancy.id == fav.vacancy_id).first()
        if vacancy and not vacancy.archived:
            # Загружаем метро для вакансии
            metro_stations = []
            if hasattr(vacancy, 'metro_stations'):
                metro_stations = [
                    {"id": metro.id, "name": metro.name, "line_name": metro.line_name}
                    for metro in vacancy.metro_stations
                ]
            
            # Загружаем навыки для вакансии
            skills = []
            if hasattr(vacancy, 'skills_rel'):
                skills = [skill.name for skill in vacancy.skills_rel]
            else:
                # Fallback: прямой запрос через join
                from app.models.vacancy import VacancySkill, vacancy_skills
                skills_query = db.query(VacancySkill).join(vacancy_skills).filter(
                    vacancy_skills.c.vacancy_id == vacancy.id
                ).all()
                skills = [skill.name for skill in skills_query]
            
            items.append(VacancyResponse(
                id=vacancy.id,
                name=vacancy.name,
                premium=vacancy.premium,
                employer_id=vacancy.employer_id,
                employer_name=vacancy.employer.name if vacancy.employer else None,
                area_id=vacancy.area_id,
                area_name=vacancy.area.name if vacancy.area else None,
                address_city=vacancy.address_city,
                address_raw=vacancy.address_raw,
                address_lat=float(vacancy.address_lat) if vacancy.address_lat else None,
                address_lng=float(vacancy.address_lng) if vacancy.address_lng else None,
                salary_from=vacancy.salary_from,
                salary_to=vacancy.salary_to,
                salary_currency=vacancy.salary_currency,
                salary_gross=vacancy.salary_gross,
                salary_description=vacancy.salary_description,
                # Полные описания для rabota.by
                description=process_highlighttext(vacancy.description_html or vacancy.description_text),
                schedule_name=vacancy.schedule_name,
                experience_name=vacancy.experience_name,
                employment_name=vacancy.employment_name,
                metro_stations=metro_stations if metro_stations else None,
                skills=skills if skills else None,
                published_at=vacancy.published_at,
                archived=vacancy.archived
            ))
    
    return items


@router.post("/{vacancy_id}", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    vacancy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавление вакансии в избранное"""
    # Проверяем, существует ли вакансия
    vacancy = db.query(Vacancy).filter(
        Vacancy.id == vacancy_id,
        Vacancy.archived == False
    ).first()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )
    
    # Проверяем, не добавлена ли уже
    existing = db.query(FavoriteVacancy).filter(
        FavoriteVacancy.user_id == current_user.id,
        FavoriteVacancy.vacancy_id == vacancy_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vacancy already in favorites"
        )
    
    favorite = FavoriteVacancy(
        user_id=current_user.id,
        vacancy_id=vacancy_id
    )
    
    db.add(favorite)
    db.commit()
    
    return {"message": "Vacancy added to favorites"}


@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    vacancy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление вакансии из избранного"""
    favorite = db.query(FavoriteVacancy).filter(
        FavoriteVacancy.user_id == current_user.id,
        FavoriteVacancy.vacancy_id == vacancy_id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found"
        )
    
    db.delete(favorite)
    db.commit()
    
    return None

