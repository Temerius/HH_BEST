-- ============================================
-- Add specialization field to users table
-- Version: 3.0
-- Date: 2025-11-23
-- ============================================

ALTER TABLE users.users 
ADD COLUMN IF NOT EXISTS specialization VARCHAR(100);

COMMENT ON COLUMN users.users.specialization IS 'Основное направление разработки (например, Backend, Frontend, Fullstack, DevOps)';

