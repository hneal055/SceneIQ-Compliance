-- Set DB-level default to empty array so future INSERTs without an
-- explicit value get '{}' instead of NULL.
ALTER TABLE jurisdictions
  ALTER COLUMN "treatyPartners" SET DEFAULT '{}'::text[];

-- Backfill any existing rows that landed with NULL when the column
-- was added in 20260514081221_add_missing_columns_to_existing_tables.
UPDATE jurisdictions
  SET "treatyPartners" = '{}'
  WHERE "treatyPartners" IS NULL;
