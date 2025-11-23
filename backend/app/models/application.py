from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = {"schema": "users"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id", ondelete="CASCADE"), nullable=False, index=True)
    vacancy_id = Column(BigInteger, ForeignKey("vacancies.vacancies.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("users.resumes.id", ondelete="SET NULL"))
    cover_letter = Column(Text)
    status = Column(String(20), default="pending", index=True)  # pending, viewed, rejected, invited
    ai_generated_cover_letter = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

