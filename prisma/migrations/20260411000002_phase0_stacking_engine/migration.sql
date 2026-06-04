-- Phase 0: Sub-Jurisdiction Layer - Stacking Engine Tables
-- FK constraint skipped: column naming handled in migration 000001

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS "production_scenarios" (
    "id"                TEXT        NOT NULL DEFAULT gen_random_uuid(),
    "productionId"      TEXT        NOT NULL,
    "name"              TEXT        NOT NULL,
    "totalBudget"       DECIMAL(12,2),
    "qualifiedSpend"    DECIMAL(12,2),
    "spendByCategory"   JSONB,
    "shootingDays"      INTEGER,
    "daysByJurisdiction" JSONB,
    "postLocation"      TEXT,
    "localHirePercent"  DECIMAL(5,2),
    "hireByJurisdiction" JSONB,
    "createdAt"         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt"         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT "production_scenarios_pkey" PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "scenario_optimization_results" (
    "id"                    TEXT        NOT NULL DEFAULT gen_random_uuid(),
    "scenarioId"            TEXT        NOT NULL,
    "recommendedStack"      JSONB       NOT NULL DEFAULT '[]',
    "totalIncentiveValue"   DECIMAL(12,2),
    "effectiveRate"         DECIMAL(5,2),
    "cashFlowEstimate"      TEXT,
    "warnings"              JSONB,
    "createdAt"             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "expiresAt"             TIMESTAMPTZ,
    CONSTRAINT "scenario_optimization_results_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "scenario_optimization_results_unique" UNIQUE ("scenarioId")
);