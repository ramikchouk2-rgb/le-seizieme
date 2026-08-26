-- ===================================================
-- Le Seizième - Urgent Event Test Data
-- ===================================================
-- Creates an urgent event for testing the urgent offer engine
-- ===================================================

BEGIN;

-- ===================================================
-- URGENT EVENT
-- ===================================================

INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type, alcohol_service, food_products_count, priority, is_urgent, urgent_created_at, required_response_minutes, status, notes)
VALUES (
    '40000001-0001-0001-0001-000000000001',
    'Soiree Urgente Derniere Minute -- Test',
    'Client Urgent Test',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Tunis Centre, Rue de la Kasbah',
    '2026-08-20 19:00:00',
    '2026-08-21 01:00:00',
    200,
    'CORPORATE',
    TRUE,
    8,
    'URGENT',
    TRUE,
    '2026-08-15 12:00:00',
    30,
    'STAFFING',
    'Evenement urgent pour test du moteur d''offres'
);

-- ===================================================
-- EVENT REQUIREMENTS
-- ===================================================

INSERT INTO event_requirements (event_id, role_name, quantity, required_gender, minimum_experience, minimum_skill_level, notes) VALUES
('40000001-0001-0001-0001-000000000001', 'Food', 8, 'MALE', 2, 5, 'Service salle et buffet'),
('40000001-0001-0001-0001-000000000001', 'Food', 3, 'FEMALE', 1, 4, 'Service cocktail'),
('40000001-0001-0001-0001-000000000001', 'Barman', 1, NULL, 3, 6, 'Bar principal');

-- ===================================================
-- VERIFICATION
-- ===================================================

SELECT 
    e.id AS event_id,
    e.name,
    e.is_urgent,
    e.priority,
    e.status,
    count(er.id) AS requirements_count,
    sum(er.quantity) AS total_required
FROM events e
JOIN event_requirements er ON e.id = er.event_id
WHERE e.id = '40000001-0001-0001-0001-000000000001'
GROUP BY e.id, e.name, e.is_urgent, e.priority, e.status;

COMMIT;
