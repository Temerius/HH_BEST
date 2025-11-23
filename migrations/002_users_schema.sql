-- ============================================
-- Users Schema Migration
-- Version: 2.0
-- Date: 2025-10-27
-- ============================================

-- ============================================
-- ПОЛЬЗОВАТЕЛИ
-- ============================================

CREATE TABLE IF NOT EXISTS users.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    birth_date DATE,
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.users IS 'Пользователи платформы';
COMMENT ON COLUMN users.users.password_hash IS 'Хеш пароля (bcrypt)';

CREATE INDEX IF NOT EXISTS idx_users_email ON users.users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users.users(is_active) WHERE is_active = TRUE;

-- ============================================
-- НАВЫКИ
-- ============================================

CREATE TABLE IF NOT EXISTS users.skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50), -- 'programming', 'design', 'management', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.skills IS 'Справочник навыков';

CREATE INDEX IF NOT EXISTS idx_skills_name ON users.skills(name);
CREATE INDEX IF NOT EXISTS idx_skills_category ON users.skills(category);

-- Связь пользователей и навыков
CREATE TABLE IF NOT EXISTS users.user_skills (
    user_id UUID NOT NULL,
    skill_id INTEGER NOT NULL,
    level VARCHAR(20) DEFAULT 'intermediate', -- 'beginner', 'intermediate', 'advanced', 'expert'
    years_of_experience INTEGER,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES users.skills(id) ON DELETE CASCADE
);

COMMENT ON TABLE users.user_skills IS 'Навыки пользователей';

CREATE INDEX IF NOT EXISTS idx_user_skills_user ON users.user_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_user_skills_skill ON users.user_skills(skill_id);

-- ============================================
-- РЕЗЮМЕ
-- ============================================

CREATE TABLE IF NOT EXISTS users.resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    position VARCHAR(255), -- Желаемая должность
    salary_from INTEGER,
    salary_to INTEGER,
    salary_currency VARCHAR(3) DEFAULT 'RUR',
    experience_years INTEGER,
    about TEXT, -- О себе
    education TEXT, -- Образование
    work_experience JSONB, -- Опыт работы (массив объектов)
    skills_summary TEXT, -- Краткое описание навыков
    languages JSONB, -- Языки (массив объектов)
    is_primary BOOLEAN DEFAULT FALSE, -- Основное резюме
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE,
    FOREIGN KEY (salary_currency) REFERENCES vacancies.currencies(code) ON DELETE SET NULL
);

COMMENT ON TABLE users.resumes IS 'Резюме пользователей';
COMMENT ON COLUMN users.resumes.work_experience IS 'JSON массив опыта работы';
COMMENT ON COLUMN users.resumes.languages IS 'JSON массив языков';

CREATE INDEX IF NOT EXISTS idx_resumes_user ON users.resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_primary ON users.resumes(user_id, is_primary) WHERE is_primary = TRUE;
CREATE INDEX IF NOT EXISTS idx_resumes_active ON users.resumes(is_active) WHERE is_active = TRUE;

-- Полнотекстовый поиск по резюме
CREATE INDEX IF NOT EXISTS idx_resumes_fts ON users.resumes 
USING gin(to_tsvector('russian', 
    COALESCE(title, '') || ' ' || 
    COALESCE(position, '') || ' ' || 
    COALESCE(about, '') || ' ' || 
    COALESCE(skills_summary, '')
));

-- ============================================
-- ИЗБРАННЫЕ ВАКАНСИИ
-- ============================================

CREATE TABLE IF NOT EXISTS users.favorite_vacancies (
    user_id UUID NOT NULL,
    vacancy_id BIGINT NOT NULL,
    notes TEXT, -- Заметки пользователя
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, vacancy_id),
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE,
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE
);

COMMENT ON TABLE users.favorite_vacancies IS 'Избранные вакансии пользователей';

