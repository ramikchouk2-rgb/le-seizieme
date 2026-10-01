-- ===================================================
-- Step 24C-D-7: audit actions for server files and attestations
--
-- Extends the existing admin_audit_action enum so administrative actions on
-- server profile photos and professional attestations become visible in the
-- audit log.
--
-- PHOTO UPLOAD vs REPLACEMENT IS ONE ACTION.
-- An upload and a replacement are the same user-facing operation; the only
-- difference is whether a current photo already existed. That fact is recorded
-- as detail->>'replaced' rather than as a separate enum value, so the two can
-- never drift apart and the action list stays honest.
--
-- target_user_id STAYS NULL for these events.
-- server_files and server_attestations are not users, and audit_log's
-- target_user_id is a foreign key onto users(id): writing a server id there
-- would raise a ForeignKeyViolation. The server is identified instead by
-- detail->>'server_id', and the acting Manager/Admin by actor_user_id.
--
-- No audit row is inserted here. The new labels are also deliberately not used
-- anywhere in this file: PostgreSQL refuses to use a not-yet-committed enum
-- value ("New enum values must be committed before they can be used"), so each
-- ADD VALUE must commit on its own. Applying this file in autocommit -- one
-- statement per implicit transaction -- satisfies that, which is the pattern
-- already proven by 20261002_server_attestations.sql.
--
-- IF NOT EXISTS makes a second run a no-op, so the file is safe to re-apply.
-- ===================================================

ALTER TYPE admin_audit_action ADD VALUE IF NOT EXISTS 'PROFILE_PHOTO_UPLOADED';
ALTER TYPE admin_audit_action ADD VALUE IF NOT EXISTS 'PROFILE_PHOTO_DELETED';
ALTER TYPE admin_audit_action ADD VALUE IF NOT EXISTS 'ATTESTATION_UPLOADED';
ALTER TYPE admin_audit_action ADD VALUE IF NOT EXISTS 'ATTESTATION_VERIFIED';
ALTER TYPE admin_audit_action ADD VALUE IF NOT EXISTS 'ATTESTATION_REJECTED';
ALTER TYPE admin_audit_action ADD VALUE IF NOT EXISTS 'ATTESTATION_SUPERSEDED';
