-- Step 21: Persistent admin audit log
-- Captures all user-management mutations by admin actors for compliance auditing.

DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'admin_audit_action') THEN
      CREATE TYPE admin_audit_action AS ENUM (
         'USER_CREATED',
         'USER_UPDATED',
         'USER_DEACTIVATED'
      );
   END IF;
END $$;

CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_user_id   UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    target_user_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    action          admin_audit_action NOT NULL,
    detail          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_target ON audit_log(target_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);