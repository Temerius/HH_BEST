from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select, case, Numeric, exists
from typing import Optional, List
from app.core.database import get_db
from app.models.vacancy import Vacancy, Employer, Area, Industry, Specialization, MetroStationBy, VacancySkill, vacancy_metro_by, vacancy_specializations, vacancy_skills
from app.schemas.vacancy import VacancyResponse, VacancyListResponse, VacancyFilters
from app.utils.text_processing import process_highlighttext

router = APIRouter()


@router.get("", response_model=VacancyListResponse)
async def get_vacancies(
    text: Optional[str] = Query(None),
    area_id: Optional[str] = Query(None),
    metro_id: Optional[List[int]] = Query(default=None),
    salary_from: Optional[int] = Query(None),
    salary_to: Optional[int] = Query(None),
    salary_currency: Optional[str] = Query(None),
    experience_id: Optional[str] = Query(None),
    employment_id: Optional[str] = Query(None),
    schedule_id: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("published_at", regex="^(published_at|salary_from)$"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получение списка вакансий с фильтрацией"""
    # Отладочное логирование всех параметров
    import logging
    logger = logging.getLogger(__name__)
    print(f"📥 Received params: metro_id={metro_id}, type={type(metro_id)}, area_id={area_id}, text={text}")
    logger.info(f"📥 Received params: metro_id={metro_id}, type={type(metro_id)}, area_id={area_id}, text={text}")
    
    # Начинаем с базового запроса
    query = db.query(Vacancy).join(Employer).join(Area).filter(Vacancy.archived == False)
    
    # Фильтры
    if text:
        query = query.filter(
            or_(
                Vacancy.name.ilike(f"%{text}%"),
                Vacancy.description_html.ilike(f"%{text}%"),
                Vacancy.description_text.ilike(f"%{text}%")
            )
        )
    
    if area_id:
        query = query.filter(Vacancy.area_id == area_id)
    
    # Фильтр по зарплате - фильтруем только ОТ (по salary_from)
    # Вакансии с NULL зарплатой не исключаются из результатов
    if salary_from:
        if salary_currency:
            # Фильтруем только по указанной валюте, по полю salary_from
            query = query.filter(
                and_(
                    Vacancy.salary_currency == salary_currency,
                    Vacancy.salary_from.isnot(None),
                    Vacancy.salary_from >= salary_from
                )
            )
        else:
            # Без указания валюты - фильтруем по любой валюте, по полю salary_from
            query = query.filter(
                and_(
                    Vacancy.salary_from.isnot(None),
                    Vacancy.salary_from >= salary_from
                )
            )
    
    if salary_currency and not salary_from:
        # Если указана только валюта без суммы
        query = query.filter(Vacancy.salary_currency == salary_currency)
    
    if experience_id:
        query = query.filter(Vacancy.experience_id == experience_id)
    
    if employment_id:
        query = query.filter(Vacancy.employment_id == employment_id)
    
    if schedule_id:
        query = query.filter(Vacancy.schedule_id == schedule_id)
    
    if metro_id:
        # Поддержка множественного выбора метро
        # Используем join как в примере SQL запроса пользователя:
        # SELECT * FROM vacancies v
        # JOIN vacancy_metro_by vmb ON v.id = vmb.vacancy_id
        # WHERE vmb.metro_id IN (...)
        metro_ids = metro_id if isinstance(metro_id, list) else [metro_id]
        print(f"🔍 metro_id received: {metro_id}, converted to: {metro_ids}, type: {type(metro_ids)}, len: {len(metro_ids) if metro_ids else 0}")
        logger.info(f"🔍 metro_id received: {metro_id}, converted to: {metro_ids}, type: {type(metro_ids)}, len: {len(metro_ids) if metro_ids else 0}")
        
        if metro_ids and len(metro_ids) > 0:
            print(f"✅ Applying metro filter with metro_ids: {metro_ids}")
            # Делаем join с vacancy_metro_by и фильтруем по metro_id
            query = query.join(
                vacancy_metro_by,
                Vacancy.id == vacancy_metro_by.c.vacancy_id
            ).filter(
                vacancy_metro_by.c.metro_id.in_(metro_ids)
            ).distinct()
            
            logger.info(f"✅ Applied metro filter using join, filtering by metro_ids: {metro_ids}")
        else:
            print(f"⚠️ metro_id is empty or invalid: {metro_id}")
            logger.warning(f"⚠️ metro_id is empty or invalid: {metro_id}")
    else:
        print("ℹ️ No metro_id filter provided")
        logger.info("ℹ️ No metro_id filter provided")
    
    # Подсчет общего количества
    total = query.count()
    
    # Сортировка
    if sort_by == 'salary_from':
        # Сортировка по зарплате - по среднему значению (salary_from + salary_to) / 2
        # Если salary_to NULL, то среднее = salary_from
        # Если оба NULL, то считаем 0 (в конце)
        # Используем CASE для правильного расчета среднего
        avg_salary = case(
            (
                and_(Vacancy.salary_from.isnot(None), Vacancy.salary_to.isnot(None)),
                (func.cast(Vacancy.salary_from, Numeric) + func.cast(Vacancy.salary_to, Numeric)) / 2.0
            ),
            (
                Vacancy.salary_from.isnot(None),
                func.cast(Vacancy.salary_from, Numeric)
            ),
            else_=func.cast(0, Numeric)
        )
        if sort_order == "asc":
            # NULL идут в конец (0)
            order_by = avg_salary.asc()
        else:
            # NULL идут в конец (0)
            order_by = avg_salary.desc()
    else:
        # Сортировка по дате (published_at)
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
        if hasattr(vacancy, 'skills_rel'):
            skills = [skill.name for skill in vacancy.skills_rel]
        else:
            # Fallback: прямой запрос через join
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
    else:
        # Fallback: прямой запрос через join
        metro_query = db.query(MetroStationBy).join(vacancy_metro_by).filter(
            vacancy_metro_by.c.vacancy_id == vacancy.id
        ).all()
        metro_stations = [
            {"id": metro.id, "name": metro.name, "line_name": metro.line_name}
            for metro in metro_query
        ]
    
    # Загружаем навыки для вакансии
    skills = []
    if hasattr(vacancy, 'skills_rel'):
        skills = [skill.name for skill in vacancy.skills_rel]
    else:
        # Fallback: прямой запрос через join
        skills_query = db.query(VacancySkill).join(vacancy_skills).filter(
            vacancy_skills.c.vacancy_id == vacancy.id
        ).all()
        skills = [skill.name for skill in skills_query]
    
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
    )

