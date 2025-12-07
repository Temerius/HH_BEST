from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None


class SkillResponse(SkillBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserSkillCreate(BaseModel):
    skill_id: Optional[int] = None
    skill_name: Optional[str] = None
    skill_category: Optional[str] = None
    level: str = "intermediate"  # 'beginner', 'intermediate', 'advanced', 'expert'
    years_of_experience: Optional[int] = None


class UserSkillUpdate(BaseModel):
    level: Optional[str] = None
    years_of_experience: Optional[int] = None


class UserSkillResponse(BaseModel):
    skill_id: int
    skill_name: str
    skill_category: Optional[str] = None
    level: str
    years_of_experience: Optional[int] = None
    
    class Config:
        from_attributes = True

