-- Add account-lockout + profile fields to users.
-- Idempotent (IF NOT EXISTS): these columns already exist on the live DB from an
-- out-of-band ALTER; this migration reconciles schema/history without conflict.
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "failedLoginCount" INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "lockedUntil" TIMESTAMP(3);
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "lastLoginAt" TIMESTAMP(3);
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "fullName" TEXT;
