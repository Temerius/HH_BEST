-- ============================================
-- Add file_path column to resumes table
-- Version: 5.0
-- Date: 2025-12-16
-- ============================================

ALTER TABLE users.resumes 
ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);

COMMENT ON COLUMN users.resumes.file_path IS 'Путь к PDF файлу резюме';

