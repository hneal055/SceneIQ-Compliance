-- CreateTable
CREATE TABLE "jurisdiction_requirements" (
    "id" TEXT NOT NULL,
    "jurisdictionId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "requirementType" TEXT NOT NULL DEFAULT 'mandatory',
    "description" TEXT NOT NULL,
    "applicableTo" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "contactInfo" TEXT,
    "portalUrl" TEXT,
    "sourceUrl" TEXT,
    "extractedBy" TEXT NOT NULL DEFAULT 'monitor',
    "active" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "jurisdiction_requirements_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_scenarios" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "codes" TEXT NOT NULL,
    "spend" TEXT NOT NULL,
    "projectType" TEXT NOT NULL DEFAULT 'film',
    "splitSpend" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "user_scenarios_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "jurisdiction_requirements_jurisdictionId_idx" ON "jurisdiction_requirements"("jurisdictionId");

-- CreateIndex
CREATE INDEX "jurisdiction_requirements_category_idx" ON "jurisdiction_requirements"("category");

-- CreateIndex
CREATE INDEX "user_scenarios_userId_idx" ON "user_scenarios"("userId");

-- AddForeignKey
ALTER TABLE "jurisdiction_requirements" ADD CONSTRAINT "jurisdiction_requirements_jurisdictionId_fkey" FOREIGN KEY ("jurisdictionId") REFERENCES "jurisdictions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_scenarios" ADD CONSTRAINT "user_scenarios_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

