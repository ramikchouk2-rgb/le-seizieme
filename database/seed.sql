-- ===================================================
-- Le Seizième - Seed Data
-- ===================================================
-- Reference data for cities and skills
-- ===================================================


-- ===================================================
-- CITIES
-- ===================================================

INSERT INTO cities (id, name) VALUES
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Tunis'),
    ('b2c3d4e5-f6a7-8901-bcde-fa2345678901', 'Ariana'),
    ('c3d4e5f6-a7b8-9012-cdef-ab3456789012', 'La Marsa'),
    ('d4e5f6a7-b8c9-0123-defa-bc4567890123', 'Ben Arous'),
    ('e5f6a7b8-c9d0-1234-efab-cd5678901234', 'Manouba'),
    ('f6a7b8c9-d0e1-2345-fabc-de6789012345', 'Nabeul'),
    ('a7b8c9d0-e1f2-3456-abcd-ef7890123456', 'Hammamet'),
    ('b8c9d0e1-f2a3-4567-bcde-fa8901234567', 'Sousse'),
    ('c9d0e1f2-a3b4-5678-cdef-ab9012345678', 'Monastir'),
    ('d0e1f2a3-b4c5-6789-defa-bc0123456789', 'Bizerte');


-- ===================================================
-- SKILLS
-- ===================================================

INSERT INTO skills (id, name, description) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Food', 'Préparation et service des plats'),
    ('22222222-2222-2222-2222-222222222222', 'Service à table', 'Service en salle, prise de commandes et accompagnement'),
    ('33333333-3333-3333-3333-333333333333', 'Buffet', 'Gestion et approvisionnement des buffets'),
    ('44444444-4444-4444-4444-444444444444', 'Barman', 'Préparation de boissons non alcoolisées'),
    ('55555555-5555-5555-5555-555555555555', 'Bar', 'Service au bar, gestion des commandes'),
    ('66666666-6666-6666-6666-666666666666', 'Cocktail', 'Préparation de cocktails et mixologie'),
    ('77777777-7777-7777-7777-777777777777', 'Mise en place', 'Préparation des tables et des espaces de service'),
    ('88888888-8888-8888-8888-888888888888', 'Débarrassage', 'Collecte et nettoyage des plateaux et tables'),
    ('99999999-9999-9999-9999-999999999999', 'Team Leader', 'Coordination d''équipe et supervision'),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Maître d''hôtel', 'Accueil des clients et gestion de la salle'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Manager', 'Pilotage global de l''événement et des équipes');
