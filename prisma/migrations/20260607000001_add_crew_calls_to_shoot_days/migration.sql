-- AlterTable
-- IF NOT EXISTS so this is safe whether it runs before or after the
-- idempotent bootstrap_schedule_tables.sql, which adds the same column.
ALTER TABLE "shoot_days" ADD COLUMN IF NOT EXISTS "crewCalls" JSONB;
