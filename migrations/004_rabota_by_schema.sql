-- ============================================
-- Миграция для перехода на rabota.by API
-- Версия: 4.0
-- Дата: 2025-11-27
-- ============================================

-- Добавляем новые поля для rabota.by структуры

-- Обновляем таблицу работодателей
ALTER TABLE vacancies.employers 
ADD COLUMN IF NOT EXISTS industry_id INTEGER,
ADD COLUMN IF NOT EXISTS industry_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS company_description TEXT,
ADD COLUMN IF NOT EXISTS company_size VARCHAR(50),
ADD COLUMN IF NOT EXISTS company_website VARCHAR(500);

COMMENT ON COLUMN vacancies.employers.industry_id IS 'ID отрасли компании';
COMMENT ON COLUMN vacancies.employers.industry_name IS 'Название отрасли компании';
COMMENT ON COLUMN vacancies.employers.company_description IS 'Описание компании';
COMMENT ON COLUMN vacancies.employers.company_size IS 'Размер компании (малая, средняя, крупная)';
COMMENT ON COLUMN vacancies.employers.company_website IS 'Сайт компании';

-- Создаем таблицу для отраслей
CREATE TABLE IF NOT EXISTS vacancies.industries(
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES vacancies.industries(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_industries_name ON vacancies.industries(name);
CREATE INDEX IF NOT EXISTS idx_industries_parent ON vacancies.industries(parent_id);

COMMENT ON TABLE vacancies.industries IS 'Справочник отраслей компаний';

-- Создаем таблицу для метро (для РБ)
CREATE TABLE IF NOT EXISTS vacancies.metro_stations_by (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    line_id INTEGER,
    line_name VARCHAR(255),
    city_id VARCHAR(10),
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    FOREIGN KEY (city_id) REFERENCES vacancies.areas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metro_stations_by_name ON vacancies.metro_stations_by(name);
CREATE INDEX IF NOT EXISTS idx_metro_stations_by_city ON vacancies.metro_stations_by(city_id);

COMMENT ON TABLE vacancies.metro_stations_by IS 'Справочник станций метро для РБ';

-- Создаем таблицу для связи вакансий и метро
CREATE TABLE IF NOT EXISTS vacancies.vacancy_metro_by (
    vacancy_id BIGINT NOT NULL,
    metro_id INTEGER NOT NULL,
    PRIMARY KEY (vacancy_id, metro_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY (metro_id) REFERENCES vacancies.metro_stations_by(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vacancy_metro_by_vacancy ON vacancies.vacancy_metro_by(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_metro_by_metro ON vacancies.vacancy_metro_by(metro_id);

-- Создаем таблицу для специализаций (профессиональных ролей)
CREATE TABLE IF NOT EXISTS vacancies.specializations (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES vacancies.specializations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_specializations_name ON vacancies.specializations(name);
CREATE INDEX IF NOT EXISTS idx_specializations_parent ON vacancies.specializations(parent_id);

COMMENT ON TABLE vacancies.specializations IS 'Справочник специализаций';

-- Создаем таблицу для связи вакансий и специализаций
CREATE TABLE IF NOT EXISTS vacancies.vacancy_specializations (
    vacancy_id BIGINT NOT NULL,
    specialization_id INTEGER NOT NULL,
    PRIMARY KEY (vacancy_id, specialization_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY (specialization_id) REFERENCES vacancies.specializations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vacancy_specializations_vacancy ON vacancies.vacancy_specializations(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_specializations_spec ON vacancies.vacancy_specializations(specialization_id);

-- Создаем таблицу для ключевых навыков вакансии
CREATE TABLE IF NOT EXISTS vacancies.vacancy_skills (
    vacancy_id BIGINT NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (vacancy_id, skill_name),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vacancy_skills_vacancy ON vacancies.vacancy_skills(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_skills_name ON vacancies.vacancy_skills(skill_name);

COMMENT ON TABLE vacancies.vacancy_skills IS 'Ключевые навыки для вакансий';

ALTER TABLE vacancies.vacancies
    ADD COLUMN IF NOT EXISTS description_html TEXT,
    ADD COLUMN IF NOT EXISTS description_text TEXT,
    ADD COLUMN IF NOT EXISTS tasks TEXT,
    ADD COLUMN IF NOT EXISTS requirements TEXT,
    ADD COLUMN IF NOT EXISTS advantages TEXT,
    ADD COLUMN IF NOT EXISTS offers TEXT,
    ADD COLUMN IF NOT EXISTS education_id VARCHAR(50),
    ADD COLUMN IF NOT EXISTS education_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS specialization_id INTEGER,
    ADD COLUMN IF NOT EXISTS coordinates_accuracy VARCHAR(50);

-- Создаем индексы для новых полей
CREATE INDEX IF NOT EXISTS idx_vacancies_education ON vacancies.vacancies(education_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_specialization ON vacancies.vacancies(specialization_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_coordinates ON vacancies.vacancies(address_lat, address_lng) WHERE address_lat IS NOT NULL AND address_lng IS NOT NULL;

-- Обновляем комментарии к существующим полям
COMMENT ON COLUMN vacancies.vacancies.salary_from IS 'Уровень дохода от';
COMMENT ON COLUMN vacancies.vacancies.salary_to IS 'Уровень дохода до';
COMMENT ON COLUMN vacancies.vacancies.salary_currency IS 'Валюта (BYN, USD, EUR, RUR)';
COMMENT ON COLUMN vacancies.vacancies.area_id IS 'Регион РБ';
COMMENT ON COLUMN vacancies.vacancies.experience_id IS 'Опыт работы';
COMMENT ON COLUMN vacancies.vacancies.employment_id IS 'Тип занятости';
COMMENT ON COLUMN vacancies.vacancies.schedule_id IS 'График работы';
COMMENT ON COLUMN vacancies.vacancies.work_format_id IS 'Формат работы (удаленно, офис, гибрид)';

-- Удаляем старые поля, которые не нужны для rabota.by (опционально, можно оставить для совместимости)
-- ALTER TABLE vacancies.vacancies DROP COLUMN IF EXISTS snippet_requirement;
-- ALTER TABLE vacancies.vacancies DROP COLUMN IF EXISTS snippet_responsibility;

-- Обновляем таблицу areas для поддержки РБ регионов
-- (структура остается той же, но данные будут из rabota.by)


