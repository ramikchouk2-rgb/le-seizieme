-- ===================================================
-- Le Seizième - Database Schema
-- ===================================================
-- PostgreSQL schema for event staffing management
-- ===================================================


-- ===================================================
-- EXTENSIONS
-- ===================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS btree_gist;


-- ===================================================
-- ENUMS
-- ===================================================

CREATE TYPE gender_type AS ENUM ('MALE', 'FEMALE', 'OTHER');
CREATE TYPE worker_type AS ENUM ('HARD_WORKER', 'BALANCED', 'SOFT_WORKER');
CREATE TYPE availability_status AS ENUM ('AVAILABLE', 'UNAVAILABLE', 'RESERVED');
CREATE TYPE vehicle_type AS ENUM ('CAR', 'VAN', 'MOTORCYCLE', 'OTHER');
CREATE TYPE event_priority AS ENUM ('NORMAL', 'PRIORITY', 'URGENT');
CREATE TYPE event_status AS ENUM ('PLANNED', 'STAFFING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
CREATE TYPE assignment_status AS ENUM ('PROPOSED', 'CONFIRMED', 'DECLINED', 'CANCELLED', 'COMPLETED');
CREATE TYPE transport_group_status AS ENUM ('PLANNED', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
CREATE TYPE pickup_status AS ENUM ('PENDING', 'PICKED_UP', 'COMPLETED', 'NO_SHOW');
CREATE TYPE offer_status AS ENUM ('PENDING', 'ACCEPTED', 'DECLINED', 'EXPIRED');
CREATE TYPE ranking_status AS ENUM ('CALCULATED', 'PAID', 'ARCHIVED');
CREATE TYPE transaction_type AS ENUM ('EARNED', 'BONUS', 'PENALTY', 'ADJUSTMENT');
CREATE TYPE user_role AS ENUM ('ADMIN', 'MANAGER', 'STAFF');
CREATE TYPE attendance_status AS ENUM ('EXPECTED', 'PRESENT', 'LATE', 'ABSENT', 'EXCUSED', 'LEFT');


-- ===================================================
-- CITIES
-- ===================================================

CREATE TABLE cities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cities_name ON cities(name);


-- ===================================================
-- USERS
-- ===================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'STAFF',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);


-- ===================================================
-- SERVERS
-- ===================================================

CREATE TABLE servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    gender gender_type NOT NULL,
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE RESTRICT,
    years_experience INTEGER NOT NULL CHECK (years_experience >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    profile_photo TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_servers_city_id ON servers(city_id);
CREATE INDEX idx_servers_is_active ON servers(is_active);
CREATE INDEX idx_servers_email ON servers(email);


-- ===================================================
-- SERVER_LOCATIONS
-- ===================================================

CREATE TABLE server_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE RESTRICT,
    area VARCHAR(255),
    latitude NUMERIC(10, 8) NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude NUMERIC(11, 8) NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMP,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_server_locations_server_id ON server_locations(server_id);
CREATE INDEX idx_server_locations_is_current ON server_locations(is_current) WHERE is_current = TRUE;
CREATE UNIQUE INDEX idx_server_locations_unique_current ON server_locations(server_id) WHERE is_current = TRUE;


-- ===================================================
-- SKILLS
-- ===================================================

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skills_name ON skills(name);


-- ===================================================
-- SERVER_SKILLS
-- ===================================================

CREATE TABLE server_skills (
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,
    level INTEGER NOT NULL CHECK (level >= 1 AND level <= 10),
    years_experience INTEGER NOT NULL CHECK (years_experience >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id, skill_id)
);

CREATE INDEX idx_server_skills_server_id ON server_skills(server_id);
CREATE INDEX idx_server_skills_skill_id ON server_skills(skill_id);


-- ===================================================
-- SERVER_PROFILE
-- ===================================================

CREATE TABLE server_profile (
    server_id UUID PRIMARY KEY REFERENCES servers(id) ON DELETE CASCADE,
    speed_score INTEGER NOT NULL CHECK (speed_score >= 1 AND speed_score <= 10),
    punctuality_score INTEGER NOT NULL CHECK (punctuality_score >= 1 AND punctuality_score <= 10),
    presentation_score INTEGER NOT NULL CHECK (presentation_score >= 1 AND presentation_score <= 10),
    communication_score INTEGER NOT NULL CHECK (communication_score >= 1 AND communication_score <= 10),
    teamwork_score INTEGER NOT NULL CHECK (teamwork_score >= 1 AND teamwork_score <= 10),
    discipline_score INTEGER NOT NULL CHECK (discipline_score >= 1 AND discipline_score <= 10),
    endurance_score INTEGER NOT NULL CHECK (endurance_score >= 1 AND endurance_score <= 10),
    worker_type worker_type NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ===================================================
-- SERVER_AVAILABILITY
-- ===================================================

CREATE TABLE server_availability (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    status availability_status NOT NULL DEFAULT 'AVAILABLE',
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_datetime > start_datetime),
    EXCLUDE USING gist (server_id WITH =, tsrange(start_datetime, end_datetime) WITH &&)
);

CREATE INDEX idx_server_availability_server_id ON server_availability(server_id);
CREATE INDEX idx_server_availability_dates ON server_availability(start_datetime, end_datetime);


-- ===================================================
-- VEHICLES
-- ===================================================

CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    vehicle_type vehicle_type NOT NULL,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    seats_total INTEGER NOT NULL CHECK (seats_total > 0),
    can_transport_coworkers BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vehicles_owner_server_id ON vehicles(owner_server_id);
CREATE INDEX idx_vehicles_is_active ON vehicles(is_active);


-- ===================================================
-- VEHICLE_AVAILABILITY
-- ===================================================

CREATE TABLE vehicle_availability (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_datetime > start_datetime)
);

CREATE INDEX idx_vehicle_availability_vehicle_id ON vehicle_availability(vehicle_id);
CREATE INDEX idx_vehicle_availability_dates ON vehicle_availability(start_datetime, end_datetime);


-- ===================================================
-- EVENTS
-- ===================================================

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE RESTRICT,
    address TEXT NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    guest_count INTEGER NOT NULL CHECK (guest_count > 0),
    event_type VARCHAR(100) NOT NULL,
    alcohol_service BOOLEAN NOT NULL DEFAULT FALSE,
    food_products_count INTEGER NOT NULL DEFAULT 0 CHECK (food_products_count >= 0),
    priority event_priority NOT NULL DEFAULT 'NORMAL',
    is_urgent BOOLEAN NOT NULL DEFAULT FALSE,
    urgent_created_at TIMESTAMP,
    required_response_minutes INTEGER,
    status event_status NOT NULL DEFAULT 'PLANNED',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_datetime > start_datetime)
);