CREATE INDEX IF NOT EXISTS idx_favorite_vacancies_user ON users.favorite_vacancies(user_id);
CREATE INDEX IF NOT EXISTS idx_favorite_vacancies_vacancy ON users.favorite_vacancies(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_favorite_vacancies_created ON users.favorite_vacancies(created_at DESC);

-- ============================================
-- ОТКЛИКИ НА ВАКАНСИИ (заготовка)
-- ============================================

CREATE TABLE IF NOT EXISTS users.applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    vacancy_id BIGINT NOT NULL,
    resume_id UUID, -- Какое резюме использовано
    cover_letter TEXT, -- Сопроводительное письмо
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'viewed', 'rejected', 'invited'
    ai_generated_cover_letter BOOLEAN DEFAULT FALSE, -- Сгенерировано ли ИИ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE,
    FOREIGN KEY (vacancy_id) REFERENCES vacancies.vacancies(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES users.resumes(id) ON DELETE SET NULL,
    UNIQUE(user_id, vacancy_id) -- Один отклик на вакансию
);

COMMENT ON TABLE users.applications IS 'Отклики пользователей на вакансии';

CREATE INDEX IF NOT EXISTS idx_applications_user ON users.applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_vacancy ON users.applications(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON users.applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_created ON users.applications(created_at DESC);

-- ============================================
-- ИИ ЗАПРОСЫ (для аналитики)
-- ============================================

CREATE TABLE IF NOT EXISTS users.ai_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    request_type VARCHAR(50) NOT NULL, -- 'improve_resume', 'generate_cover_letter', 'analyze_match'
    input_data JSONB, -- Входные данные
    output_data JSONB, -- Результат
    provider VARCHAR(20), -- 'nebius', 'azure'
    tokens_used INTEGER,
    cost DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE
);

COMMENT ON TABLE users.ai_requests IS 'История ИИ запросов для аналитики';

CREATE INDEX IF NOT EXISTS idx_ai_requests_user ON users.ai_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_requests_type ON users.ai_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_ai_requests_created ON users.ai_requests(created_at DESC);

-- ============================================
-- ТРИГГЕРЫ
-- ============================================

-- Автообновление updated_at для users
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users.users
    FOR EACH ROW
    EXECUTE FUNCTION vacancies.update_updated_at_column();

-- Автообновление updated_at для resumes
CREATE TRIGGER update_resumes_updated_at
    BEFORE UPDATE ON users.resumes
    FOR EACH ROW
    EXECUTE FUNCTION vacancies.update_updated_at_column();

-- Автообновление updated_at для applications
CREATE TRIGGER update_applications_updated_at
    BEFORE UPDATE ON users.applications
    FOR EACH ROW
    EXECUTE FUNCTION vacancies.update_updated_at_column();

-- ============================================
-- ПРЕДСТАВЛЕНИЯ
-- ============================================

-- Пользователи с основным резюме
CREATE OR REPLACE VIEW users.users_with_resume AS
SELECT 
    u.*,
    r.id as primary_resume_id,
    r.title as primary_resume_title,
    r.position as primary_resume_position,
    r.salary_from as desired_salary_from,
    r.salary_to as desired_salary_to,
    r.salary_currency as desired_salary_currency
FROM users.users u
LEFT JOIN users.resumes r ON u.id = r.user_id AND r.is_primary = TRUE AND r.is_active = TRUE;

COMMENT ON VIEW users.users_with_resume IS 'Пользователи с основным резюме';

-- ============================================
-- ФУНКЦИИ
-- ============================================

-- Функция для получения навыков пользователя
CREATE OR REPLACE FUNCTION users.get_user_skills(user_uuid UUID)
RETURNS TABLE (
    skill_id INTEGER,
    skill_name VARCHAR(100),
    level VARCHAR(20),
    years_of_experience INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.name,
        us.level,
        us.years_of_experience
    FROM users.user_skills us
    JOIN users.skills s ON us.skill_id = s.id
    WHERE us.user_id = user_uuid
    ORDER BY s.name;
END;
$$ LANGUAGE plpgsql;

-- Функция для получения статистики пользователя
CREATE OR REPLACE FUNCTION users.get_user_stats(user_uuid UUID)
RETURNS TABLE (
    stat_name TEXT,
    stat_value BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'resumes'::TEXT, COUNT(*)::BIGINT FROM users.resumes WHERE user_id = user_uuid
    UNION ALL
    SELECT 'favorite_vacancies'::TEXT, COUNT(*)::BIGINT FROM users.favorite_vacancies WHERE user_id = user_uuid
    UNION ALL
    SELECT 'applications'::TEXT, COUNT(*)::BIGINT FROM users.applications WHERE user_id = user_uuid
    UNION ALL
    SELECT 'skills'::TEXT, COUNT(*)::BIGINT FROM users.user_skills WHERE user_id = user_uuid;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ============================================

-- Популярные навыки (можно расширить)
INSERT INTO users.skills (name, category) VALUES
('Python', 'programming'),
('JavaScript', 'programming'),
('Java', 'programming'),
('TypeScript', 'programming'),
('React', 'programming'),
('Vue.js', 'programming'),
('Node.js', 'programming'),
('SQL', 'programming'),
('PostgreSQL', 'programming'),
('Docker', 'devops'),
('Kubernetes', 'devops'),
('Git', 'tools'),
('Linux', 'tools'),
('Agile', 'methodology'),
('Scrum', 'methodology')
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- ЗАВЕРШЕНИЕ
-- ============================================

DO $$
DECLARE
    tables_count INTEGER;
    indexes_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO tables_count FROM information_schema.tables 
    WHERE table_schema = 'users' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO indexes_count FROM pg_indexes 
    WHERE schemaname = 'users';
    
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Users schema migration completed!';
    RAISE NOTICE 'Tables created: %', tables_count;
    RAISE NOTICE 'Indexes created: %', indexes_count;
    RAISE NOTICE '============================================';
END $$;

