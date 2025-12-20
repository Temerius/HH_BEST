from app.models.user import User
from app.models.resume import Resume, UserSkill, ResumeText
from app.models.skill import Skill
from app.models.vacancy import (
    Vacancy, Employer, Area, ProfessionalRole, Industry, 
    Specialization, MetroStationBy, VacancySkill
)
from app.models.favorite import FavoriteVacancy
from app.models.application import Application

__all__ = [
    "User",
    "Resume",
    "UserSkill",
    "ResumeText",
    "Skill",
    "Vacancy",
    "Employer",
    "Area",
    "ProfessionalRole",
    "Industry",
    "Specialization",
    "MetroStationBy",
    "VacancySkill",
    "FavoriteVacancy",
    "Application",
]