CREATE INDEX idx_events_city_id ON events(city_id);
CREATE INDEX idx_events_start_datetime ON events(start_datetime);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_is_urgent ON events(is_urgent) WHERE is_urgent = TRUE;


-- ===================================================
-- EVENT_REQUIREMENTS
-- ===================================================

CREATE TABLE event_requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    role_name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    required_gender gender_type,
    minimum_experience INTEGER NOT NULL DEFAULT 0 CHECK (minimum_experience >= 0),
    minimum_skill_level INTEGER NOT NULL DEFAULT 1 CHECK (minimum_skill_level >= 1 AND minimum_skill_level <= 10),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_event_requirements_event_id ON event_requirements(event_id);


-- ===================================================
-- EVENT_STAFF
-- ===================================================

CREATE TABLE event_staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE RESTRICT,
    role VARCHAR(100) NOT NULL,
    assignment_status assignment_status NOT NULL DEFAULT 'PROPOSED',
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    CHECK (
        (assignment_status = 'CONFIRMED' AND confirmed_at IS NOT NULL) OR
        (assignment_status != 'CONFIRMED')
    ),
    UNIQUE(event_id, server_id)
);

CREATE INDEX idx_event_staff_event_id ON event_staff(event_id);
CREATE INDEX idx_event_staff_server_id ON event_staff(server_id);
CREATE INDEX idx_event_staff_status ON event_staff(assignment_status);


-- ===================================================
-- EVENT_ATTENDANCE
-- ===================================================

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


-- ===================================================
-- EVALUATIONS
-- ===================================================

CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE RESTRICT,
    punctuality INTEGER NOT NULL CHECK (punctuality >= 1 AND punctuality <= 10),
    work_quality INTEGER NOT NULL CHECK (work_quality >= 1 AND work_quality <= 10),
    presentation INTEGER NOT NULL CHECK (presentation >= 1 AND presentation <= 10),
    teamwork INTEGER NOT NULL CHECK (teamwork >= 1 AND teamwork <= 10),
    client_relation INTEGER NOT NULL CHECK (client_relation >= 1 AND client_relation <= 10),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, server_id)
);

CREATE INDEX idx_evaluations_event_id ON evaluations(event_id);
CREATE INDEX idx_evaluations_server_id ON evaluations(server_id);


-- ===================================================
-- TRANSPORT_GROUPS
-- ===================================================

