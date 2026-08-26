# Documentation de la base de données - Le Seizième

## Vue d'ensemble

Base de données PostgreSQL pour la gestion du personnel événementiel.
Architecture relationnelle normalisée pour ~150 serveurs, plusieurs villes et de nombreux événements.

## Tables

### cities
Référentiel des villes.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(100) | Nom unique de la ville |
| created_at | TIMESTAMP | Date de création |

### servers
Serveurs événementiels.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| first_name | VARCHAR(100) | Prénom |
| last_name | VARCHAR(100) | Nom |
| phone | VARCHAR(20) | Téléphone |
| email | VARCHAR(255) | Email unique |
| gender | gender_type | Genre |
| city_id | UUID | Ville de rattachement (FK cities) |
| years_experience | INTEGER | Années d'expérience |
| is_active | BOOLEAN | Compte actif |
| profile_photo | TEXT | Photo de profil |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**IMPORTANT** : L'adresse exacte du domicile n'est pas stockée dans cette table.

### server_locations
Historique des localisations des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur concerné (FK servers) |
| city_id | UUID | Ville (FK cities) |
| area | VARCHAR(255) | Quartier/zone approximative |
| latitude | NUMERIC(10,8) | Latitude GPS |
| longitude | NUMERIC(11,8) | Longitude GPS |
| is_verified | BOOLEAN | Localisation confirmée par le serveur |
| verified_at | TIMESTAMP | Date de confirmation |
| is_current | BOOLEAN | Localisation actuelle |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**Règles** :
- Un serveur peut avoir plusieurs anciennes localisations
- Une seule localisation `is_current = TRUE` par serveur (garanti par trigger)
- Les coordonnées GPS exactes sont considérées comme privées

### skills
Référentiel des compétences.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(100) | Nom unique |
| description | TEXT | Description |
| created_at | TIMESTAMP | Date de création |

**Compétences pré-chargées** :
- Food
- Service à table
- Buffet
- Barman
- Bar
- Cocktail
- Mise en place
- Débarrassage
- Team Leader
- Maître d'hôtel
- Manager

### server_skills
Compétences des serveurs (many-to-many).

| Colonne | Type | Description |
|---------|------|-------------|
| server_id | UUID | Serveur (FK servers) |
| skill_id | UUID | Compétence (FK skills) |
| level | INTEGER | Niveau 1-10 |
| years_experience | INTEGER | Années d'expérience sur cette compétence |

**Clé primaire composite** : (server_id, skill_id)

### server_profile
Profil professionnel et scores.

| Colonne | Type | Description |
|---------|------|-------------|
| server_id | UUID | Serveur (FK servers) |
| speed_score | INTEGER | Rapidité 1-10 |
| punctuality_score | INTEGER | Ponctualité 1-10 |
| presentation_score | INTEGER | Présentation 1-10 |
| communication_score | INTEGER | Communication 1-10 |
| teamwork_score | INTEGER | Esprit d'équipe 1-10 |
| discipline_score | INTEGER | Discipline 1-10 |
| endurance_score | INTEGER | Endurance 1-10 |
| worker_type | worker_type | HARD_WORKER, BALANCED, SOFT_WORKER |

**IMPORTANT** : `worker_type` est indicatif. Le futur moteur de sélection ne doit pas s'y baser exclusivement.

### server_availability
Disponibilités des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers) |
| start_datetime | TIMESTAMP | Début de disponibilité |
| end_datetime | TIMESTAMP | Fin de disponibilité |
| status | availability_status | AVAILABLE, UNAVAILABLE, RESERVED |
| note | TEXT | Remarque |
| created_at | TIMESTAMP | Date de création |

**Contrainte** : `end_datetime > start_datetime`

### vehicles
Véhicules des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| owner_server_id | UUID | Propriétaire (FK servers) |
| vehicle_type | vehicle_type | CAR, VAN, MOTORCYCLE, OTHER |
| brand | VARCHAR(100) | Marque |
| model | VARCHAR(100) | Modèle |
| seats_total | INTEGER | Nombre de places |
| can_transport_coworkers | BOOLEAN | Accepte le covoiturage |
| is_active | BOOLEAN | Véhicule actif |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**IMPORTANT** : `can_transport_coworkers` est explicite. Posséder un véhicule n'implique pas automatiquement le covoiturage.

