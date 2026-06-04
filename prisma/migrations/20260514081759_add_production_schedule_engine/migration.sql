-- CreateTable
CREATE TABLE "scenes" (
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

-- CreateTable
CREATE TABLE "shoot_days" (
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
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "shoot_days_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "cast_members" (
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

-- CreateTable
CREATE TABLE "call_sheets" (
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

-- CreateTable
CREATE TABLE "jurisdiction_shoot_days" (
    "id" TEXT NOT NULL,
    "productionId" TEXT NOT NULL,
    "jurisdictionId" TEXT NOT NULL,
    "shootDays" INTEGER NOT NULL DEFAULT 0,
    "verifiedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "jurisdiction_shoot_days_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "scenes_productionId_idx" ON "scenes"("productionId");

-- CreateIndex
CREATE INDEX "scenes_shootDayId_idx" ON "scenes"("shootDayId");

-- CreateIndex
CREATE INDEX "scenes_jurisdictionId_idx" ON "scenes"("jurisdictionId");

-- CreateIndex
CREATE INDEX "shoot_days_productionId_idx" ON "shoot_days"("productionId");

-- CreateIndex
CREATE INDEX "shoot_days_jurisdictionId_idx" ON "shoot_days"("jurisdictionId");

-- CreateIndex
CREATE UNIQUE INDEX "shoot_days_productionId_dayNumber_key" ON "shoot_days"("productionId", "dayNumber");

-- CreateIndex
CREATE INDEX "cast_members_productionId_idx" ON "cast_members"("productionId");

-- CreateIndex
CREATE INDEX "call_sheets_productionId_idx" ON "call_sheets"("productionId");

-- CreateIndex
CREATE INDEX "call_sheets_shootDayId_idx" ON "call_sheets"("shootDayId");

-- CreateIndex
CREATE INDEX "jurisdiction_shoot_days_productionId_idx" ON "jurisdiction_shoot_days"("productionId");

-- CreateIndex
CREATE INDEX "jurisdiction_shoot_days_jurisdictionId_idx" ON "jurisdiction_shoot_days"("jurisdictionId");

-- CreateIndex
CREATE UNIQUE INDEX "jurisdiction_shoot_days_productionId_jurisdictionId_key" ON "jurisdiction_shoot_days"("productionId", "jurisdictionId");

-- AddForeignKey
ALTER TABLE "scenes" ADD CONSTRAINT "scenes_productionId_fkey" FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scenes" ADD CONSTRAINT "scenes_jurisdictionId_fkey" FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "scenes" ADD CONSTRAINT "scenes_shootDayId_fkey" FOREIGN KEY ("shootDayId") REFERENCES "shoot_days"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shoot_days" ADD CONSTRAINT "shoot_days_productionId_fkey" FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "shoot_days" ADD CONSTRAINT "shoot_days_jurisdictionId_fkey" FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cast_members" ADD CONSTRAINT "cast_members_productionId_fkey" FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "call_sheets" ADD CONSTRAINT "call_sheets_productionId_fkey" FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "call_sheets" ADD CONSTRAINT "call_sheets_shootDayId_fkey" FOREIGN KEY ("shootDayId") REFERENCES "shoot_days"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "jurisdiction_shoot_days" ADD CONSTRAINT "jurisdiction_shoot_days_productionId_fkey" FOREIGN KEY ("productionId") REFERENCES "productions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "jurisdiction_shoot_days" ADD CONSTRAINT "jurisdiction_shoot_days_jurisdictionId_fkey" FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

