from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.skill import Skill
from app.models.resume import UserSkill
from app.schemas.skill import (
    SkillResponse, 
    UserSkillCreate, 
    UserSkillUpdate, 
    UserSkillResponse
)

router = APIRouter()


@router.get("", response_model=List[SkillResponse])
async def get_skills(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получение списка всех навыков с фильтрацией"""
    query = db.query(Skill)
    
    if category:
        query = query.filter(Skill.category == category)
    
    if search:
        query = query.filter(Skill.name.ilike(f"%{search}%"))
    
    skills = query.order_by(Skill.name).all()
    return skills


@router.get("/categories", response_model=List[str])
async def get_skill_categories(db: Session = Depends(get_db)):
    """Получение списка категорий навыков"""
    categories = db.query(Skill.category).distinct().filter(
        Skill.category.isnot(None)
    ).all()
    return [cat[0] for cat in categories if cat[0]]


@router.get("/my", response_model=List[UserSkillResponse])
async def get_my_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение навыков текущего пользователя"""
    user_skills = db.query(UserSkill, Skill).join(
        Skill, UserSkill.skill_id == Skill.id
    ).filter(
        UserSkill.user_id == current_user.id
    ).all()
    
    return [
        UserSkillResponse(
            skill_id=skill.id,
            skill_name=skill.name,
            skill_category=skill.category,
            level=user_skill.level,
            years_of_experience=user_skill.years_of_experience
        )
        for user_skill, skill in user_skills
    ]


@router.post("/my", response_model=UserSkillResponse, status_code=status.HTTP_201_CREATED)
async def add_skill(
    skill_data: UserSkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавление навыка пользователю по ID или имени"""
    # Если передан skill_id, используем его
    if skill_data.skill_id:
        skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found"
            )
        skill_id = skill.id
        skill_name = skill.name
        skill_category = skill.category
    else:
        # Иначе ищем или создаем навык по имени
        skill = db.query(Skill).filter(Skill.name == skill_data.skill_name).first()
        if not skill:
            # Создаем новый навык в БД
            skill = Skill(
                name=skill_data.skill_name,
                category=skill_data.skill_category
            )
            db.add(skill)
            db.commit()
            db.refresh(skill)
        skill_id = skill.id
        skill_name = skill.name
        skill_category = skill.category
    
    # Проверяем, не добавлен ли уже этот навык
    existing = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already added"
        )
    
    user_skill = UserSkill(
        user_id=current_user.id,
        skill_id=skill_id,
        level=skill_data.level,
        years_of_experience=skill_data.years_of_experience
    )
    
    db.add(user_skill)
    db.commit()
    db.refresh(user_skill)
    
    return UserSkillResponse(
        skill_id=skill.id,
        skill_name=skill_name,
        skill_category=skill_category,
        level=user_skill.level,
        years_of_experience=user_skill.years_of_experience
    )


@router.put("/my/{skill_id}", response_model=UserSkillResponse)
async def update_skill(
    skill_id: int,
    skill_update: UserSkillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление навыка пользователя"""
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_id
    ).first()
    
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User skill not found"
        )
    
    update_data = skill_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_skill, field, value)
    
    db.commit()
    db.refresh(user_skill)
    
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    return UserSkillResponse(
        skill_id=skill.id,
        skill_name=skill.name,
        skill_category=skill.category,
        level=user_skill.level,
        years_of_experience=user_skill.years_of_experience
    )


@router.delete("/my/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление навыка у пользователя"""
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_id
    ).first()
    
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User skill not found"
        )
    
    db.delete(user_skill)
    db.commit()
    
    return None

