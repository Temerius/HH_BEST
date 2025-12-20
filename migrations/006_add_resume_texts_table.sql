-- ============================================
-- Add resume_texts table for storing PDF text content
-- Version: 6.0
-- Date: 2025-12-16
-- ============================================

CREATE TABLE IF NOT EXISTS users.resume_texts (
    user_id UUID PRIMARY KEY,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE
);

COMMENT ON TABLE users.resume_texts IS 'Текст резюме, извлеченный из PDF файла';
COMMENT ON COLUMN users.resume_texts.text IS 'Полный текст резюме из PDF';

CREATE INDEX IF NOT EXISTS idx_resume_texts_user ON users.resume_texts(user_id);

-- Автообновление updated_at для resume_texts
CREATE TRIGGER update_resume_texts_updated_at
    BEFORE UPDATE ON users.resume_texts
    FOR EACH ROW
    EXECUTE FUNCTION vacancies.update_updated_at_column();

