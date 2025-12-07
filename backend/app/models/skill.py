from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = {"schema": "users"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), index=True)  # 'programming', 'design', 'management', etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

