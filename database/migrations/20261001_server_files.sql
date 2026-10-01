-- Step 24C-D-5: reusable server file storage.
--
-- `servers.profile_photo` is dead legacy infrastructure (a TEXT column that no
-- code reads or writes). It is intentionally LEFT UNTOUCHED for backward
-- compatibility, and this table becomes the authoritative photo store.
--
-- Design notes:
--   * BYTEA storage: no external object storage, no public URLs, no signed links.
--   * `server_file_type` is an enum rather than a free TEXT column so that a
--     later file kind (e.g. attestations) can be added without a table rewrite.
--     Only PROFILE_PHOTO exists today; adding a value is a separate, additive step.
--   * NO location/GPS columns. A file record carries bytes and descriptive
--     metadata only.
--   * `file_size = octet_length(content)` is enforced by a CHECK constraint, so
--     a size mismatch can never be persisted.
--   * Partial UNIQUE index on (server_id, file_type) WHERE is_current: at most
--     one current file per kind per server, while replaced files are retained
--     as history rather than deleted.
--
-- Idempotent: safe to run repeatedly.

-- ===================================================
-- Enum: server file type
-- ===================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'server_file_type') THEN
        CREATE TYPE server_file_type AS ENUM ('PROFILE_PHOTO');
    END IF;
END$$;

-- ===================================================
-- Table: server_files
-- ===================================================
CREATE TABLE IF NOT EXISTS server_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    file_type server_file_type NOT NULL DEFAULT 'PROFILE_PHOTO',
    content BYTEA NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    original_filename VARCHAR(255),
    file_size INTEGER NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Reject an empty upload: no zero-byte or NULL-ish "photo".
    CONSTRAINT server_files_content_nonempty_check CHECK (octet_length(content) > 0),

    -- A declared size that disagrees with the stored bytes is a bug or an
    -- attack; refuse it at the storage layer rather than trusting the caller.
    CONSTRAINT server_files_size_matches_content_check
        CHECK (file_size = octet_length(content)),

    -- Only image MIME types are ever stored today.
    CONSTRAINT server_files_mime_allowed_check CHECK (
        mime_type IN ('image/jpeg', 'image/png', 'image/webp')
    ),

    -- No public URL is stored. Enforced structurally: there is no such column.
    CONSTRAINT server_files_filename_no_path_check CHECK (
        original_filename IS NULL OR original_filename NOT LIKE '%/%'
        OR original_filename NOT LIKE '%\\%'
    )
);

-- Lookup by server (batch metadata projection, no BYTEA selected by callers).
CREATE INDEX IF NOT EXISTS idx_server_files_server_id
    ON server_files(server_id);

-- Current-file lookup: the only index used by photo reads.
CREATE INDEX IF NOT EXISTS idx_server_files_current
    ON server_files(server_id, file_type)
    WHERE is_current = TRUE;

-- At most one current file per kind per server. Concurrent uploads of the same
-- kind cannot both become current.
CREATE UNIQUE INDEX IF NOT EXISTS idx_server_files_unique_current
    ON server_files(server_id, file_type)
    WHERE is_current = TRUE;