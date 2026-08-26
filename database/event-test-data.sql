-- ===================================================
-- Le Seizième - Event Test Data
-- ===================================================
-- Creates the first test event with requirements
-- ===================================================

BEGIN;

-- ===================================================
-- EVENT
-- ===================================================

INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type, alcohol_service, food_products_count, priority, is_urgent, status, notes)
VALUES (
    '30000001-0001-0001-0001-000000000001',
    'Grande Soirée Jeunes -- Test',
    'Client Test',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Tunis Centre, Avenue Habib Bourguiba',
    '2026-09-20 18:00:00',
    '2026-09-21 02:00:00',
    400,
    'WEDDING',
    TRUE,
    12,
    'NORMAL',
    FALSE,
    'PLANNED',
    'Premier evenement de test pour validation du schema'
);

-- ===================================================
-- EVENT_REQUIREMENTS (5 requirements, total = 14)
-- ===================================================

INSERT INTO event_requirements (event_id, role_name, quantity, required_gender, minimum_experience, minimum_skill_level, notes) VALUES
-- 1. FOOD - 8 male servers
('30000001-0001-0001-0001-000000000001', 'Food', 8, 'MALE', 2, 5, 'Service salle et buffet principal'),

-- 2. FOOD - 3 female servers
('30000001-0001-0001-0001-000000000001', 'Food', 3, 'FEMALE', 1, 4, 'Service cocktail et mise en place'),

-- 3. BARMAN - 1 server, any gender
('30000001-0001-0001-0001-000000000001', 'Barman', 1, NULL, 3, 6, 'Bar principal'),

-- 4. MAITRE D'HOTEL - 1 server, any gender
('30000001-0001-0001-0001-000000000001', 'Maitre d''hotel', 1, NULL, 5, 8, 'Accueil et supervision salle'),

-- 5. MANAGER - 1 server, any gender
('30000001-0001-0001-0001-000000000001', 'Manager', 1, NULL, 8, 9, 'Pilotage global de l''evenement');


-- ===================================================
-- VERIFICATION QUERIES
-- ===================================================

-- Verify exactly 1 event created
SELECT count(*) AS event_count FROM events WHERE id = '30000001-0001-0001-0001-000000000001';

-- Verify event details
SELECT 
    id,
    name,
    client_name,
    city_id,
    address,
    start_datetime,
    end_datetime,
    guest_count,
    event_type,
    alcohol_service,
    food_products_count,
    priority,
    is_urgent,
    status,
    notes
FROM events
WHERE id = '30000001-0001-0001-0001-000000000001';

-- Verify event is in Tunis
SELECT c.name AS city_name
FROM events e
JOIN cities c ON e.city_id = c.id
WHERE e.id = '30000001-0001-0001-0001-000000000001';

-- Verify exactly 5 event requirements
SELECT count(*) AS requirement_count FROM event_requirements WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify each requirement
SELECT 
    role_name,
    quantity,
    required_gender,
    minimum_experience,
    minimum_skill_level
FROM event_requirements
WHERE event_id = '30000001-0001-0001-0001-000000000001'
ORDER BY role_name, required_gender;

-- Verify total required quantity = 14
SELECT sum(quantity) AS total_quantity FROM event_requirements WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify gender breakdown for FOOD
SELECT 
    count(CASE WHEN role_name = 'Food' AND required_gender = 'MALE' THEN 1 END) AS food_male_requirements,
    count(CASE WHEN role_name = 'Food' AND required_gender = 'FEMALE' THEN 1 END) AS food_female_requirements,
    count(CASE WHEN role_name = 'Barman' THEN 1 END) AS barman_requirements,
    count(CASE WHEN role_name = 'Maitre d''hotel' THEN 1 END) AS maitre_requirements,
    count(CASE WHEN role_name = 'Manager' THEN 1 END) AS manager_requirements
FROM event_requirements
WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify event is not urgent
SELECT is_urgent FROM events WHERE id = '30000001-0001-0001-0001-000000000001';

-- Verify end_datetime > start_datetime
SELECT 
    start_datetime,
    end_datetime,
    CASE WHEN end_datetime > start_datetime THEN 'VALID' ELSE 'INVALID' END AS date_check
FROM events
WHERE id = '30000001-0001-0001-0001-000000000001';

-- Verify no servers assigned yet
SELECT count(*) AS assigned_servers FROM event_staff WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify no transport groups created
SELECT count(*) AS transport_groups FROM transport_groups WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify no urgent offers created
SELECT count(*) AS urgent_offers FROM urgent_event_offers WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify no point transactions created
SELECT count(*) AS point_transactions FROM point_transactions WHERE event_id = '30000001-0001-0001-0001-000000000001';

-- Verify no evaluations created
SELECT count(*) AS evaluations FROM evaluations WHERE event_id = '30000001-0001-0001-0001-000000000001';

COMMIT;
