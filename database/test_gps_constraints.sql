-- ===================================================
-- GPS Transport Tables Constraint Tests
-- ===================================================

BEGIN;

-- Setup test data
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

-- ===================================================
-- TEST 1: transport_groups departure latitude = 95 (invalid)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
        VALUES ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 95.0, 2.3522, 'Departure', '2026-12-01T09:00:00', 48.8566, 2.3522, 'Destination');
        RAISE EXCEPTION 'TEST 1 FAILED: invalid departure latitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 1 PASSED: invalid departure latitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 2: transport_groups departure longitude = 200 (invalid)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
        VALUES ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 48.8566, 200.0, 'Departure', '2026-12-01T09:00:00', 48.8566, 2.3522, 'Destination');
        RAISE EXCEPTION 'TEST 2 FAILED: invalid departure longitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 2 PASSED: invalid departure longitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 3: transport_groups destination latitude = -95 (invalid)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
        VALUES ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 48.8566, 2.3522, 'Departure', '2026-12-01T09:00:00', -95.0, 2.3522, 'Destination');
        RAISE EXCEPTION 'TEST 3 FAILED: invalid destination latitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 3 PASSED: invalid destination latitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 4: transport_groups destination longitude = -200 (invalid)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
        VALUES ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 48.8566, 2.3522, 'Departure', '2026-12-01T09:00:00', 48.8566, -200.0, 'Destination');
        RAISE EXCEPTION 'TEST 4 FAILED: invalid destination longitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 4 PASSED: invalid destination longitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 5: Valid transport_groups coordinates should be accepted
-- ===================================================
DO $$
BEGIN
    INSERT INTO transport_groups (id, event_id, vehicle_id, driver_server_id, departure_latitude, departure_longitude, departure_location_label, departure_time, destination_latitude, destination_longitude, destination_label)
    VALUES ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 48.8566, 2.3522, 'Departure', '2026-12-01T09:00:00', 48.8566, 2.3522, 'Destination');
    RAISE NOTICE 'TEST 5 PASSED: valid transport_groups coordinates accepted';
EXCEPTION WHEN others THEN
    RAISE EXCEPTION 'TEST 5 FAILED: valid transport_groups coordinates rejected - %', SQLERRM;
END;
$$;

-- ===================================================
-- TEST 6: transport_passengers pickup latitude = 95 (invalid)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_passengers (transport_group_id, server_id, pickup_latitude, pickup_longitude, pickup_location_label, pickup_order)
        VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 95.0, 2.3522, 'Pickup', 1);
        RAISE EXCEPTION 'TEST 6 FAILED: invalid pickup latitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 6 PASSED: invalid pickup latitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 7: transport_passengers pickup longitude = 200 (invalid)
-- ===================================================
DO $$
BEGIN
    BEGIN
        INSERT INTO transport_passengers (transport_group_id, server_id, pickup_latitude, pickup_longitude, pickup_location_label, pickup_order)
        VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 48.8566, 200.0, 'Pickup', 1);
        RAISE EXCEPTION 'TEST 7 FAILED: invalid pickup longitude was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'TEST 7 PASSED: invalid pickup longitude rejected';
    END;
END;
$$;

-- ===================================================
-- TEST 8: Valid transport_passengers coordinates should be accepted
-- ===================================================
DO $$
BEGIN
    INSERT INTO transport_passengers (transport_group_id, server_id, pickup_latitude, pickup_longitude, pickup_location_label, pickup_order)
    VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 48.8566, 2.3522, 'Pickup', 1);
    RAISE NOTICE 'TEST 8 PASSED: valid transport_passengers coordinates accepted';
EXCEPTION WHEN others THEN
    RAISE EXCEPTION 'TEST 8 FAILED: valid transport_passengers coordinates rejected - %', SQLERRM;
END;
$$;

ROLLBACK;
