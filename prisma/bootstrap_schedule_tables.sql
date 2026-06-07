-- =============================================================================
-- bootstrap_schedule_tables.sql
--
-- Idempotent, migration-history-INDEPENDENT creation of the Production
-- Schedule Engine tables (scenes, shoot_days, cast_members, call_sheets,
-- jurisdiction_shoot_days) plus their indexes and foreign keys.
--
-- WHY THIS EXISTS:
--   `prisma migrate deploy` is the normal path for applying these tables
--   (migration 20260514081759_add_production_schedule_engine). But if the
--   prod migration history is in a failed/drifted state, `migrate deploy`
--   aborts BEFORE reaching that migration and the tables never land — every
--   /production-schedule endpoint then throws 500 ("relation does not
--   exist"). The Dockerfile masks the migrate failure with `|| echo`, so the
--   API boots anyway and the 500s persist silently.
--
--   This script is run at startup AFTER `migrate deploy` as a safety net. It
--   only ever CREATEs missing objects (everything is guarded with
--   IF NOT EXISTS / pg_constraint checks), so it is safe to run on every boot
--   and cannot touch or drop existing data.
--
-- NOTE: jurisdiction_shoot_days.verifiedAt is created NULLABLE here — that is
--   the final intended state (migration 20260515115923_make_verified_at_nullable).
--   The ComplianceBridge relies on NULL meaning "not yet verified".
-- =============================================================================

-- ── Tables ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS "scenes" (
    "id" TEXT NOT NULL,
    "productionId" TEXT NOT NULL,
    "sceneNumber" TEXT NOT NULL,
    "title" TEXT,
    "location" TEXT,
    "locationType" TEXT,
    "timeOfDay" TEXT,
    "pageCount" DOUBLE PRECISION,
    "jurisdictionId" TEXT,
    "castIds" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "notes" TEXT,
    "shootDayId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "scenes_pkey" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "shoot_days" (
    "id" TEXT NOT NULL,
    "productionId" TEXT NOT NULL,
    "dayNumber" INTEGER NOT NULL,
    "date" TEXT,
    "jurisdictionId" TEXT,
    "totalPages" DOUBLE PRECISION,
    "callTime" TEXT,
    "location" TEXT,
    "nearestHospital" TEXT,
    "notes" TEXT,
    "crewCalls" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "shoot_days_pkey" PRIMARY KEY ("id")
);

-- crewCalls was added after the initial shoot_days table (Phase: crew calls).
-- Guarded so it lands on databases whose shoot_days predates the column.
ALTER TABLE "shoot_days" ADD COLUMN IF NOT EXISTS "crewCalls" JSONB;

CREATE TABLE IF NOT EXISTS "cast_members" (
    "id" TEXT NOT NULL,
    "productionId" TEXT NOT NULL,
    "characterName" TEXT NOT NULL,
    "actorName" TEXT,
    "doodEntries" JSONB,
    "startDay" INTEGER,
    "finishDay" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "cast_members_pkey" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "call_sheets" (
    "id" TEXT NOT NULL,
    "productionId" TEXT NOT NULL,
    "shootDayId" TEXT NOT NULL,
    "dayNumber" INTEGER NOT NULL,
    "date" TEXT,
    "generalCall" TEXT,
    "location" TEXT,
    "nearestHospital" TEXT,
    "weather" TEXT,
    "scenes" JSONB,
    "crewCalls" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "call_sheets_pkey" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "jurisdiction_shoot_days" (
    "id" TEXT NOT NULL,
    "productionId" TEXT NOT NULL,
    "jurisdictionId" TEXT NOT NULL,
    "shootDays" INTEGER NOT NULL DEFAULT 0,
    "verifiedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "jurisdiction_shoot_days_pkey" PRIMARY KEY ("id")
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS "scenes_productionId_idx" ON "scenes"("productionId");
CREATE INDEX IF NOT EXISTS "scenes_shootDayId_idx" ON "scenes"("shootDayId");
CREATE INDEX IF NOT EXISTS "scenes_jurisdictionId_idx" ON "scenes"("jurisdictionId");

CREATE INDEX IF NOT EXISTS "shoot_days_productionId_idx" ON "shoot_days"("productionId");
CREATE INDEX IF NOT EXISTS "shoot_days_jurisdictionId_idx" ON "shoot_days"("jurisdictionId");
CREATE UNIQUE INDEX IF NOT EXISTS "shoot_days_productionId_dayNumber_key" ON "shoot_days"("productionId", "dayNumber");

CREATE INDEX IF NOT EXISTS "cast_members_productionId_idx" ON "cast_members"("productionId");

CREATE INDEX IF NOT EXISTS "call_sheets_productionId_idx" ON "call_sheets"("productionId");
CREATE INDEX IF NOT EXISTS "call_sheets_shootDayId_idx" ON "call_sheets"("shootDayId");

CREATE INDEX IF NOT EXISTS "jurisdiction_shoot_days_productionId_idx" ON "jurisdiction_shoot_days"("productionId");
CREATE INDEX IF NOT EXISTS "jurisdiction_shoot_days_jurisdictionId_idx" ON "jurisdiction_shoot_days"("jurisdictionId");
CREATE UNIQUE INDEX IF NOT EXISTS "jurisdiction_shoot_days_productionId_jurisdictionId_key" ON "jurisdiction_shoot_days"("productionId", "jurisdictionId");

-- ── Foreign keys (Postgres has no ADD CONSTRAINT IF NOT EXISTS) ────────────────
-- Each FK is added only if a constraint of that name does not already exist.

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'scenes_productionId_fkey') THEN
    ALTER TABLE "scenes" ADD CONSTRAINT "scenes_productionId_fkey"
      FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'scenes_jurisdictionId_fkey') THEN
    ALTER TABLE "scenes" ADD CONSTRAINT "scenes_jurisdictionId_fkey"
      FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'scenes_shootDayId_fkey') THEN
    ALTER TABLE "scenes" ADD CONSTRAINT "scenes_shootDayId_fkey"
      FOREIGN KEY ("shootDayId") REFERENCES "shoot_days"("id") ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'shoot_days_productionId_fkey') THEN
    ALTER TABLE "shoot_days" ADD CONSTRAINT "shoot_days_productionId_fkey"
      FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'shoot_days_jurisdictionId_fkey') THEN
    ALTER TABLE "shoot_days" ADD CONSTRAINT "shoot_days_jurisdictionId_fkey"
      FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cast_members_productionId_fkey') THEN
    ALTER TABLE "cast_members" ADD CONSTRAINT "cast_members_productionId_fkey"
      FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'call_sheets_productionId_fkey') THEN
    ALTER TABLE "call_sheets" ADD CONSTRAINT "call_sheets_productionId_fkey"
      FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'call_sheets_shootDayId_fkey') THEN
    ALTER TABLE "call_sheets" ADD CONSTRAINT "call_sheets_shootDayId_fkey"
      FOREIGN KEY ("shootDayId") REFERENCES "shoot_days"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'jurisdiction_shoot_days_productionId_fkey') THEN
    ALTER TABLE "jurisdiction_shoot_days" ADD CONSTRAINT "jurisdiction_shoot_days_productionId_fkey"
      FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'jurisdiction_shoot_days_jurisdictionId_fkey') THEN
    ALTER TABLE "jurisdiction_shoot_days" ADD CONSTRAINT "jurisdiction_shoot_days_jurisdictionId_fkey"
      FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END $$;
