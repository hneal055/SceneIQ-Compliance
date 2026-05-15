-- Phase 11.5 fix #4: JurisdictionShootDays.verifiedAt becomes nullable.
--
-- Previously the column was DateTime @default(now()), which made every
-- row implicitly "verified" the moment it was created. The Verify
-- vs Unverified UI state was therefore dead — the field was never null
-- so the frontend's `!!verified_at` check always returned true.
--
-- After this migration: new rows default to NULL; the
-- POST /jurisdiction-tracker/verify endpoint (Phase 11.5) explicitly
-- writes a timestamp via the existing verify_shoot_days() pure function.
--
-- Existing rows retain their non-null verifiedAt values — no data loss.
ALTER TABLE "jurisdiction_shoot_days"
  ALTER COLUMN "verifiedAt" DROP NOT NULL,
  ALTER COLUMN "verifiedAt" DROP DEFAULT;
