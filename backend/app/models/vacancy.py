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
    url = Column(String(500))
    trusted = Column(Boolean, default=False, index=True)
    logo_url = Column(String(500))
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


class VacancySkill(Base):
    __tablename__ = "skills"
    __table_args__ = {"schema": "vacancies"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255))
    category = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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
    Column('skill_id', Integer, ForeignKey('vacancies.skills.id', ondelete='CASCADE'), primary_key=True),
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
    
    # Зарплата (уровень дохода и валюта)
    salary_from = Column(Integer, index=True)
    salary_to = Column(Integer)
    salary_currency = Column(String(3), index=True)  # BYN, USD, EUR, RUR
    salary_gross = Column(Boolean)
    salary_description = Column(String(255))  # Описание зарплаты
    
    # Полные описания для rabota.by
    description_html = Column(Text)  # HTML описание
    description_text = Column(Text)  # Текстовое описание
    
    # Условия работы (для фильтров)
    schedule_id = Column(String(50), index=True)  # График работы
    schedule_name = Column(String(100))
    experience_id = Column(String(50), nullable=False, index=True)  # Опыт работы
    experience_name = Column(String(100), nullable=False)
    employment_id = Column(String(50), index=True)  # Тип занятости
    employment_name = Column(String(100))
    
    # Требования
    response_letter_required = Column(Boolean, default=False)
    accept_handicapped = Column(Boolean, default=False)
    accept_kids = Column(Boolean, default=False)
    
    # Ссылки
    url = Column(String(500))
    
    # Даты
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    archived = Column(Boolean, default=False, index=True)
    
    # Служебные
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employer = relationship("Employer")
    area = relationship("Area")
    metro_stations = relationship("MetroStationBy", secondary=vacancy_metro_by, backref="vacancies")
    specializations = relationship("Specialization", secondary=vacancy_specializations, backref="vacancies")
    skills_rel = relationship("VacancySkill", secondary=vacancy_skills, backref="vacancies")

