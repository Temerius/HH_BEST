"""
API для работы со станциями метро
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.vacancy import MetroStationBy

router = APIRouter()


@router.get("", response_model=List[dict])
async def get_metro_stations(
    city_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Получение списка станций метро"""
    query = db.query(MetroStationBy)
    
    if city_id:
        query = query.filter(MetroStationBy.city_id == city_id)
    
    if search:
        query = query.filter(MetroStationBy.name.ilike(f"%{search}%"))
    
    stations = query.order_by(MetroStationBy.name).limit(100).all()
    
    return [
        {
            "id": station.id,
            "name": station.name,
            "line_id": station.line_id,
            "line_name": station.line_name,
            "city_id": station.city_id,
            "lat": float(station.lat) if station.lat else None,
            "lng": float(station.lng) if station.lng else None
        }
        for station in stations
    ]

