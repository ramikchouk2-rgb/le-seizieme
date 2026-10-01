-- Step 24C-D-6: professional attestations.
--
-- BUSINESS RULE enforced by this schema: an attestation is NOT a verified
-- professional qualification until a Manager or Admin explicitly verifies it.
-- A freshly uploaded document is PENDING and nothing else may mark it VERIFIED.
--
-- Storage: documents are BYTEA rows in the existing `server_files` table
-- (Step 24C-D-5). This table only references the file; document bytes are never
-- duplicated here.
--
-- History: attestations are append-only. A new document never deletes or
-- overwrites an older row; the old one moves to SUPERSEDED instead, and
-- superseded_by_id records the chain.
--
-- Idempotent: safe to run repeatedly.

-- ===================================================
-- Enum: attestation status
-- ===================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attestation_status') THEN
        CREATE TYPE attestation_status AS ENUM (
            'PENDING',    -- uploaded, awaiting a human decision; NOT a qualification
            'VERIFIED',   -- explicitly verified by a Manager/Admin; counts as a qualification
            'REJECTED',   -- refused; rejection_reason is mandatory
            'SUPERSEDED'  -- replaced by a newer document; never counts
        );
    END IF;
END$$;

-- ===================================================
-- Enum: new server file kind
--
-- NOTE: PostgreSQL cannot use a newly added enum value in the same transaction
-- that adds it, so this ALTER must be committed before any row is written with
-- the ATTESTATION value. It is therefore a statement of its own here, and the
-- DDL below deliberately avoids referencing the literal (no DEFAULT, no CHECK
-- on the label). The service layer enforces the file kind.
-- ===================================================
ALTER TYPE server_file_type ADD VALUE IF NOT EXISTS 'ATTESTATION';

-- ===================================================
-- Scope the "one current file" guarantee to profile photos
--
-- Step 24C-D-5 created a partial UNIQUE index over (server_id, file_type)
-- WHERE is_current, which is correct for avatars but wrong for attestations: a
-- server legitimately has SEVERAL current attestation documents at once, and
-- attestations are append-only. Left unchanged, uploading a second attestation
-- document would fail with a unique violation.
--
-- The predicate names only the PRE-EXISTING 'PROFILE_PHOTO' label, so it is
-- safe to evaluate in the same transaction that added the new enum value
-- (PostgreSQL only forbids using a not-yet-committed label in DDL). It must be
-- an enum comparison rather than a ::text cast, because an index predicate may
-- only reference IMMUTABLE expressions and the enum-to-text cast is not.
-- ===================================================
DROP INDEX IF EXISTS idx_server_files_unique_current;

CREATE UNIQUE INDEX IF NOT EXISTS idx_server_files_unique_current_photo
    ON server_files(server_id, file_type)
    WHERE is_current = TRUE AND file_type = 'PROFILE_PHOTO';

-- ===================================================
-- Widen the server_files MIME allowlist for documents
--
-- Step 24C-D-5 restricted server_files to image types, which is correct for
-- avatars. Attestation documents are mostly PDF, so the constraint is replaced
-- rather than dropped: the same three image types plus PDF, nothing looser.
-- Only string literals are involved, so this is safe in the same transaction
-- as the enum value added above.
-- ===================================================
ALTER TABLE server_files DROP CONSTRAINT IF EXISTS server_files_mime_allowed_check;
ALTER TABLE server_files ADD CONSTRAINT server_files_mime_allowed_check CHECK (
    mime_type IN ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')
);

-- ===================================================
-- Table: server_attestations
-- ===================================================
CREATE TABLE IF NOT EXISTS server_attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    file_id UUID NOT NULL REFERENCES server_files(id) ON DELETE RESTRICT,
    status attestation_status NOT NULL DEFAULT 'PENDING',
    qualification_name VARCHAR(200) NOT NULL,
    issuing_organization VARCHAR(200),
    issued_on DATE,
    expires_on DATE,
    rejection_reason TEXT,
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    superseded_by_id UUID REFERENCES server_attestations(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- A blank qualification name is not a usable record.
    CONSTRAINT server_attestations_name_not_blank_check
        CHECK (btrim(qualification_name) <> ''),

    -- Expiry, when present, cannot precede issuance.
    CONSTRAINT server_attestations_dates_ordered_check
        CHECK (expires_on IS NULL OR issued_on IS NULL OR expires_on >= issued_on),

    -- A rejection must carry a real, non-blank reason.
    CONSTRAINT server_attestations_rejection_reason_check
        CHECK (
            status <> 'REJECTED'
            OR (rejection_reason IS NOT NULL AND btrim(rejection_reason) <> '')
        ),

    -- Only VERIFIED rows may carry verification metadata, and they must carry
    -- it: a verified qualification always names its verifier and its timestamp.
    CONSTRAINT server_attestations_verified_fields_check
        CHECK (
            (status = 'VERIFIED'
                AND verified_at IS NOT NULL
                AND verified_by IS NOT NULL
                AND rejection_reason IS NULL)
            OR (status <> 'VERIFIED')
        ),

    -- A row that is not VERIFIED and not REJECTED must not look verified:
    -- PENDING and SUPERSEDED rows keep their old verification data only as
    -- audit history, so only REJECTED is forbidden from holding it.
    CONSTRAINT server_attestations_rejected_not_verified_check
        CHECK (status <> 'REJECTED' OR (verified_at IS NULL AND verified_by IS NULL)),

    -- An attestation cannot supersede itself.
    CONSTRAINT server_attestations_no_self_supersede_check
        CHECK (superseded_by_id IS NULL OR superseded_by_id <> id)
);

-- Hot-path lookups: a server's attestation list, and status filtering.
CREATE INDEX IF NOT EXISTS idx_server_attestations_server_id
    ON server_attestations(server_id);

CREATE INDEX IF NOT EXISTS idx_server_attestations_status
    ON server_attestations(status);

-- One document per attestation row; also prevents a shared document between rows.
CREATE INDEX IF NOT EXISTS idx_server_attestations_file_id
    ON server_attestations(file_id);

-- "Does this server have a verified qualification?" and audit-by-verifier.
CREATE INDEX IF NOT EXISTS idx_server_attestations_verified_by
    ON server_attestations(verified_by);

-- Counting verified qualifications per server without touching the documents.
CREATE INDEX IF NOT EXISTS idx_server_attestations_server_status
    ON server_attestations(server_id, status);
