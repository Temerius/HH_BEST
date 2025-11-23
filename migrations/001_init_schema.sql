-- ============================================
-- Vacancy Matcher Database Schema
-- Version: 1.0
-- Date: 2025-10-26
-- ============================================

-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- СОЗДАНИЕ СХЕМ
-- ============================================

-- Схема для данных о вакансиях
CREATE SCHEMA IF NOT EXISTS vacancies;
COMMENT ON SCHEMA vacancies IS 'Схема для хранения данных о вакансиях с HH.ru';

-- Схема для данных пользователей (пока пустая, заполним позже)
CREATE SCHEMA IF NOT EXISTS users;
COMMENT ON SCHEMA users IS 'Схема для хранения резюме и данных пользователей';

-- ============================================
-- СПРАВОЧНИКИ (vacancies schema)
-- ============================================

-- Валюты
CREATE TABLE IF NOT EXISTS vacancies.currencies (
    code VARCHAR(3) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10)
);

COMMENT ON TABLE vacancies.currencies IS 'Справочник валют для зарплат';

-- Регионы/Города
CREATE TABLE IF NOT EXISTS vacancies.areas (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id VARCHAR(10),
    FOREIGN KEY (parent_id) REFERENCES vacancies.areas(id) ON DELETE SET NULL
);

COMMENT ON TABLE vacancies.areas IS 'Справочник регионов и городов из HH.ru';

CREATE INDEX IF NOT EXISTS idx_areas_name ON vacancies.areas(name);
CREATE INDEX IF NOT EXISTS idx_areas_parent ON vacancies.areas(parent_id);

-- Работодатели
CREATE TABLE IF NOT EXISTS vacancies.employers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    trusted BOOLEAN DEFAULT FALSE,
    accredited_it_employer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE vacancies.employers IS 'Справочник работодателей';

CREATE INDEX IF NOT EXISTS idx_employers_name ON vacancies.employers(name);
CREATE INDEX IF NOT EXISTS idx_employers_trusted ON vacancies.employers(trusted);

