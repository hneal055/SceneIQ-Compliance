-- CreateTable
CREATE TABLE "schedule_events" (
    "id" TEXT NOT NULL,
    "channel" TEXT NOT NULL,
    "scheduleDate" TEXT,
    "sourceFile" TEXT NOT NULL,
    "sourceFormat" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "episodeTitle" TEXT,
    "episodeNumber" TEXT,
    "seriesNumber" TEXT,
    "txTime" TEXT,
    "duration" TEXT,
    "genre" TEXT,
    "rightsStart" TEXT,
    "rightsEnd" TEXT,
    "assetId" TEXT,
    "daypart" TEXT,
    "importedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "productionId" TEXT,

    CONSTRAINT "schedule_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "schedule_events_channel_idx" ON "schedule_events"("channel");

-- CreateIndex
CREATE INDEX "schedule_events_scheduleDate_idx" ON "schedule_events"("scheduleDate");

-- CreateIndex
CREATE INDEX "schedule_events_sourceFormat_idx" ON "schedule_events"("sourceFormat");

-- CreateIndex
CREATE INDEX "schedule_events_importedAt_idx" ON "schedule_events"("importedAt");
