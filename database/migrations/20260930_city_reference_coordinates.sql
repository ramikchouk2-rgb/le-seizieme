-- Step 24C-D-4: City reference coordinates
--
-- Adds optional reference coordinates to `cities` so an event with no stored
-- venue position can fall back to a point in its OWN city instead of the single
-- global technical fallback (Tunis downtown), which was geographically wrong
-- for every other seeded city.
--
-- Both columns stay NULLABLE on purpose:
--   * A NULL city means "no verified reference position for this city", and the
--     resolver then degrades to the global technical fallback rather than
--     inventing one.
--   * This migration deliberately performs NO backfill. Fabricating a centre
--     point for a city we have no verified reference for would reintroduce
--     exactly the class of bug Step 24C-B removed.
--
-- `server_locations` is intentionally left untouched: it models a person's
-- current position and is NEVER used to represent a venue, at any level of the
-- resolution hierarchy.
--
-- No index is added on (latitude, longitude): cities are always looked up by
-- their primary key (`events.city_id`), and there is no radius or proximity
-- query anywhere in the application. An index here would be dead weight. The
-- partial coordinate index on `events` (idx_events_coordinates) already covers
-- the coordinate-bearing lookup pattern.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cities' AND column_name = 'latitude'
    ) THEN
        ALTER TABLE cities ADD COLUMN latitude NUMERIC(10, 8);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'cities' AND column_name = 'longitude'
    ) THEN
        ALTER TABLE cities ADD COLUMN longitude NUMERIC(11, 8);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cities_latitude_range_check'
    ) THEN
        ALTER TABLE cities
            ADD CONSTRAINT cities_latitude_range_check
            CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cities_longitude_range_check'
    ) THEN
        ALTER TABLE cities
            ADD CONSTRAINT cities_longitude_range_check
            CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180));
    END IF;
END $$;

-- Partial coordinate pair: a city reference is only usable when BOTH values are
-- present. A single NULL coordinate is never interpreted as origin (0, 0).
ALTER TABLE cities DROP CONSTRAINT IF EXISTS cities_coordinates_paired_check;
ALTER TABLE cities
    ADD CONSTRAINT cities_coordinates_paired_check
    CHECK (
        (latitude IS NULL AND longitude IS NULL)
        OR (latitude IS NOT NULL AND longitude IS NOT NULL)
    );
