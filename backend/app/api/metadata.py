"""
API для работы с метаданными (навыки, направления) из Redis
"""
from fastapi import APIRouter
from typing import List
import json
from app.core.redis_client import redis_client

router = APIRouter()


@router.get("/skills", response_model=List[dict])
async def get_skills():
    """Получение списка всех навыков из Redis"""
    skills_json = redis_client.get("metadata:skills")
    if skills_json:
        return json.loads(skills_json)
    return []


@router.get("/specializations", response_model=List[str])
async def get_specializations():
    """Получение списка направлений разработки из Redis"""
    specializations_json = redis_client.get("metadata:specializations")
    if specializations_json:
        return json.loads(specializations_json)
    return []


@router.get("/skill-categories", response_model=List[str])
async def get_skill_categories():
    """Получение списка категорий навыков из Redis"""
    categories_json = redis_client.get("metadata:skill_categories")
    if categories_json:
        return json.loads(categories_json)
    return []

