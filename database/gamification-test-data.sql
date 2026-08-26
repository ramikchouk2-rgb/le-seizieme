-- ===================================================
-- Le Seizième - Gamification Test Data
-- ===================================================
-- Creates test data for the gamification engine
-- ===================================================

BEGIN;

-- ===================================================
-- COMPLETED EVENT
-- ===================================================

INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type, alcohol_service, food_products_count, priority, is_urgent, status, notes)
VALUES (
    '50000001-0001-0001-0001-000000000001',
    'Mariage Amina -- Test',
    'Client Mariage Test',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Tunis Centre, Rue Habib Bourguiba',
    '2026-08-01 18:00:00',
    '2026-08-02 02:00:00',
    150,
    'WEDDING',
    TRUE,
    6,
    'NORMAL',
    FALSE,
    'COMPLETED',
    'Evenement complete pour test gamification'
);

-- ===================================================
-- EVENT REQUIREMENTS
-- ===================================================

INSERT INTO event_requirements (event_id, role_name, quantity, required_gender, minimum_experience, minimum_skill_level, notes) VALUES
('50000001-0001-0001-0001-000000000001', 'Food', 4, 'MALE', 2, 5, 'Service salle'),
('50000001-0001-0001-0001-000000000001', 'Food', 2, 'FEMALE', 1, 4, 'Service cocktail'),
('50000001-0001-0001-0001-000000000001', 'Barman', 1, NULL, 3, 6, 'Bar principal');

-- ===================================================
-- EVENT STAFF (CONFIRMED)
-- ===================================================

INSERT INTO event_staff (event_id, server_id, role, assignment_status, assigned_at, confirmed_at) VALUES
('50000001-0001-0001-0001-000000000001', '10000001-0001-0001-0001-000000000001', 'Food', 'CONFIRMED', '2026-07-25 10:00:00', '2026-07-25 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000002-0001-0001-0001-000000000002', 'Barman', 'CONFIRMED', '2026-07-25 10:00:00', '2026-07-25 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000003-0001-0001-0001-000000000003', 'Food', 'CONFIRMED', '2026-07-25 10:00:00', '2026-07-25 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000004-0001-0001-0001-000000000004', 'Food', 'CONFIRMED', '2026-07-25 10:00:00', '2026-07-25 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000006-0001-0001-0001-000000000006', 'Food', 'CONFIRMED', '2026-07-25 10:00:00', '2026-07-25 10:00:00');

-- ===================================================
-- EVALUATIONS
-- ===================================================

INSERT INTO evaluations (event_id, server_id, punctuality, work_quality, presentation, teamwork, client_relation, comment, created_at) VALUES
('50000001-0001-0001-0001-000000000001', '10000001-0001-0001-0001-000000000001', 10, 9, 9, 9, 9, 'Excellent travail', '2026-08-03 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000002-0001-0001-0001-000000000002', 10, 10, 10, 9, 10, 'Service impeccable', '2026-08-03 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000003-0001-0001-0001-000000000003', 8, 7, 7, 8, 7, 'Bon travail', '2026-08-03 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000004-0001-0001-0001-000000000004', 9, 9, 10, 9, 9, 'Tres professionnelle', '2026-08-03 10:00:00'),
('50000001-0001-0001-0001-000000000001', '10000006-0001-0001-0001-000000000006', 9, 8, 8, 9, 8, 'Bonne equipe', '2026-08-03 10:00:00');

-- ===================================================
-- BONUS RULES
-- ===================================================

INSERT INTO bonus_rules (name, min_points, max_points, rank_from, rank_to, bonus_amount, active, created_at, updated_at) VALUES
('Top Performer', 500, 9999, 1, 1, 300.00, TRUE, '2026-01-01 00:00:00', '2026-01-01 00:00:00'),
('Excellent', 300, 499, 2, 3, 150.00, TRUE, '2026-01-01 00:00:00', '2026-01-01 00:00:00'),
('Good', 100, 299, 4, 10, 50.00, TRUE, '2026-01-01 00:00:00', '2026-01-01 00:00:00');

-- ===================================================
-- VERIFICATION
-- ===================================================

SELECT 
    e.id AS event_id,
    e.name,
    e.status,
    count(DISTINCT es.id) AS staff_count,
    count(DISTINCT ev.id) AS evaluations_count
FROM events e
LEFT JOIN event_staff es ON e.id = es.event_id
LEFT JOIN evaluations ev ON e.id = ev.event_id
WHERE e.id = '50000001-0001-0001-0001-000000000001'
GROUP BY e.id, e.name, e.status;

COMMIT;
