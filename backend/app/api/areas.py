"""
API для работы с областями/городами
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.vacancy import Area

router = APIRouter()


@router.get("", response_model=List[dict])
async def get_areas(
    parent_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Получение списка областей/городов"""
    query = db.query(Area)
    
    if parent_id:
        query = query.filter(Area.parent_id == parent_id)
    else:
        # По умолчанию показываем только регионы верхнего уровня (без parent_id)
        query = query.filter(Area.parent_id.is_(None))
    
    if search:
        query = query.filter(Area.name.ilike(f"%{search}%"))
    
    areas = query.order_by(Area.name).limit(100).all()
    
    return [
        {
            "id": area.id,
            "name": area.name,
            "parent_id": area.parent_id
        }
        for area in areas
    ]

