-- ===================================================
-- Le Seizième - Test Data (10 fictional servers)
-- ===================================================
-- This file creates test data for algorithm testing.
-- It is separate from database/seed.sql to keep
-- reference data clean.
-- ===================================================

BEGIN;

-- ===================================================
-- SERVERS (10 total: 6 male, 4 female)
-- ===================================================

INSERT INTO servers (id, first_name, last_name, phone, email, gender, city_id, years_experience, is_active) VALUES
-- 1. Jean Dupont - MALE - Tunis - 12 years - HARD_WORKER - Food expert (Scenarios 1, 3, 5)
('10000001-0001-0001-0001-000000000001', 'Jean', 'Dupont', '+33601020304', 'jean.dupont@example.com', 'MALE', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 12, TRUE),

-- 2. Marie Leroy - FEMALE - Ariana - 8 years - BALANCED - Barman/Cocktail (Scenario 2)
('10000002-0001-0001-0001-000000000002', 'Marie', 'Leroy', '+33605060708', 'marie.leroy@example.com', 'FEMALE', 'b2c3d4e5-f6a7-8901-bcde-fa2345678901', 8, TRUE),

-- 3. Thomas Martin - MALE - La Marsa - 3 years - SOFT_WORKER - Beginner (Scenario 6 - car, refuses coworkers)
('10000003-0001-0001-0001-000000000003', 'Thomas', 'Martin', '+33609101112', 'thomas.martin@example.com', 'MALE', 'c3d4e5f6-a7b8-9012-cdef-ab3456789012', 3, TRUE),

-- 4. Sophie Bernard - FEMALE - Monastir - 10 years - HARD_WORKER - Maître d'hôtel (Scenario 9 - excellent but far)
('10000004-0001-0001-0001-000000000004', 'Sophie', 'Bernard', '+33613141516', 'sophie.bernard@example.com', 'FEMALE', 'c9d0e1f2-a3b4-5678-cdef-ab9012345678', 10, TRUE),

-- 5. Ahmed Benali - MALE - Manouba - 1 year - BALANCED - Beginner (Scenario 10 - close and available)
('10000005-0001-0001-0001-000000000005', 'Ahmed', 'Benali', '+33617181920', 'ahmed.benali@example.com', 'MALE', 'e5f6a7b8-c9d0-1234-efab-cd5678901234', 1, TRUE),

-- 6. Camille Petit - FEMALE - Ben Arous - 6 years - HARD_WORKER - Team Leader
('10000006-0001-0001-0001-000000000006', 'Camille', 'Petit', '+33621222324', 'camille.petit@example.com', 'FEMALE', 'd4e5f6a7-b8c9-0123-defa-bc4567890123', 6, TRUE),

-- 7. Lucas Moreau - MALE - Sousse - 11 years - SOFT_WORKER - Manager (Scenario 7 - unavailable)
('10000007-0001-0001-0001-000000000007', 'Lucas', 'Moreau', '+33625262728', 'lucas.moreau@example.com', 'MALE', 'b8c9d0e1-f2a3-4567-bcde-fa8901234567', 11, TRUE),

-- 8. Emma Roux - FEMALE - Nabeul - 4 years - BALANCED - Barman/Bar (Scenario 8 - limited availability)
('10000008-0001-0001-0001-000000000008', 'Emma', 'Roux', '+33629303132', 'emma.roux@example.com', 'FEMALE', 'f6a7b8c9-d0e1-2345-fabc-de6789012345', 4, TRUE),

-- 9. Hugo Girard - MALE - Hammamet - 7 years - HARD_WORKER - Food/Mise en place (Scenario 5 - car, refuses coworkers)
('10000009-0001-0001-0001-000000000009', 'Hugo', 'Girard', '+33633343536', 'hugo.girard@example.com', 'MALE', 'a7b8c9d0-e1f2-3456-abcd-ef7890123456', 7, TRUE),

-- 10. Leo Mercier - MALE - Bizerte - 2 years - SOFT_WORKER - Beginner (Scenario 8 - limited availability)
('10000010-0001-0001-0001-000000000010', 'Leo', 'Mercier', '+33637383940', 'leo.mercier@example.com', 'MALE', 'd0e1f2a3-b4c5-6789-defa-bc0123456789', 2, TRUE);


-- ===================================================
-- SERVER_PROFILES (10 entries)
-- ===================================================