### vehicle_availability
Disponibilités des véhicules.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| vehicle_id | UUID | Véhicule (FK vehicles) |
| start_datetime | TIMESTAMP | Début |
| end_datetime | TIMESTAMP | Fin |
| available | BOOLEAN | Disponible |
| created_at | TIMESTAMP | Date de création |

**Contrainte** : `end_datetime > start_datetime`

### events
Événements.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(255) | Nom de l'événement |
| client_name | VARCHAR(255) | Nom du client |
| city_id | UUID | Ville (FK cities) |
| address | TEXT | Adresse exacte |
| start_datetime | TIMESTAMP | Début |
| end_datetime | TIMESTAMP | Fin |
| guest_count | INTEGER | Nombre de convives |
| event_type | VARCHAR(100) | Type d'événement |
| alcohol_service | BOOLEAN | Service d'alcool |
| food_products_count | INTEGER | Nombre de produits alimentaires |
| priority | event_priority | NORMAL, PRIORITY, URGENT |
| is_urgent | BOOLEAN | Marqué comme urgent |
| urgent_created_at | TIMESTAMP | Date de marquage urgent |
| required_response_minutes | INTEGER | Délai de réponse requis (minutes) |
| status | event_status | PLANNED, STAFFING, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED |
| notes | TEXT | Remarques |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

**Contrainte** : `end_datetime > start_datetime`

### event_requirements
Besoins en personnel d'un événement.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| role_name | VARCHAR(100) | Rôle requis |
| quantity | INTEGER | Quantité nécessaire |
| required_gender | gender_type | Genre requis (optionnel) |
| minimum_experience | INTEGER | Expérience minimum (années) |
| minimum_skill_level | INTEGER | Niveau de compétence minimum 1-10 |
| notes | TEXT | Remarques |
| created_at | TIMESTAMP | Date de création |

**Flexibilité** : Les exigences sont paramétrables, pas codées en dur.

### event_staff
Affectations de serveurs aux événements.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| server_id | UUID | Serveur (FK servers) |
| role | VARCHAR(100) | Rôle attribué |
| assignment_status | assignment_status | PROPOSED, CONFIRMED, DECLINED, CANCELLED, COMPLETED |
| assigned_at | TIMESTAMP | Date d'affectation |
| confirmed_at | TIMESTAMP | Date de confirmation |

**Contrainte unique** : (event_id, server_id)

### evaluations
Évaluations des serveurs après événement.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| server_id | UUID | Serveur (FK servers) |
| punctuality | INTEGER | Ponctualité 1-10 |
| work_quality | INTEGER | Qualité du travail 1-10 |
| presentation | INTEGER | Présentation 1-10 |
| teamwork | INTEGER | Esprit d'équipe 1-10 |
| client_relation | INTEGER | Relation client 1-10 |
| comment | TEXT | Commentaire |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (event_id, server_id)

### transport_groups
Groupes de transport pour les serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement (FK events) |
| vehicle_id | UUID | Véhicule (FK vehicles) |
| driver_server_id | UUID | Conducteur (FK servers) |
| departure_latitude | NUMERIC(10,8) | Latitude départ |
| departure_longitude | NUMERIC(11,8) | Longitude départ |
| departure_location_label | VARCHAR(255) | Label lieu de départ |
| departure_time | TIMESTAMP | Heure de départ |
| destination_latitude | NUMERIC(10,8) | Latitude destination |
| destination_longitude | NUMERIC(11,8) | Longitude destination |
| destination_label | VARCHAR(255) | Label destination |
| estimated_distance_km | NUMERIC(6,2) | Distance estimée (km) |
| estimated_duration_minutes | INTEGER | Durée estimée (min) |
| status | transport_group_status | Statut du transport |
| created_at | TIMESTAMP | Date de création |

### transport_passengers
Passagers d'un groupe de transport.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| transport_group_id | UUID | Groupe de transport (FK transport_groups) |
| server_id | UUID | Serveur (FK servers) |
| pickup_latitude | NUMERIC(10,8) | Latitude du pickup |
| pickup_longitude | NUMERIC(11,8) | Longitude du pickup |
| pickup_location_label | VARCHAR(255) | Label lieu de pickup |
| pickup_order | INTEGER | Ordre de pickup (>=1) |
| pickup_status | pickup_status | Statut du pickup |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (transport_group_id, server_id)