-- Профессиональные роли
CREATE TABLE IF NOT EXISTS vacancies.professional_roles (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

COMMENT ON TABLE vacancies.professional_roles IS 'Справочник профессиональных ролей';

CREATE INDEX IF NOT EXISTS idx_professional_roles_name ON vacancies.professional_roles(name);

-- Станции метро
CREATE TABLE IF NOT EXISTS vacancies.metro_stations (
    station_id VARCHAR(20) PRIMARY KEY,
    station_name VARCHAR(255) NOT NULL,
    line_id VARCHAR(10),
    line_name VARCHAR(255),
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    area_id VARCHAR(10),
    FOREIGN KEY (area_id) REFERENCES vacancies.areas(id) ON DELETE CASCADE
);

COMMENT ON TABLE vacancies.metro_stations IS 'Справочник станций метро';

CREATE INDEX IF NOT EXISTS idx_metro_station_name ON vacancies.metro_stations(station_name);
CREATE INDEX IF NOT EXISTS idx_metro_area ON vacancies.metro_stations(area_id);

-- ============================================
-- ОСНОВНАЯ ТАБЛИЦА ВАКАНСИЙ
-- ============================================

CREATE TABLE IF NOT EXISTS vacancies.vacancies (
    -- Основное
    id BIGINT PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    premium BOOLEAN DEFAULT FALSE,
    
    -- Работодатель
    employer_id INTEGER NOT NULL,
    
    -- Локация
    area_id VARCHAR(10) NOT NULL,
    address_city VARCHAR(255),
    address_street VARCHAR(500),
    address_building VARCHAR(50),
    address_raw VARCHAR(1000),
    address_lat DECIMAL(10, 8),
    address_lng DECIMAL(11, 8),
    
    -- Зарплата
    salary_from INTEGER,
    salary_to INTEGER,
    salary_currency VARCHAR(3),
    salary_gross BOOLEAN,
    
    -- Описание (для GPT)
    snippet_requirement TEXT,
    snippet_responsibility TEXT,
    description TEXT,
    
    -- Условия работы
    schedule_id VARCHAR(50),
    schedule_name VARCHAR(100),
    experience_id VARCHAR(50) NOT NULL,
    experience_name VARCHAR(100) NOT NULL,
    employment_id VARCHAR(50),
    employment_name VARCHAR(100),
    
    -- Формат работы
    work_format_id VARCHAR(20),
    work_format_name VARCHAR(100),
    
    -- Рабочее время
    working_hours_id VARCHAR(20),
    working_hours_name VARCHAR(100),
    work_schedule_id VARCHAR(30),
    work_schedule_name VARCHAR(100),
    night_shifts BOOLEAN DEFAULT FALSE,
    
    -- Требования к отклику
    has_test BOOLEAN DEFAULT FALSE,
    response_letter_required BOOLEAN DEFAULT FALSE,
    accept_incomplete_resumes BOOLEAN DEFAULT FALSE,
    internship BOOLEAN DEFAULT FALSE,
    accept_temporary BOOLEAN DEFAULT FALSE,
    
    -- Ссылки
    url VARCHAR(500),
    alternate_url VARCHAR(500),
    apply_alternate_url VARCHAR(500),
    
    -- Даты
    published_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    archived BOOLEAN DEFAULT FALSE,
    
    -- Служебные поля
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description_fetched BOOLEAN DEFAULT FALSE,
    
    -- Связи
    FOREIGN KEY (employer_id) REFERENCES vacancies.employers(id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES vacancies.areas(id) ON DELETE CASCADE,
    FOREIGN KEY (salary_currency) REFERENCES vacancies.currencies(code) ON DELETE SET NULL
);

COMMENT ON TABLE vacancies.vacancies IS 'Основная таблица вакансий с HH.ru';
COMMENT ON COLUMN vacancies.vacancies.snippet_requirement IS 'Краткое описание требований из API';
COMMENT ON COLUMN vacancies.vacancies.snippet_responsibility IS 'Краткое описание обязанностей из API';
COMMENT ON COLUMN vacancies.vacancies.description IS 'Полное описание вакансии (загружается отдельно)';
COMMENT ON COLUMN vacancies.vacancies.description_fetched IS 'Флаг загрузки полного описания';

-- Индексы для vacancies
CREATE INDEX IF NOT EXISTS idx_vacancies_employer ON vacancies.vacancies(employer_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_area ON vacancies.vacancies(area_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_published ON vacancies.vacancies(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_vacancies_archived ON vacancies.vacancies(archived) WHERE archived = FALSE;
CREATE INDEX IF NOT EXISTS idx_vacancies_experience ON vacancies.vacancies(experience_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_salary_from ON vacancies.vacancies(salary_from) WHERE salary_from IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vacancies_work_format ON vacancies.vacancies(work_format_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_currency ON vacancies.vacancies(salary_currency);
CREATE INDEX IF NOT EXISTS idx_vacancies_description_fetched ON vacancies.vacancies(description_fetched) WHERE description_fetched = FALSE;

-- Полнотекстовый поиск
CREATE INDEX IF NOT EXISTS idx_vacancies_fts ON vacancies.vacancies 
USING gin(to_tsvector('russian', 
    name || ' ' || 
    COALESCE(snippet_requirement, '') || ' ' || 
    COALESCE(snippet_responsibility, '') || ' ' || 
    COALESCE(description, '')
));

-- ============================================
-- СВЯЗИ many-to-many
-- ============================================

-- Профессиональные роли вакансий
CREATE TABLE IF NOT EXISTS vacancies.vacancy_roles (
    vacancy_id BIGINT,
    role_id INTEGER,
    PRIMARY KEY (vacancy_id, role_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES vacancies.professional_roles(id) ON DELETE CASCADE
);

COMMENT ON TABLE vacancies.vacancy_roles IS 'Связь вакансий с профессиональными ролями (many-to-many)';

CREATE INDEX IF NOT EXISTS idx_vacancy_roles_vacancy ON vacancies.vacancy_roles(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_roles_role ON vacancies.vacancy_roles(role_id);

-- Станции метро рядом с вакансией
CREATE TABLE IF NOT EXISTS vacancies.vacancy_metro (
    vacancy_id BIGINT,
    station_id VARCHAR(20),
    PRIMARY KEY (vacancy_id, station_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES vacancies.metro_stations(station_id) ON DELETE CASCADE
);

COMMENT ON TABLE vacancies.vacancy_metro IS 'Связь вакансий со станциями метро (many-to-many)';

CREATE INDEX IF NOT EXISTS idx_vacancy_metro_vacancy ON vacancies.vacancy_metro(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_metro_station ON vacancies.vacancy_metro(station_id);

-- ============================================
-- КУРСЫ ВАЛЮТ
-- ============================================

CREATE TABLE IF NOT EXISTS vacancies.exchange_rates (
    id SERIAL PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(12, 6) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (from_currency) REFERENCES vacancies.currencies(code) ON DELETE CASCADE,
    FOREIGN KEY (to_currency) REFERENCES vacancies.currencies(code) ON DELETE CASCADE,
    UNIQUE(from_currency, to_currency, date)
);

COMMENT ON TABLE vacancies.exchange_rates IS 'Курсы валют для конвертации зарплат';

CREATE INDEX IF NOT EXISTS idx_exchange_rates_date ON vacancies.exchange_rates(date DESC);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_pair ON vacancies.exchange_rates(from_currency, to_currency);

-- ============================================
-- ТРИГГЕРЫ
-- ============================================

-- Автообновление updated_at для employers
CREATE OR REPLACE FUNCTION vacancies.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_employers_updated_at
    BEFORE UPDATE ON vacancies.employers
    FOR EACH ROW
    EXECUTE FUNCTION vacancies.update_updated_at_column();

CREATE TRIGGER update_vacancies_updated_at
    BEFORE UPDATE ON vacancies.vacancies
    FOR EACH ROW
    EXECUTE FUNCTION vacancies.update_updated_at_column();

-- ============================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ============================================

-- Валюты
INSERT INTO vacancies.currencies (code, name, symbol) VALUES
('RUR', 'Российский рубль', '₽'),
('USD', 'Доллар США', '$'),
('EUR', 'Евро', '€'),
('KZT', 'Казахстанский тенге', '₸'),
('BYR', 'Белорусский рубль', 'Br'),
('AZN', 'Азербайджанский манат', '₼'),
('UZS', 'Узбекский сум', 'сўм'),
('GEL', 'Грузинский лари', '₾')
ON CONFLICT (code) DO NOTHING;

-- ============================================
-- ПРЕДСТАВЛЕНИЯ ДЛЯ УДОБСТВА
-- ============================================

-- Активные вакансии с полной информацией
CREATE OR REPLACE VIEW vacancies.active_vacancies AS
SELECT 
    v.*,
    e.name as employer_name,
    e.trusted as employer_trusted,
    a.name as area_name,
    array_agg(DISTINCT pr.name) as professional_roles,
    array_agg(DISTINCT ms.station_name) as metro_stations
FROM vacancies.vacancies v
LEFT JOIN vacancies.employers e ON v.employer_id = e.id
LEFT JOIN vacancies.areas a ON v.area_id = a.id
LEFT JOIN vacancies.vacancy_roles vr ON v.id = vr.vacancy_id
LEFT JOIN vacancies.professional_roles pr ON vr.role_id = pr.id
LEFT JOIN vacancies.vacancy_metro vm ON v.id = vm.vacancy_id
LEFT JOIN vacancies.metro_stations ms ON vm.station_id = ms.station_id
WHERE v.archived = FALSE
GROUP BY v.id, e.name, e.trusted, a.name;

COMMENT ON VIEW vacancies.active_vacancies IS 'Представление активных вакансий с дополнительной информацией';

-- ============================================
-- СТАТИСТИКА
-- ============================================

-- Функция для получения статистики по схеме vacancies
CREATE OR REPLACE FUNCTION vacancies.get_stats()
RETURNS TABLE (
    table_name TEXT,
    row_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'vacancies'::TEXT, COUNT(*)::BIGINT FROM vacancies.vacancies
    UNION ALL
    SELECT 'employers'::TEXT, COUNT(*)::BIGINT FROM vacancies.employers
    UNION ALL
    SELECT 'areas'::TEXT, COUNT(*)::BIGINT FROM vacancies.areas
    UNION ALL
    SELECT 'professional_roles'::TEXT, COUNT(*)::BIGINT FROM vacancies.professional_roles
    UNION ALL
    SELECT 'metro_stations'::TEXT, COUNT(*)::BIGINT FROM vacancies.metro_stations
    UNION ALL
    SELECT 'currencies'::TEXT, COUNT(*)::BIGINT FROM vacancies.currencies;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- НАСТРОЙКА SEARCH PATH
-- ============================================

-- По умолчанию ищем сначала в vacancies, потом в public
ALTER DATABASE hh_data SET search_path TO vacancies, public;

-- ============================================
-- ЗАВЕРШЕНИЕ
-- ============================================

-- Вывод информации о созданных объектах
DO $$
DECLARE
    schemas_count INTEGER;
    tables_count INTEGER;
    indexes_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO schemas_count FROM information_schema.schemata 
    WHERE schema_name IN ('vacancies', 'users');
    
    SELECT COUNT(*) INTO tables_count FROM information_schema.tables 
    WHERE table_schema = 'vacancies' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO indexes_count FROM pg_indexes 
    WHERE schemaname = 'vacancies';
    
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Schemas created: %', schemas_count;
    RAISE NOTICE 'Tables created in vacancies schema: %', tables_count;
    RAISE NOTICE 'Indexes created: %', indexes_count;
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Schema "users" is ready for future migrations';
    RAISE NOTICE '============================================';
END $$; 