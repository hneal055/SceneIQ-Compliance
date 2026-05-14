-- AlterTable
ALTER TABLE "incentive_rules" ADD COLUMN     "creditType" TEXT NOT NULL DEFAULT 'refundable';

-- AlterTable
ALTER TABLE "jurisdictions" ADD COLUMN     "currency" TEXT NOT NULL DEFAULT 'USD',
ADD COLUMN     "treatyPartners" TEXT[];

-- AlterTable
ALTER TABLE "notification_preferences" ADD COLUMN     "reportFrequency" TEXT NOT NULL DEFAULT 'never';