### urgent_event_offers
Offres pour événements urgents.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| event_id | UUID | Événement urgent (FK events) |
| server_id | UUID | Serveur contacté (FK servers) |
| sent_at | TIMESTAMP | Date d'envoi |
| response_deadline | TIMESTAMP | Date limite de réponse |
| status | offer_status | PENDING, ACCEPTED, DECLINED, EXPIRED |
| responded_at | TIMESTAMP | Date de réponse |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (event_id, server_id)

### point_transactions
Historique des points attribués.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers) |
| event_id | UUID | Événement (FK events, nullable) |
| points | INTEGER | Points (positif ou négatif) |
| transaction_type | transaction_type | EARNED, BONUS, PENALTY, ADJUSTMENT |
| reason | TEXT | Raison |
| created_by | UUID | Créateur (FK users, nullable) |
| created_at | TIMESTAMP | Date de création |

**IMPORTANT** : Historique complet des points. Ne pas stocker de total dans servers.

### monthly_rankings
Classements mensuels des serveurs.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| server_id | UUID | Serveur (FK servers) |
| year | INTEGER | Année (2000-2100) |
| month | INTEGER | Mois (1-12) |
| total_points | INTEGER | Total des points |
| rank | INTEGER | Classement |
| bonus_amount | NUMERIC(10,2) | Montant de la prime |
| status | ranking_status | CALCULATED, PAID, ARCHIVED |
| created_at | TIMESTAMP | Date de création |

**Contrainte unique** : (server_id, year, month)

### bonus_rules
Règles configurables des primes.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Clé primaire |
| name | VARCHAR(255) | Nom de la règle |
| min_points | INTEGER | Points minimum |
| max_points | INTEGER | Points maximum |
| rank_from | INTEGER | Classement minimum |
| rank_to | INTEGER | Classement maximum |
| bonus_amount | NUMERIC(10,2) | Montant de la prime |
| active | BOOLEAN | Règle active |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Date de modification |

## Relations principales

```
cities ──< servers ──< server_locations
                    ├──< server_skills >── skills
                    ├──< server_profile
                    ├──< server_availability
                    ├──< vehicles ──< vehicle_availability
                    ├──< event_staff ──< events ──< event_requirements
                    ├──< evaluations
                    ├──< transport_passengers <── transport_groups
                    ├──< urgent_event_offers
                    └──< point_transactions
                            └──< monthly_rankings
```

## Indexes

Les indexes suivants optimisent les requêtes fréquentes :

- `servers.city_id`
- `server_locations.server_id`
- `server_locations.is_current`
- `server_availability.server_id`
- `server_availability(start_datetime, end_datetime)`
- `vehicles.owner_server_id`
- `vehicle_availability.vehicle_id`
- `events.city_id`
- `events.start_datetime`
- `events.status`
- `events.is_urgent`
- `event_requirements.event_id`
- `event_staff.event_id`
- `event_staff.server_id`
- `transport_groups.event_id`
- `urgent_event_offers.event_id`
- `urgent_event_offers.server_id`
- `point_transactions.server_id`
- `monthly_rankings(year, month)`

## Triggers

- `update_updated_at_column` : Met à jour automatiquement le champ `updated_at` sur plusieurs tables
- `enforce_single_current_location` : Garantit qu'un serveur ne peut avoir qu'une seule localisation actuelle

## Sécurité et vie privée

- Les coordonnées GPS exactes (`latitude`, `longitude`) sont stockées dans `server_locations` mais **ne doivent jamais être exposées publiquement**
- L'adresse exacte du domicile n'est pas stockée dans `servers`
- Le futur système devra contrôler les permissions d'accès aux données sensibles

## Exécution

```bash
# Créer la base de données
createdb le_seizieme

# Appliquer le schéma
psql -U postgres -d le_seizieme -f schema.sql

# Insérer les données de référence
psql -U postgres -d le_seizieme -f seed.sql
```
