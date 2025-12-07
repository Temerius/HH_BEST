from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select
from typing import Optional
from app.core.database import get_db
from app.models.vacancy import Vacancy, Employer, Area, Industry, Specialization, MetroStationBy, vacancy_metro_by, vacancy_specializations, vacancy_skills
from app.schemas.vacancy import VacancyResponse, VacancyListResponse, VacancyFilters
from app.utils.text_processing import process_highlighttext

router = APIRouter()


@router.get("", response_model=VacancyListResponse)
async def get_vacancies(
    text: Optional[str] = Query(None),
    area_id: Optional[str] = Query(None),
    metro_id: Optional[int] = Query(None),
    salary_from: Optional[int] = Query(None),
    salary_to: Optional[int] = Query(None),
    salary_currency: Optional[str] = Query(None),
    experience_id: Optional[str] = Query(None),
    employment_id: Optional[str] = Query(None),
    work_format_id: Optional[str] = Query(None),
    schedule_id: Optional[str] = Query(None),
    education_id: Optional[str] = Query(None),
    specialization_id: Optional[int] = Query(None),
    industry_id: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("published_at", regex="^(published_at|salary_from|salary_to|name)$"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
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
                Vacancy.description.ilike(f"%{text}%"),
                Vacancy.tasks.ilike(f"%{text}%"),
                Vacancy.requirements.ilike(f"%{text}%"),
                Vacancy.advantages.ilike(f"%{text}%"),
                Vacancy.offers.ilike(f"%{text}%"),
                # Старые поля для совместимости
                Vacancy.snippet_requirement.ilike(f"%{text}%"),
                Vacancy.snippet_responsibility.ilike(f"%{text}%")
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
    
    if schedule_id:
        query = query.filter(Vacancy.schedule_id == schedule_id)
    
    if education_id:
        query = query.filter(Vacancy.education_id == education_id)
    
    if specialization_id:
        query = query.filter(Vacancy.specialization_id == specialization_id)
    
    if industry_id:
        query = query.join(Employer).filter(Employer.industry_id == industry_id)
    
    if metro_id:
        query = query.join(vacancy_metro_by).filter(vacancy_metro_by.c.metro_id == metro_id)
    
    if salary_currency:
        query = query.filter(Vacancy.salary_currency == salary_currency)
    
    # Подсчет общего количества
    total = query.count()
    
    # Сортировка
    sort_column = getattr(Vacancy, sort_by, Vacancy.published_at)
    if sort_order == "asc":
        order_by = sort_column.asc()
    else:
        order_by = sort_column.desc()
    
    # Пагинация
    offset = (page - 1) * per_page
    vacancies = query.order_by(order_by).offset(offset).limit(per_page).all()
    
    # Формируем ответ с обработкой highlighttext
    items = []
    for vacancy in vacancies:
        # Загружаем метро для вакансии
        metro_stations = []
        if hasattr(vacancy, 'metro_stations'):
            metro_stations = [
                {"id": metro.id, "name": metro.name, "line_name": metro.line_name}
                for metro in vacancy.metro_stations
            ]
        
        # Загружаем навыки для вакансии
        skills = []
        skills_query = db.execute(
            sql_select(vacancy_skills.c.skill_name).where(vacancy_skills.c.vacancy_id == vacancy.id)
        )
        skills = [row.skill_name for row in skills_query]
        
        # Загружаем специализацию
        specialization_name = None
        if vacancy.specialization:
            specialization_name = vacancy.specialization.name
        
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
            # Полные описания для rabota.by
            description=process_highlighttext(vacancy.description),
            tasks=process_highlighttext(vacancy.tasks),
            requirements=process_highlighttext(vacancy.requirements),
            advantages=process_highlighttext(vacancy.advantages),
            offers=process_highlighttext(vacancy.offers),
            # Старые поля (для совместимости)
            snippet_requirement=process_highlighttext(vacancy.snippet_requirement),
            snippet_responsibility=process_highlighttext(vacancy.snippet_responsibility),
            schedule_name=vacancy.schedule_name,
            experience_name=vacancy.experience_name,
            employment_name=vacancy.employment_name,
            work_format_name=vacancy.work_format_name,
            education_name=vacancy.education_name,
            specialization_id=vacancy.specialization_id,
            specialization_name=specialization_name,
            metro_stations=metro_stations if metro_stations else None,
            skills=skills if skills else None,
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
    
    # Загружаем метро для вакансии
    metro_stations = []
    if hasattr(vacancy, 'metro_stations'):
        metro_stations = [
            {"id": metro.id, "name": metro.name, "line_name": metro.line_name}
            for metro in vacancy.metro_stations
        ]
    
    # Загружаем навыки для вакансии
    skills = []
    skills_query = db.execute(
        sql_select(vacancy_skills.c.skill_name).where(vacancy_skills.c.vacancy_id == vacancy.id)
    )
    skills = [row.skill_name for row in skills_query]
    
    # Загружаем специализацию
    specialization_name = None
    if vacancy.specialization:
        specialization_name = vacancy.specialization.name
    
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
        address_lat=float(vacancy.address_lat) if vacancy.address_lat else None,
        address_lng=float(vacancy.address_lng) if vacancy.address_lng else None,
        salary_from=vacancy.salary_from,
        salary_to=vacancy.salary_to,
        salary_currency=vacancy.salary_currency,
        salary_gross=vacancy.salary_gross,
        # Полные описания для rabota.by
        description=process_highlighttext(vacancy.description),
        tasks=process_highlighttext(vacancy.tasks),
        requirements=process_highlighttext(vacancy.requirements),
        advantages=process_highlighttext(vacancy.advantages),
        offers=process_highlighttext(vacancy.offers),
        # Старые поля (для совместимости)
        snippet_requirement=process_highlighttext(vacancy.snippet_requirement),
        snippet_responsibility=process_highlighttext(vacancy.snippet_responsibility),
        schedule_name=vacancy.schedule_name,
        experience_name=vacancy.experience_name,
        employment_name=vacancy.employment_name,
        work_format_name=vacancy.work_format_name,
        education_name=vacancy.education_name,
        specialization_id=vacancy.specialization_id,
        specialization_name=specialization_name,
        metro_stations=metro_stations if metro_stations else None,
        skills=skills if skills else None,
        published_at=vacancy.published_at,
        alternate_url=vacancy.alternate_url,
        archived=vacancy.archived
    )

