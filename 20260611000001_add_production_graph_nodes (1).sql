-- ============================================================
-- SceneIQ Production Graph — Phase 2 Migration
-- Adds: crew_members, production_locations, budget_lines,
--       production_signals
-- Safe to apply: no existing tables modified
-- ============================================================

-- CREW MEMBER NODE
CREATE TABLE "crew_members" (
    "id"            TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "productionId"  TEXT NOT NULL,
    "name"          TEXT NOT NULL,
    "role"          TEXT NOT NULL,
    "department"    TEXT NOT NULL,
    "union"         TEXT,
    "dailyRate"     DOUBLE PRECISION,
    "weeklyRate"    DOUBLE PRECISION,
    "startDate"     TIMESTAMP(3),
    "endDate"       TIMESTAMP(3),
    "status"        TEXT NOT NULL DEFAULT 'active',
    "notes"         TEXT,
    "createdAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "crew_members_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "crew_members_productionId_fkey"
        FOREIGN KEY ("productionId")
        REFERENCES "productions"("id")
        ON DELETE CASCADE
);

CREATE INDEX "crew_members_productionId_idx" ON "crew_members"("productionId");
CREATE INDEX "crew_members_department_idx"   ON "crew_members"("department");

-- PRODUCTION LOCATION NODE
CREATE TABLE "production_locations" (
    "id"            TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "productionId"  TEXT NOT NULL,
    "name"          TEXT NOT NULL,
    "address"       TEXT,
    "city"          TEXT,
    "state"         TEXT,
    "country"       TEXT,
    "locationType"  TEXT NOT NULL,
    "permitStatus"  TEXT,
    "dailyCost"     DOUBLE PRECISION,
    "notes"         TEXT,
    "createdAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "production_locations_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "production_locations_productionId_fkey"
        FOREIGN KEY ("productionId")
        REFERENCES "productions"("id")
        ON DELETE CASCADE
);

CREATE INDEX "production_locations_productionId_idx" ON "production_locations"("productionId");

-- BUDGET LINE NODE
CREATE TABLE "budget_lines" (
    "id"            TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "productionId"  TEXT NOT NULL,
    "category"      TEXT NOT NULL,
    "lineItem"      TEXT NOT NULL,
    "accountCode"   TEXT,
    "estimated"     DOUBLE PRECISION NOT NULL,
    "actual"        DOUBLE PRECISION,
    "variance"      DOUBLE PRECISION,
    "notes"         TEXT,
    "createdAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "budget_lines_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "budget_lines_productionId_fkey"
        FOREIGN KEY ("productionId")
        REFERENCES "productions"("id")
        ON DELETE CASCADE
);

CREATE INDEX "budget_lines_productionId_idx" ON "budget_lines"("productionId");
CREATE INDEX "budget_lines_category_idx"     ON "budget_lines"("category");

-- PRODUCTION SIGNAL NODE (the autonomous OS intelligence layer)
CREATE TABLE "production_signals" (
    "id"            TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "productionId"  TEXT NOT NULL,
    "signalType"    TEXT NOT NULL,
    "severity"      TEXT NOT NULL,
    "source"        TEXT,
    "entityType"    TEXT,
    "entityId"      TEXT,
    "message"       TEXT NOT NULL,
    "resolved"      BOOLEAN NOT NULL DEFAULT false,
    "resolvedAt"    TIMESTAMP(3),
    "resolvedBy"    TEXT,
    "createdAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "production_signals_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "production_signals_productionId_fkey"
        FOREIGN KEY ("productionId")
        REFERENCES "productions"("id")
        ON DELETE CASCADE
);

CREATE INDEX "production_signals_productionId_idx" ON "production_signals"("productionId");
CREATE INDEX "production_signals_signalType_idx"   ON "production_signals"("signalType");
CREATE INDEX "production_signals_severity_idx"     ON "production_signals"("severity");
CREATE INDEX "production_signals_resolved_idx"     ON "production_signals"("resolved");
