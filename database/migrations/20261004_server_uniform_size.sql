-- Step 24C-D-9: server uniform size.
--
-- Operational data: the clothing size a server wears, so staffing can check a
-- uniform is available before an event. Recorded once on the server, not per
-- assignment, because it is a property of the person.
--
-- WHY AN ENUM AND NOT TEXT.
-- A free-text column would let 'L', 'l', 'large', 'Grand' and 'L ' coexist for
-- the same size, and a print sheet would then have to decide how to group them.
-- The enum makes the value set exactly XS..XXXL, so an invalid size is rejected
-- by the database as well as by the API.
--
-- WHY NULLABLE.
-- Existing servers, and the seed data, have no measured uniform size. There is
-- no honest default to fill: a default would assert a size nobody recorded, and
-- "S" would then be indistinguishable from a real measurement. NULL means
-- "not recorded" and is displayed as such.
--
-- Idempotent: safe to run repeatedly. The enum is created only if absent and
-- the column only if absent, so a re-apply is a no-op.
--
-- Deploy order: this migration must be applied BEFORE the code that reads or
-- writes servers.uniform_size. The column is additive and nullable, so it can
-- also be applied while the old code is still running.

-- ===================================================
-- Enum: uniform size
-- ===================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'server_uniform_size') THEN
        CREATE TYPE server_uniform_size AS ENUM (
            'XS',
            'S',
            'M',
            'L',
            'XL',
            'XXL',
            'XXXL'
        );
    END IF;
END$$;

-- ===================================================
-- Column: servers.uniform_size
--
-- Added with no DEFAULT and no NOT NULL, so every existing row reads NULL and
-- no backfill is implied.
-- ===================================================
ALTER TABLE servers ADD COLUMN IF NOT EXISTS uniform_size server_uniform_size;
