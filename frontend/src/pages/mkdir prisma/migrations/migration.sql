-- Add episode_count column to productions table
ALTER TABLE productions
  ADD COLUMN IF NOT EXISTS episode_count INTEGER;
  