INSERT INTO server_profile (server_id, speed_score, punctuality_score, presentation_score, communication_score, teamwork_score, discipline_score, endurance_score, worker_type) VALUES
-- 1. Jean - HARD_WORKER - excellent but not perfect
('10000001-0001-0001-0001-000000000001', 9, 8, 9, 7, 8, 8, 9, 'HARD_WORKER'),

-- 2. Marie - BALANCED - strong communication
('10000002-0001-0001-0001-000000000002', 7, 8, 8, 9, 9, 7, 7, 'BALANCED'),

-- 3. Thomas - SOFT_WORKER - developing
('10000003-0001-0001-0001-000000000003', 6, 5, 6, 6, 5, 5, 6, 'SOFT_WORKER'),

-- 4. Sophie - HARD_WORKER - excellent presentation (Scenario 9)
('10000004-0001-0001-0001-000000000004', 8, 9, 10, 8, 8, 9, 8, 'HARD_WORKER'),

-- 5. Ahmed - BALANCED - beginner but promising (Scenario 10)
('10000005-0001-0001-0001-000000000005', 5, 6, 5, 5, 5, 6, 5, 'BALANCED'),

-- 6. Camille - HARD_WORKER - strong teamwork
('10000006-0001-0001-0001-000000000006', 8, 7, 8, 8, 9, 7, 8, 'HARD_WORKER'),

-- 7. Lucas - SOFT_WORKER - experienced but relaxed (Scenario 7)
('10000007-0001-0001-0001-000000000007', 7, 8, 7, 9, 7, 8, 6, 'SOFT_WORKER'),

-- 8. Emma - BALANCED - steady performer
('10000008-0001-0001-0001-000000000008', 6, 7, 7, 7, 7, 6, 6, 'BALANCED'),

-- 9. Hugo - HARD_WORKER - strong endurance (Scenario 5)
('10000009-0001-0001-0001-000000000009', 8, 7, 8, 6, 8, 8, 9, 'HARD_WORKER'),

-- 10. Leo - SOFT_WORKER - junior, learning (Scenario 8)
('10000010-0001-0001-0001-000000000010', 4, 5, 5, 4, 4, 5, 4, 'SOFT_WORKER');


-- ===================================================
-- SERVER_LOCATIONS (11 total: 10 current + 2 historical)
-- ===================================================

