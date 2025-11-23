from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class ResumeBase(BaseModel):
    title: str
    position: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: str = "RUR"
    experience_years: Optional[int] = None
    about: Optional[str] = None
    education: Optional[str] = None
    work_experience: Optional[List[Dict[str, Any]]] = None
    skills_summary: Optional[str] = None
    languages: Optional[List[Dict[str, Any]]] = None
    is_primary: bool = False


class ResumeCreate(ResumeBase):
    pass


class ResumeUpdate(BaseModel):
    title: Optional[str] = None
    position: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: Optional[str] = None
    experience_years: Optional[int] = None
    about: Optional[str] = None
    education: Optional[str] = None
    work_experience: Optional[List[Dict[str, Any]]] = None
    skills_summary: Optional[str] = None
    languages: Optional[List[Dict[str, Any]]] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class ResumeResponse(ResumeBase):
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

