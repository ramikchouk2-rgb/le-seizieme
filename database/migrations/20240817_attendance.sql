-- ===================================================
-- EVENT_ATTENDANCE
-- ===================================================

CREATE TYPE attendance_status AS ENUM ('EXPECTED', 'PRESENT', 'LATE', 'ABSENT', 'EXCUSED', 'LEFT');

CREATE TABLE event_attendance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    event_staff_id UUID NOT NULL REFERENCES event_staff(id) ON DELETE CASCADE,
    status attendance_status NOT NULL DEFAULT 'EXPECTED',
    check_in_at TIMESTAMP,
    check_out_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_staff_id),
    CHECK (
        (status IN ('PRESENT', 'LATE') AND check_in_at IS NOT NULL) OR
        (status NOT IN ('PRESENT', 'LATE'))
    ),
    CHECK (
        check_out_at IS NULL OR check_in_at IS NULL OR check_out_at >= check_in_at
    )
);

CREATE INDEX idx_event_attendance_event_id ON event_attendance(event_id);
CREATE INDEX idx_event_attendance_event_staff_id ON event_attendance(event_staff_id);
CREATE INDEX idx_event_attendance_status ON event_attendance(status);
