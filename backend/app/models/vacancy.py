from sqlalchemy import Column, BigInteger, String, Boolean, Integer, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Employer(Base):
    __tablename__ = "employers"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, index=True)
    trusted = Column(Boolean, default=False, index=True)
    accredited_it_employer = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Area(Base):
    __tablename__ = "areas"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(String(10), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    parent_id = Column(String(10), ForeignKey("vacancies.areas.id", ondelete="SET NULL"), index=True)


class ProfessionalRole(Base):
    __tablename__ = "professional_roles"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)


class Vacancy(Base):
    __tablename__ = "vacancies"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(500), nullable=False)
    premium = Column(Boolean, default=False)
    employer_id = Column(Integer, ForeignKey("vacancies.employers.id", ondelete="CASCADE"), nullable=False, index=True)
    area_id = Column(String(10), ForeignKey("vacancies.areas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Адрес
    address_city = Column(String(255))
    address_street = Column(String(500))
    address_building = Column(String(50))
    address_raw = Column(String(1000))
    address_lat = Column(Numeric(10, 8))
    address_lng = Column(Numeric(11, 8))
    
    # Зарплата
    salary_from = Column(Integer, index=True)
    salary_to = Column(Integer)
    salary_currency = Column(String(3))
    salary_gross = Column(Boolean)
    
    # Описание
    snippet_requirement = Column(Text)
    snippet_responsibility = Column(Text)
    description = Column(Text)
    
    # Условия работы
    schedule_id = Column(String(50))
    schedule_name = Column(String(100))
    experience_id = Column(String(50), nullable=False)
    experience_name = Column(String(100), nullable=False)
    employment_id = Column(String(50))
    employment_name = Column(String(100))
    work_format_id = Column(String(20), index=True)
    work_format_name = Column(String(100))
    working_hours_id = Column(String(20))
    working_hours_name = Column(String(100))
    work_schedule_id = Column(String(30))
    work_schedule_name = Column(String(100))
    night_shifts = Column(Boolean, default=False)
    
    # Требования
    has_test = Column(Boolean, default=False)
    response_letter_required = Column(Boolean, default=False)
    accept_incomplete_resumes = Column(Boolean, default=False)
    internship = Column(Boolean, default=False)
    accept_temporary = Column(Boolean, default=False)
    
    # Ссылки
    url = Column(String(500))
    alternate_url = Column(String(500))
    apply_alternate_url = Column(String(500))
    
    # Даты
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    archived = Column(Boolean, default=False, index=True)
    
    # Служебные
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    description_fetched = Column(Boolean, default=False, index=True)
    
    # Relationships
    employer = relationship("Employer")
    area = relationship("Area")

