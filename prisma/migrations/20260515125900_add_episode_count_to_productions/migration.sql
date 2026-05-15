-- Add episode_count to productions
ALTER TABLE productions ADD COLUMN IF NOT EXISTS episode_count INTEGER;
