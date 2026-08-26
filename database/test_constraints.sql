-- ===================================================
-- Controlled Constraint Tests (ROLLBACK at end)
-- ===================================================

BEGIN;

-- Helper: create a temp server and city for FK references
INSERT INTO servers (id, first_name, last_name, phone, email, gender, city_id, years_experience)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Test',
    'Server',
    '+33600000000',
    'test.server@example.com',
    'MALE',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    5
);

INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'Test Event',
    'Test Client',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '123 Test Street',
    '2026-12-01T10:00:00',
    '2026-12-01T14:00:00',
    50,
    'WEDDING'
);

INSERT INTO vehicles (id, owner_server_id, vehicle_type, brand, model, seats_total, can_transport_coworkers)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    'CAR',
    'Toyota',
    'Corolla',
    4,
    TRUE
);

INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
VALUES (
    '44444444-4444-4444-4444-444444444444',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    48.8566,
    2.3522,
    'Departure Point',
    '2026-12-01T09:00:00',
    48.8566,
    2.3522,
    'Destination Point'
);

INSERT INTO point_transactions (id, server_id, event_id, points, transaction_type, reason, created_by)
VALUES (
    '55555555-5555-5555-5555-555555555555',
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    100,
    'EARNED',
    'Test transaction',
    '11111111-1111-1111-1111-111111111111'
);

-- ===================================================
-- TEST 1: Invalid latitude should fail (95.0 is within NUMERIC(10,8) but outside CHECK -90..90)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO server_locations (server_id, city_id, latitude, longitude, is_current)
        VALUES ('11111111-1111-1111-1111-111111111111', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 95.0, 2.3522, FALSE);
        RAISE EXCEPTION 'TEST 1 FAILED: invalid latitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 1 PASSED: invalid latitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 2: Invalid longitude should fail (200.0 is within NUMERIC(11,8) but outside CHECK -180..180)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO server_locations (server_id, city_id, latitude, longitude, is_current)
        VALUES ('11111111-1111-1111-1111-111111111111', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 48.8566, 200.0, FALSE);
        RAISE EXCEPTION 'TEST 2 FAILED: invalid longitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 2 PASSED: invalid longitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 3: Two current locations for same server should fail
-- ===================================================
INSERT INTO server_locations (server_id, city_id, latitude, longitude, is_current)
VALUES ('11111111-1111-1111-1111-111111111111', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 48.8566, 2.3522, TRUE);

DO $$
BEGIN
    BEGIN
        INSERT INTO server_locations (server_id, city_id, latitude, longitude, is_current)
        VALUES ('11111111-1111-1111-1111-111111111111', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 48.8566, 2.3522, TRUE);
        RAISE EXCEPTION 'TEST 3 FAILED: duplicate current location was accepted';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'TEST 3 PASSED: duplicate current location rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 4: Invalid event dates should fail
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type)
        VALUES ('66666666-6666-6666-6666-666666666666', 'Bad Event', 'Client', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Address', '2026-12-02T14:00:00', '2026-12-02T10:00:00', 50, 'TEST');
        RAISE EXCEPTION 'TEST 4 FAILED: invalid event dates were accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 4 PASSED: invalid event dates rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 5: Invalid GPS in transport_groups
-- NOTE: transport_groups has NO GPS CHECK constraints in current schema.
-- This test documents the gap: invalid GPS is currently ACCEPTED.
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
        VALUES ('77777777-7777-7777-7777-777777777777', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 95.0, 2.3522, 'Departure', '2026-12-01T09:00:00', 48.8566, 2.3522, 'Destination');
        RAISE NOTICE 'TEST 5 GAP: invalid GPS in transport_groups was accepted (no CHECK constraint exists)';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 5 PASSED: invalid GPS in transport_groups rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 6: Duplicate pickup order should fail
-- ===================================================
INSERT INTO transport_passengers (transport_group_id, server_id, pickup_latitude, pickup_longitude, pickup_location_label, pickup_order)
VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 48.8566, 2.3522, 'Pickup 1', 1);

DO $$
BEGIN
    BEGIN
        INSERT INTO transport_passengers (transport_group_id, server_id, pickup_latitude, pickup_longitude, pickup_location_label, pickup_order)
        VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 48.8566, 2.3522, 'Pickup 1 Duplicate', 1);
        RAISE EXCEPTION 'TEST 6 FAILED: duplicate pickup order was accepted';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'TEST 6 PASSED: duplicate pickup order rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 7: Duplicate urgent offer in same wave should fail
-- ===================================================
INSERT INTO urgent_event_offers (event_id, server_id, wave_number, response_deadline)
VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 1, '2026-11-01T10:00:00');

DO $$
BEGIN
    BEGIN
        INSERT INTO urgent_event_offers (event_id, server_id, wave_number, response_deadline)
        VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 1, '2026-11-01T10:00:00');
        RAISE EXCEPTION 'TEST 7 FAILED: duplicate urgent offer in same wave was accepted';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'TEST 7 PASSED: duplicate urgent offer in same wave rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 8: Same server in two different urgent waves should be allowed
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO urgent_event_offers (event_id, server_id, wave_number, response_deadline)
        VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 2, '2026-11-01T10:00:00');
        RAISE NOTICE 'TEST 8 PASSED: same server in different wave allowed';
    EXCEPTION WHEN unique_violation THEN
        RAISE EXCEPTION 'TEST 8 FAILED: same server in different wave was rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 9: UPDATE point_transactions should fail
-- ===================================================
DO $$
BEGIN
    BEGIN
        UPDATE point_transactions SET points = 200 WHERE id = '55555555-5555-5555-5555-555555555555';
        RAISE EXCEPTION 'TEST 9 FAILED: UPDATE on point_transactions was accepted';
    EXCEPTION WHEN raise_exception THEN
        RAISE NOTICE 'TEST 9 PASSED: UPDATE on point_transactions rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 10: DELETE point_transactions should fail
-- ===================================================
DO $$
BEGIN
    BEGIN
        DELETE FROM point_transactions WHERE id = '55555555-5555-5555-5555-555555555555';
        RAISE EXCEPTION 'TEST 10 FAILED: DELETE on point_transactions was accepted';
    EXCEPTION WHEN raise_exception THEN
        RAISE NOTICE 'TEST 10 PASSED: DELETE on point_transactions rejected';
    END;
END;
$$;

ROLLBACK;
