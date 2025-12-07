from sqlalchemy import Column, BigInteger, String, Boolean, Integer, Text, DateTime, ForeignKey, Numeric, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Industry(Base):
    __tablename__ = "industries"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("vacancies.industries.id", ondelete="SET NULL"), index=True)
    
    # Relationships
    parent = relationship("Industry", remote_side=[id])


class Employer(Base):
    __tablename__ = "employers"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, index=True)
    trusted = Column(Boolean, default=False, index=True)
    accredited_it_employer = Column(Boolean, default=False)
    
    # Новые поля для rabota.by
    industry_id = Column(Integer, ForeignKey("vacancies.industries.id", ondelete="SET NULL"), index=True)
    industry_name = Column(String(255))
    company_description = Column(Text)
    company_size = Column(String(50))
    company_website = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    industry = relationship("Industry", foreign_keys=[industry_id])


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


class Specialization(Base):
    __tablename__ = "specializations"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("vacancies.specializations.id", ondelete="SET NULL"), index=True)
    
    # Relationships
    parent = relationship("Specialization", remote_side=[id])


class MetroStationBy(Base):
    __tablename__ = "metro_stations_by"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    line_id = Column(Integer)
    line_name = Column(String(255))
    city_id = Column(String(10), ForeignKey("vacancies.areas.id", ondelete="CASCADE"), index=True)
    lat = Column(Numeric(10, 8))
    lng = Column(Numeric(11, 8))
    
    # Relationships
    city = relationship("Area", foreign_keys=[city_id])


# Связующие таблицы для many-to-many
vacancy_metro_by = Table(
    'vacancy_metro_by',
    Base.metadata,
    Column('vacancy_id', BigInteger, ForeignKey('vacancies.vacancies.id', ondelete='CASCADE'), primary_key=True),
    Column('metro_id', Integer, ForeignKey('vacancies.metro_stations_by.id', ondelete='CASCADE'), primary_key=True),
    schema='vacancies'
)

vacancy_specializations = Table(
    'vacancy_specializations',
    Base.metadata,
    Column('vacancy_id', BigInteger, ForeignKey('vacancies.vacancies.id', ondelete='CASCADE'), primary_key=True),
    Column('specialization_id', Integer, ForeignKey('vacancies.specializations.id', ondelete='CASCADE'), primary_key=True),
    schema='vacancies'
)

vacancy_skills = Table(
    'vacancy_skills',
    Base.metadata,
    Column('vacancy_id', BigInteger, ForeignKey('vacancies.vacancies.id', ondelete='CASCADE'), primary_key=True),
    Column('skill_name', String(255), primary_key=True),
    schema='vacancies'
)


class Vacancy(Base):
    __tablename__ = "vacancies"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(500), nullable=False)
    premium = Column(Boolean, default=False)
    employer_id = Column(Integer, ForeignKey("vacancies.employers.id", ondelete="CASCADE"), nullable=False, index=True)
    area_id = Column(String(10), ForeignKey("vacancies.areas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Адрес и координаты (для карты)
    address_city = Column(String(255))
    address_street = Column(String(500))
    address_building = Column(String(50))
    address_raw = Column(String(1000))
    address_lat = Column(Numeric(10, 8), index=True)
    address_lng = Column(Numeric(11, 8), index=True)
    coordinates_accuracy = Column(String(50))
    
    # Зарплата (уровень дохода и валюта)
    salary_from = Column(Integer, index=True)
    salary_to = Column(Integer)
    salary_currency = Column(String(3), index=True)  # BYN, USD, EUR, RUR
    salary_gross = Column(Boolean)
    
    # Полные описания для rabota.by
    description = Column(Text)  # Общее описание
    tasks = Column(Text)  # Задачи
    requirements = Column(Text)  # Мы ожидаем (полные требования)
    advantages = Column(Text)  # Будет плюсом
    offers = Column(Text)  # Мы предлагаем
    
    # Старые поля (оставляем для совместимости, но не используем)
    snippet_requirement = Column(Text)
    snippet_responsibility = Column(Text)
    
    # Условия работы (для фильтров)
    schedule_id = Column(String(50), index=True)  # График работы
    schedule_name = Column(String(100))
    experience_id = Column(String(50), nullable=False, index=True)  # Опыт работы
    experience_name = Column(String(100), nullable=False)
    employment_id = Column(String(50), index=True)  # Тип занятости
    employment_name = Column(String(100))
    work_format_id = Column(String(20), index=True)  # Формат работы
    work_format_name = Column(String(100))
    education_id = Column(String(50), index=True)  # Образование
    education_name = Column(String(255))
    
    # Специализация
    specialization_id = Column(Integer, ForeignKey("vacancies.specializations.id", ondelete="SET NULL"), index=True)
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
    specialization = relationship("Specialization", foreign_keys=[specialization_id])
    metro_stations = relationship("MetroStationBy", secondary=vacancy_metro_by, backref="vacancies")
    specializations = relationship("Specialization", secondary=vacancy_specializations, backref="vacancies")

