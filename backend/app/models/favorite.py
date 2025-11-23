from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class FavoriteVacancy(Base):
    __tablename__ = "favorite_vacancies"
    __table_args__ = {"schema": "users"}
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), primary_key=True, index=True)
    vacancy_id = Column(BigInteger, ForeignKey("vacancies.vacancies.id", ondelete="CASCADE"), primary_key=True, index=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