CREATE TABLE transport_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
    driver_server_id UUID NOT NULL REFERENCES servers(id) ON DELETE RESTRICT,
    departure_latitude NUMERIC(10, 8) NOT NULL CHECK (departure_latitude >= -90 AND departure_latitude <= 90),
    departure_longitude NUMERIC(11, 8) NOT NULL CHECK (departure_longitude >= -180 AND departure_longitude <= 180),
    departure_location_label VARCHAR(255) NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    destination_latitude NUMERIC(10, 8) NOT NULL CHECK (destination_latitude >= -90 AND destination_latitude <= 90),
    destination_longitude NUMERIC(11, 8) NOT NULL CHECK (destination_longitude >= -180 AND destination_longitude <= 180),
    destination_label VARCHAR(255) NOT NULL,
    estimated_distance_km NUMERIC(6, 2),
    estimated_duration_minutes INTEGER,
    status transport_group_status NOT NULL DEFAULT 'PLANNED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transport_groups_event_id ON transport_groups(event_id);
CREATE INDEX idx_transport_groups_vehicle_id ON transport_groups(vehicle_id);
CREATE INDEX idx_transport_groups_driver_server_id ON transport_groups(driver_server_id);


-- ===================================================
-- TRANSPORT_PASSENGERS
-- ===================================================

CREATE TABLE transport_passengers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transport_group_id UUID NOT NULL REFERENCES transport_groups(id) ON DELETE CASCADE,
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE RESTRICT,
    pickup_latitude NUMERIC(10, 8) NOT NULL CHECK (pickup_latitude >= -90 AND pickup_latitude <= 90),
    pickup_longitude NUMERIC(11, 8) NOT NULL CHECK (pickup_longitude >= -180 AND pickup_longitude <= 180),
    pickup_location_label VARCHAR(255) NOT NULL,
    pickup_order INTEGER NOT NULL CHECK (pickup_order >= 1),
    pickup_status pickup_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(transport_group_id, server_id),
    UNIQUE(transport_group_id, pickup_order)
);

CREATE INDEX idx_transport_passengers_transport_group_id ON transport_passengers(transport_group_id);
CREATE INDEX idx_transport_passengers_server_id ON transport_passengers(server_id);


-- ===================================================
-- URGENT_EVENT_OFFERS
-- ===================================================

CREATE TABLE urgent_event_offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE RESTRICT,
    wave_number INTEGER NOT NULL CHECK (wave_number >= 1),
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_deadline TIMESTAMP NOT NULL,
    status offer_status NOT NULL DEFAULT 'PENDING',
    responded_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, server_id, wave_number)
);

CREATE INDEX idx_urgent_event_offers_event_id ON urgent_event_offers(event_id);
CREATE INDEX idx_urgent_event_offers_server_id ON urgent_event_offers(server_id);


-- ===================================================
-- POINT_TRANSACTIONS
-- ===================================================

CREATE TABLE point_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE RESTRICT,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    points INTEGER NOT NULL,
    transaction_type transaction_type NOT NULL,
    reason TEXT,
    created_by UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_point_transactions_server_id ON point_transactions(server_id);
CREATE INDEX idx_point_transactions_event_id ON point_transactions(event_id);


-- ===================================================
-- MONTHLY_RANKINGS
-- ===================================================

CREATE TABLE monthly_rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    year INTEGER NOT NULL CHECK (year >= 2000 AND year <= 2100),
    month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
    total_points INTEGER NOT NULL DEFAULT 0,
    rank INTEGER,
    bonus_amount NUMERIC(10, 2) DEFAULT 0,
    status ranking_status NOT NULL DEFAULT 'CALCULATED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, year, month)
);

CREATE INDEX idx_monthly_rankings_server_id ON monthly_rankings(server_id);
CREATE INDEX idx_monthly_rankings_year_month ON monthly_rankings(year, month);


-- ===================================================
-- BONUS_RULES
-- ===================================================

CREATE TABLE bonus_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    min_points INTEGER NOT NULL CHECK (min_points >= 0),
    max_points INTEGER NOT NULL CHECK (max_points >= min_points),
    rank_from INTEGER NOT NULL CHECK (rank_from >= 1),
    rank_to INTEGER NOT NULL CHECK (rank_to >= rank_from),
    bonus_amount NUMERIC(10, 2) NOT NULL CHECK (bonus_amount >= 0),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bonus_rules_active ON bonus_rules(active) WHERE active = TRUE;


-- ===================================================
-- TRIGGERS
-- ===================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_servers_updated_at BEFORE UPDATE ON servers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_server_locations_updated_at BEFORE UPDATE ON server_locations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_server_profile_updated_at BEFORE UPDATE ON server_profile FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_bonus_rules_updated_at BEFORE UPDATE ON bonus_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Ensure only one current location per server is enforced by:
-- CREATE UNIQUE INDEX idx_server_locations_unique_current ON server_locations(server_id) WHERE is_current = TRUE;


-- Point transactions are immutable
CREATE OR REPLACE FUNCTION prevent_point_transaction_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'point_transactions is immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_point_transaction_modification 
BEFORE UPDATE OR DELETE ON point_transactions 
FOR EACH ROW EXECUTE FUNCTION prevent_point_transaction_modification();
