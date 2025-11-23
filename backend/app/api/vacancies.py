from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional
from app.core.database import get_db
from app.models.vacancy import Vacancy, Employer, Area
from app.schemas.vacancy import VacancyResponse, VacancyListResponse, VacancyFilters

router = APIRouter()


@router.get("", response_model=VacancyListResponse)
async def get_vacancies(
    text: Optional[str] = Query(None),
    area_id: Optional[str] = Query(None),
    salary_from: Optional[int] = Query(None),
    salary_to: Optional[int] = Query(None),
    experience_id: Optional[str] = Query(None),
    employment_id: Optional[str] = Query(None),
    work_format_id: Optional[str] = Query(None),
    professional_role_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получение списка вакансий с фильтрацией"""
    query = db.query(Vacancy).join(Employer).join(Area).filter(Vacancy.archived == False)
    
    # Фильтры
    if text:
        query = query.filter(
            or_(
                Vacancy.name.ilike(f"%{text}%"),
                Vacancy.snippet_requirement.ilike(f"%{text}%"),
                Vacancy.snippet_responsibility.ilike(f"%{text}%"),
                Vacancy.description.ilike(f"%{text}%")
            )
        )
    
    if area_id:
        query = query.filter(Vacancy.area_id == area_id)
    
    if salary_from:
        query = query.filter(
            or_(
                Vacancy.salary_from >= salary_from,
                Vacancy.salary_to >= salary_from
            )
        )
    
    if salary_to:
        query = query.filter(
            or_(
                Vacancy.salary_from <= salary_to,
                Vacancy.salary_to <= salary_to
            )
        )
    
    if experience_id:
        query = query.filter(Vacancy.experience_id == experience_id)
    
    if employment_id:
        query = query.filter(Vacancy.employment_id == employment_id)
    
    if work_format_id:
        query = query.filter(Vacancy.work_format_id == work_format_id)
    
    # Подсчет общего количества
    total = query.count()
    
    # Пагинация
    offset = (page - 1) * per_page
    vacancies = query.order_by(Vacancy.published_at.desc()).offset(offset).limit(per_page).all()
    
    # Формируем ответ
    items = []
    for vacancy in vacancies:
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
            salary_from=vacancy.salary_from,
            salary_to=vacancy.salary_to,
            salary_currency=vacancy.salary_currency,
            salary_gross=vacancy.salary_gross,
            snippet_requirement=vacancy.snippet_requirement,
            snippet_responsibility=vacancy.snippet_responsibility,
            description=vacancy.description,
            schedule_name=vacancy.schedule_name,
            experience_name=vacancy.experience_name,
            employment_name=vacancy.employment_name,
            work_format_name=vacancy.work_format_name,
            published_at=vacancy.published_at,
            alternate_url=vacancy.alternate_url,
            archived=vacancy.archived
        ))
    
    return VacancyListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(vacancy_id: int, db: Session = Depends(get_db)):
    """Получение детальной информации о вакансии"""
    vacancy = db.query(Vacancy).filter(
        Vacancy.id == vacancy_id,
        Vacancy.archived == False
    ).first()
    
    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )
    
    return VacancyResponse(
        id=vacancy.id,
        name=vacancy.name,
        premium=vacancy.premium,
        employer_id=vacancy.employer_id,
        employer_name=vacancy.employer.name if vacancy.employer else None,
        area_id=vacancy.area_id,
        area_name=vacancy.area.name if vacancy.area else None,
        address_city=vacancy.address_city,
        address_raw=vacancy.address_raw,
        salary_from=vacancy.salary_from,
        salary_to=vacancy.salary_to,
        salary_currency=vacancy.salary_currency,
        salary_gross=vacancy.salary_gross,
        snippet_requirement=vacancy.snippet_requirement,
        snippet_responsibility=vacancy.snippet_responsibility,
        description=vacancy.description,
        schedule_name=vacancy.schedule_name,
        experience_name=vacancy.experience_name,
        employment_name=vacancy.employment_name,
        work_format_name=vacancy.work_format_name,
        published_at=vacancy.published_at,
        alternate_url=vacancy.alternate_url,
        archived=vacancy.archived
    )

