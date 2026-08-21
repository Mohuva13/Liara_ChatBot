BEGIN;

-- 001 used a doubly escaped PostgreSQL regex, which rejected valid canonical
-- documentation URLs. Replace it for already-created databases. The definition
-- check keeps this migration cheap when the idempotent runner applies it again.
DO $migration$
DECLARE
    constraint_definition text;
BEGIN
    SELECT pg_get_constraintdef(oid)
    INTO constraint_definition
    FROM pg_constraint
    WHERE conrelid = 'documents'::regclass
      AND conname = 'documents_canonical_url_check';

    IF constraint_definition IS NULL
       OR strpos(constraint_definition, 'https://docs.liara.ir/%') = 0 THEN
        ALTER TABLE documents
            DROP CONSTRAINT IF EXISTS documents_canonical_url_check;
        ALTER TABLE documents
            ADD CONSTRAINT documents_canonical_url_check
            CHECK (canonical_url LIKE 'https://docs.liara.ir/%');
    END IF;
END;
$migration$;

COMMIT;
