-- Conflict engine tables (ported from incentives-app).
-- Prisma maps `Decimal` (no @db) to DECIMAL(65,30) on PostgreSQL.

-- CreateTable
CREATE TABLE "conflict_resolution_strategies" (
    "id" TEXT NOT NULL,
    "strategyName" TEXT NOT NULL,
    "description" TEXT,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "conflict_resolution_strategies_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "detected_conflicts" (
    "id" TEXT NOT NULL,
    "projectId" TEXT,
    "sessionId" TEXT,
    "jurisdictionId" TEXT NOT NULL,
    "ruleKey1" TEXT NOT NULL,
    "ruleKey2" TEXT NOT NULL,
    "ruleType" TEXT,
    "conflictType" TEXT NOT NULL,
    "value1" DECIMAL(65,30),
    "value2" DECIMAL(65,30),
    "jurisdictionName1" TEXT,
    "jurisdictionName2" TEXT,
    "resolutionStrategyId" TEXT,
    "resolvedValue" DECIMAL(65,30),
    "resolvedBy" TEXT,
    "resolvedAt" TIMESTAMP(3),
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "detected_conflicts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_conflict_overrides" (
    "id" TEXT NOT NULL,
    "conflictId" TEXT,
    "chosenRuleKey" TEXT NOT NULL,
    "chosenValue" DECIMAL(65,30),
    "chosenBy" TEXT,
    "chosenAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT,

    CONSTRAINT "user_conflict_overrides_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "conflict_resolution_strategies_strategyName_key" ON "conflict_resolution_strategies"("strategyName");

-- CreateIndex
CREATE INDEX "detected_conflicts_projectId_idx" ON "detected_conflicts"("projectId");

-- CreateIndex
CREATE INDEX "detected_conflicts_resolvedAt_idx" ON "detected_conflicts"("resolvedAt");

-- CreateIndex
CREATE INDEX "user_conflict_overrides_conflictId_idx" ON "user_conflict_overrides"("conflictId");

-- AddForeignKey
ALTER TABLE "detected_conflicts" ADD CONSTRAINT "detected_conflicts_jurisdictionId_fkey" FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "detected_conflicts" ADD CONSTRAINT "detected_conflicts_resolutionStrategyId_fkey" FOREIGN KEY ("resolutionStrategyId") REFERENCES "conflict_resolution_strategies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_conflict_overrides" ADD CONSTRAINT "user_conflict_overrides_conflictId_fkey" FOREIGN KEY ("conflictId") REFERENCES "detected_conflicts"("id") ON DELETE CASCADE ON UPDATE CASCADE;
