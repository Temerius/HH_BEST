from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class VacancyBase(BaseModel):
    name: str
    employer_id: int
    area_id: str


class VacancyResponse(BaseModel):
    id: int
    name: str
    premium: bool
    employer_id: int
    employer_name: Optional[str] = None
    area_id: str
    area_name: Optional[str] = None
    address_city: Optional[str] = None
    address_raw: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_gross: Optional[bool] = None
    snippet_requirement: Optional[str] = None
    snippet_responsibility: Optional[str] = None
    description: Optional[str] = None
    schedule_name: Optional[str] = None
    experience_name: Optional[str] = None
    employment_name: Optional[str] = None
    work_format_name: Optional[str] = None
    published_at: datetime
    alternate_url: Optional[str] = None
    archived: bool
    
    class Config:
        from_attributes = True


class VacancyListResponse(BaseModel):
    items: List[VacancyResponse]
    total: int
    page: int
    per_page: int


class VacancyFilters(BaseModel):
    text: Optional[str] = None
    area_id: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    experience_id: Optional[str] = None
    employment_id: Optional[str] = None
    work_format_id: Optional[str] = None
    professional_role_id: Optional[int] = None
    page: int = 1
    per_page: int = 20

