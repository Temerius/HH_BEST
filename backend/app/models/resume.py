from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = {"schema": "users"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    position = Column(String(255))  # Желаемая должность
    salary_from = Column(Integer)
    salary_to = Column(Integer)
    salary_currency = Column(String(3), default="RUR")
    experience_years = Column(Integer)
    about = Column(Text)
    education = Column(Text)
    work_experience = Column(JSONB)
    skills_summary = Column(Text)
    languages = Column(JSONB)
    is_primary = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="resumes")


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = {"schema": "users"}
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("users.skills.id", ondelete="CASCADE"), primary_key=True)
    level = Column(String(20), default="intermediate")
    years_of_experience = Column(Integer)