-- Current locations (all verified)
INSERT INTO server_locations (server_id, city_id, area, latitude, longitude, is_verified, verified_at, is_current) VALUES
-- 1. Jean - Tunis Centre (current)
('10000001-0001-0001-0001-000000000001', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Tunis Centre', 36.8065, 10.1815, TRUE, '2026-07-15 10:30:00', TRUE),

-- 2. Marie - Ariana Centre (current)
('10000002-0001-0001-0001-000000000002', 'b2c3d4e5-f6a7-8901-bcde-fa2345678901', 'Ariana Centre', 36.8601, 10.1634, TRUE, '2026-07-20 14:00:00', TRUE),

-- 3. Thomas - La Marsa (current)
('10000003-0001-0001-0001-000000000003', 'c3d4e5f6-a7b8-9012-cdef-ab3456789012', 'La Marsa', 36.8781, 10.3246, TRUE, '2026-08-01 09:15:00', TRUE),

-- 4. Sophie - Monastir Centre (current)
('10000004-0001-0001-0001-000000000004', 'c9d0e1f2-a3b4-5678-cdef-ab9012345678', 'Monastir Centre', 35.7643, 10.8158, TRUE, '2026-07-10 11:45:00', TRUE),

-- 5. Ahmed - Manouba Centre (current)
('10000005-0001-0001-0001-000000000005', 'e5f6a7b8-c9d0-1234-efab-cd5678901234', 'Manouba Centre', 36.8080, 10.0875, TRUE, '2026-08-05 16:20:00', TRUE),

-- 6. Camille - Ben Arous Centre (current)
('10000006-0001-0001-0001-000000000006', 'd4e5f6a7-b8c9-0123-defa-bc4567890123', 'Ben Arous Centre', 36.7424, 10.2186, TRUE, '2026-07-25 13:10:00', TRUE),

-- 7. Lucas - Sousse Centre (current)
('10000007-0001-0001-0001-000000000007', 'b8c9d0e1-f2a3-4567-bcde-fa8901234567', 'Sousse Centre', 35.8256, 10.5856, TRUE, '2026-08-02 10:00:00', TRUE),

-- 8. Emma - Nabeul Centre (current)
('10000008-0001-0001-0001-000000000008', 'f6a7b8c9-d0e1-2345-fabc-de6789012345', 'Nabeul Centre', 36.4519, 10.7353, TRUE, '2026-07-18 15:30:00', TRUE),

-- 9. Hugo - Hammamet Centre (current)
('10000009-0001-0001-0001-000000000009', 'a7b8c9d0-e1f2-3456-abcd-ef7890123456', 'Hammamet Centre', 36.3969, 10.6143, TRUE, '2026-07-22 12:00:00', TRUE),

-- 10. Leo - Bizerte Centre (current)
('10000010-0001-0001-0001-000000000010', 'd0e1f2a3-b4c5-6789-defa-bc0123456789', 'Bizerte Centre', 37.2744, 9.8739, TRUE, '2026-08-08 09:45:00', TRUE);

-- Historical locations for Jean (Tunis -> Ariana)
INSERT INTO server_locations (server_id, city_id, area, latitude, longitude, is_verified, verified_at, is_current) VALUES
('10000001-0001-0001-0001-000000000001', 'b2c3d4e5-f6a7-8901-bcde-fa2345678901', 'Ariana Nord', 36.8675, 10.1750, TRUE, '2025-06-01 10:00:00', FALSE);

-- Historical location for Sophie (Monastir -> Tunis, then moved back)
INSERT INTO server_locations (server_id, city_id, area, latitude, longitude, is_verified, verified_at, is_current) VALUES
('10000004-0001-0001-0001-000000000004', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Tunis Lac', 36.8450, 10.2350, TRUE, '2025-09-15 14:30:00', FALSE);


-- ===================================================
-- SERVER_SKILLS (all 10 servers with realistic combinations)
-- ===================================================

INSERT INTO server_skills (server_id, skill_id, level, years_experience) VALUES
-- 1. Jean - Food expert
('10000001-0001-0001-0001-000000000001', '11111111-1111-1111-1111-111111111111', 10, 8),
('10000001-0001-0001-0001-000000000001', '22222222-2222-2222-2222-222222222222', 9, 7),
('10000001-0001-0001-0001-000000000001', '33333333-3333-3333-3333-333333333333', 9, 6),
('10000001-0001-0001-0001-000000000001', '77777777-7777-7777-7777-777777777777', 8, 5),

-- 2. Marie - Barman/Cocktail
('10000002-0001-0001-0001-000000000002', '44444444-4444-4444-4444-444444444444', 10, 6),
('10000002-0001-0001-0001-000000000002', '66666666-6666-6666-6666-666666666666', 10, 5),
('10000002-0001-0001-0001-000000000002', '55555555-5555-5555-5555-555555555555', 9, 4),
('10000002-0001-0001-0001-000000000002', '22222222-2222-2222-2222-222222222222', 7, 3),

-- 3. Thomas - Beginner
('10000003-0001-0001-0001-000000000003', '11111111-1111-1111-1111-111111111111', 6, 2),
('10000003-0001-0001-0001-000000000003', '22222222-2222-2222-2222-222222222222', 5, 1),
('10000003-0001-0001-0001-000000000003', '33333333-3333-3333-3333-333333333333', 5, 1),
('10000003-0001-0001-0001-000000000003', '77777777-7777-7777-7777-777777777777', 4, 1),

-- 4. Sophie - Maître d'hôtel
('10000004-0001-0001-0001-000000000004', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 10, 8),
('10000004-0001-0001-0001-000000000004', '22222222-2222-2222-2222-222222222222', 9, 7),
('10000004-0001-0001-0001-000000000004', '11111111-1111-1111-1111-111111111111', 7, 5),
('10000004-0001-0001-0001-000000000004', '99999999-9999-9999-9999-999999999999', 8, 4),

-- 5. Ahmed - Beginner
('10000005-0001-0001-0001-000000000005', '11111111-1111-1111-1111-111111111111', 5, 1),
('10000005-0001-0001-0001-000000000005', '33333333-3333-3333-3333-333333333333', 6, 1),
('10000005-0001-0001-0001-000000000005', '77777777-7777-7777-7777-777777777777', 5, 1),
('10000005-0001-0001-0001-000000000005', '88888888-8888-8888-8888-888888888888', 5, 1),

-- 6. Camille - Team Leader
('10000006-0001-0001-0001-000000000006', '22222222-2222-2222-2222-222222222222', 9, 5),
('10000006-0001-0001-0001-000000000006', '99999999-9999-9999-9999-999999999999', 8, 4),
('10000006-0001-0001-0001-000000000006', '77777777-7777-7777-7777-777777777777', 7, 4),
('10000006-0001-0001-0001-000000000006', '11111111-1111-1111-1111-111111111111', 7, 3),

-- 7. Lucas - Manager
('10000007-0001-0001-0001-000000000007', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 10, 10),
('10000007-0001-0001-0001-000000000007', '66666666-6666-6666-6666-666666666666', 8, 4),
('10000007-0001-0001-0001-000000000007', '55555555-5555-5555-5555-555555555555', 7, 3),
('10000007-0001-0001-0001-000000000007', '11111111-1111-1111-1111-111111111111', 6, 2),

-- 8. Emma - Barman/Bar
('10000008-0001-0001-0001-000000000008', '44444444-4444-4444-4444-444444444444', 8, 3),
('10000008-0001-0001-0001-000000000008', '55555555-5555-5555-5555-555555555555', 9, 3),
('10000008-0001-0001-0001-000000000008', '66666666-6666-6666-6666-666666666666', 7, 2),
('10000008-0001-0001-0001-000000000008', '22222222-2222-2222-2222-222222222222', 6, 2),

-- 9. Hugo - Food/Mise en place
('10000009-0001-0001-0001-000000000009', '11111111-1111-1111-1111-111111111111', 9, 6),
('10000009-0001-0001-0001-000000000009', '77777777-7777-7777-7777-777777777777', 8, 5),
('10000009-0001-0001-0001-000000000009', '88888888-8888-8888-8888-888888888888', 7, 4),
('10000009-0001-0001-0001-000000000009', '33333333-3333-3333-3333-333333333333', 7, 3),

-- 10. Leo - Beginner
('10000010-0001-0001-0001-000000000010', '22222222-2222-2222-2222-222222222222', 4, 1),
('10000010-0001-0001-0001-000000000010', '33333333-3333-3333-3333-333333333333', 5, 1),
('10000010-0001-0001-0001-000000000010', '11111111-1111-1111-1111-111111111111', 5, 1),
('10000010-0001-0001-0001-000000000010', '88888888-8888-8888-8888-888888888888', 4, 1);


-- ===================================================
-- VEHICLES (5 vehicles for 5 servers)
-- ===================================================

INSERT INTO vehicles (id, owner_server_id, vehicle_type, brand, model, seats_total, can_transport_coworkers, is_active) VALUES
-- 1. Jean - Car - transports coworkers (Scenario 5)
('20000001-0001-0001-0001-000000000001', '10000001-0001-0001-0001-000000000001', 'CAR', 'Toyota', 'Corolla', 4, TRUE, TRUE),

-- 2. Thomas - Car - refuses coworkers (Scenario 6)
('20000002-0001-0001-0001-000000000002', '10000003-0001-0001-0001-000000000003', 'CAR', 'Peugeot', '208', 4, FALSE, TRUE),

-- 3. Ahmed - Car - transports coworkers
('20000003-0001-0001-0001-000000000003', '10000005-0001-0001-0001-000000000005', 'CAR', 'Renault', 'Clio', 4, TRUE, TRUE),

-- 4. Lucas - Van - transports coworkers
('20000004-0001-0001-0001-000000000004', '10000007-0001-0001-0001-000000000007', 'VAN', 'Renault', 'Traffic', 5, TRUE, TRUE),

-- 5. Hugo - Car - refuses coworkers (Scenario 5)
('20000005-0001-0001-0001-000000000005', '10000009-0001-0001-0001-000000000009', 'CAR', 'BMW', 'Serie 3', 4, FALSE, TRUE);


-- ===================================================
-- VEHICLE_AVAILABILITY
-- ===================================================

INSERT INTO vehicle_availability (vehicle_id, start_datetime, end_datetime, available) VALUES
-- 1. Jean's vehicle - available
('20000001-0001-0001-0001-000000000001', '2026-08-15 00:00:00', '2026-12-31 23:59:59', TRUE),

-- 2. Thomas's vehicle - available
('20000002-0001-0001-0001-000000000002', '2026-08-15 00:00:00', '2026-12-31 23:59:59', TRUE),

-- 3. Ahmed's vehicle - available
('20000003-0001-0001-0001-000000000003', '2026-08-15 00:00:00', '2026-12-31 23:59:59', TRUE),

-- 4. Lucas's vehicle - available
('20000004-0001-0001-0001-000000000004', '2026-08-15 00:00:00', '2026-12-31 23:59:59', TRUE),

-- 5. Hugo's vehicle - UNAVAILABLE during 2026-12-01 to 2026-12-05 (for future test)
('20000005-0001-0001-0001-000000000005', '2026-08-15 00:00:00', '2026-11-30 23:59:59', TRUE),
('20000005-0001-0001-0001-000000000005', '2026-12-01 00:00:00', '2026-12-05 23:59:59', FALSE),
('20000005-0001-0001-0001-000000000005', '2026-12-06 00:00:00', '2026-12-31 23:59:59', TRUE);


-- ===================================================
-- SERVER_AVAILABILITY (non-overlapping intervals per server)
-- ===================================================

-- 1. Jean - fully available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000001-0001-0001-0001-000000000001', '2026-08-15 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 2. Marie - fully available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000002-0001-0001-0001-000000000002', '2026-08-15 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 3. Thomas - fully available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000003-0001-0001-0001-000000000003', '2026-08-15 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 4. Sophie - fully available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000004-0001-0001-0001-000000000004', '2026-08-15 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 5. Ahmed - limited availability (non-overlapping intervals)
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000005-0001-0001-0001-000000000005', '2026-08-15 00:00:00', '2026-08-25 23:59:59', 'AVAILABLE'),
('10000005-0001-0001-0001-000000000005', '2026-08-26 00:00:00', '2026-09-05 23:59:59', 'UNAVAILABLE'),
('10000005-0001-0001-0001-000000000005', '2026-09-06 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 6. Camille - fully available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000006-0001-0001-0001-000000000006', '2026-08-15 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 7. Lucas - unavailable first 15 days, then available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000007-0001-0001-0001-000000000007', '2026-08-15 00:00:00', '2026-08-30 23:59:59', 'UNAVAILABLE'),
('10000007-0001-0001-0001-000000000007', '2026-08-31 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 8. Emma - limited availability (alternating pattern)
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000008-0001-0001-0001-000000000008', '2026-08-15 00:00:00', '2026-08-18 23:59:59', 'AVAILABLE'),
('10000008-0001-0001-0001-000000000008', '2026-08-19 00:00:00', '2026-08-25 23:59:59', 'UNAVAILABLE'),
('10000008-0001-0001-0001-000000000008', '2026-08-26 00:00:00', '2026-09-01 23:59:59', 'AVAILABLE'),
('10000008-0001-0001-0001-000000000008', '2026-09-02 00:00:00', '2026-09-08 23:59:59', 'UNAVAILABLE'),
('10000008-0001-0001-0001-000000000008', '2026-09-09 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 9. Hugo - fully available
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000009-0001-0001-0001-000000000009', '2026-08-15 00:00:00', '2026-09-15 23:59:59', 'AVAILABLE');

-- 10. Leo - limited availability (alternating pattern)
INSERT INTO server_availability (server_id, start_datetime, end_datetime, status) VALUES
('10000010-0001-0001-0001-000000000010', '2026-08-15 00:00:00', '2026-08-17 23:59:59', 'AVAILABLE'),
('10000010-0001-0001-0001-000000000010', '2026-08-18 00:00:00', '2026-08-20 23:59:59', 'UNAVAILABLE'),
('10000010-0001-0001-0001-000000000010', '2026-08-21 00:00:00', '2026-08-23 23:59:59', 'AVAILABLE'),
('10000010-0001-0001-0001-000000000010', '2026-08-24 00:00:00', '2026-09-15 23:59:59', 'UNAVAILABLE');


-- ===================================================
-- VERIFICATION QUERIES
-- ===================================================

-- Verify server count and gender distribution
SELECT 
    count(*) AS total_servers,
    count(CASE WHEN gender = 'MALE' THEN 1 END) AS male_count,
    count(CASE WHEN gender = 'FEMALE' THEN 1 END) AS female_count
FROM servers;

-- Verify all required fields are populated
SELECT 
    count(*) AS servers_with_profile,
    count(*) AS servers_with_location,
    count(*) AS servers_with_skills
FROM servers s
JOIN server_profile sp ON s.id = sp.server_id
JOIN server_locations sl ON s.id = sl.server_id AND sl.is_current = TRUE
JOIN server_skills ss ON s.id = ss.server_id;

-- Verify exactly 10 current locations
SELECT count(*) AS current_locations FROM server_locations WHERE is_current = TRUE;

-- Verify historical locations exist for at least 2 servers
SELECT count(DISTINCT server_id) AS servers_with_history FROM server_locations WHERE is_current = FALSE;

-- Verify exactly one current location per server
SELECT server_id, count(*) FROM server_locations WHERE is_current = TRUE GROUP BY server_id HAVING count(*) > 1;

-- Verify no overlapping availability per server
SELECT sa1.server_id, sa1.start_datetime, sa1.end_datetime, sa2.start_datetime, sa2.end_datetime
FROM server_availability sa1
JOIN server_availability sa2 ON sa1.server_id = sa2.server_id
WHERE sa1.id < sa2.id
AND tsrange(sa1.start_datetime, sa1.end_datetime) && tsrange(sa2.start_datetime, sa2.end_datetime);

-- Verify vehicle count
SELECT count(*) AS vehicle_count FROM vehicles;

-- Verify vehicle ownership distribution
SELECT 
    count(DISTINCT owner_server_id) AS servers_with_vehicle,
    count(*) AS total_vehicles
FROM vehicles;

-- Verify can_transport_coworkers distribution
SELECT 
    count(CASE WHEN can_transport_coworkers = TRUE THEN 1 END) AS transports_coworkers,
    count(CASE WHEN can_transport_coworkers = FALSE THEN 1 END) AS refuses_coworkers
FROM vehicles;

-- Verify skills distribution per server
SELECT s.id, s.first_name, s.last_name, count(ss.skill_id) AS skill_count
FROM servers s
JOIN server_skills ss ON s.id = ss.server_id
GROUP BY s.id, s.first_name, s.last_name
ORDER BY s.id;

-- Verify all referenced skill IDs exist
SELECT ss.server_id, ss.skill_id
FROM server_skills ss
LEFT JOIN skills sk ON ss.skill_id = sk.id
WHERE sk.id IS NULL;

-- Verify all referenced city IDs exist
SELECT s.id, s.city_id
FROM servers s
LEFT JOIN cities c ON s.city_id = c.id
WHERE c.id IS NULL;

-- Verify GPS ranges for all locations
SELECT 'server_locations' AS source, count(*) AS invalid_count
FROM server_locations
WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180;

-- Verify all server profiles have valid scores
SELECT 'server_profile_speed' AS field, count(*) AS invalid_count FROM server_profile WHERE speed_score NOT BETWEEN 1 AND 10
UNION ALL
SELECT 'server_profile_punctuality', count(*) FROM server_profile WHERE punctuality_score NOT BETWEEN 1 AND 10
UNION ALL
SELECT 'server_profile_presentation', count(*) FROM server_profile WHERE presentation_score NOT BETWEEN 1 AND 10
UNION ALL
SELECT 'server_profile_communication', count(*) FROM server_profile WHERE communication_score NOT BETWEEN 1 AND 10
UNION ALL
SELECT 'server_profile_teamwork', count(*) FROM server_profile WHERE teamwork_score NOT BETWEEN 1 AND 10
UNION ALL
SELECT 'server_profile_discipline', count(*) FROM server_profile WHERE discipline_score NOT BETWEEN 1 AND 10
UNION ALL
SELECT 'server_profile_endurance', count(*) FROM server_profile WHERE endurance_score NOT BETWEEN 1 AND 10;

-- Verify worker_type distribution
SELECT worker_type, count(*) AS count
FROM server_profile
GROUP BY worker_type;

-- Verify experience range
SELECT min(years_experience) AS min_exp, max(years_experience) AS max_exp
FROM servers;

-- Verify cities used
SELECT c.name, count(s.id) AS server_count
FROM cities c
JOIN servers s ON c.id = s.city_id
GROUP BY c.name
ORDER BY c.name;

-- Verify availability status distribution
SELECT status, count(*) AS count
FROM server_availability
GROUP BY status
ORDER BY status;

-- Final summary
SELECT 
    'TEST DATA SUMMARY' AS section,
    count(DISTINCT s.id) AS servers,
    count(DISTINCT sl.id) AS current_locations,
    count(DISTINCT CASE WHEN sl.is_current = FALSE THEN sl.server_id END) AS servers_with_history,
    count(DISTINCT v.id) AS vehicles,
    count(DISTINCT ss.server_id) AS servers_with_skills,
    count(DISTINCT sa.server_id) AS servers_with_availability
FROM servers s
LEFT JOIN server_locations sl ON s.id = sl.server_id
LEFT JOIN vehicles v ON s.id = v.owner_server_id
LEFT JOIN server_skills ss ON s.id = ss.server_id
LEFT JOIN server_availability sa ON s.id = sa.server_id;

COMMIT;
