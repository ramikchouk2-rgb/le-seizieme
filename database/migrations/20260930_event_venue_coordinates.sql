-- Step 24C: Event venue coordinates
--
-- Adds optional, real geographic coordinates to `events` so the venue position
-- is stored on the event itself instead of being derived from the personal GPS
-- of an arbitrary server in the same city.
--
-- Both columns stay NULLABLE on purpose:
--   * Existing events have no verified venue position.
--   * This migration deliberately performs NO backfill: fabricating coordinates
--     for events that were never geolocated would be worse than leaving them
--     unknown. The application falls back to DEFAULT_EVENT_LATITUDE /
--     DEFAULT_EVENT_LONGITUDE and flags the location as approximate.
--
-- `server_locations` is intentionally left untouched: it models a person's
-- current position and is never used to represent a venue.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'events' AND column_name = 'latitude'
    ) THEN
        ALTER TABLE events ADD COLUMN latitude NUMERIC(10, 8);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'events' AND column_name = 'longitude'
    ) THEN
        ALTER TABLE events ADD COLUMN longitude NUMERIC(11, 8);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'events_latitude_range_check'
    ) THEN
        ALTER TABLE events
            ADD CONSTRAINT events_latitude_range_check
            CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'events_longitude_range_check'
    ) THEN
        ALTER TABLE events
            ADD CONSTRAINT events_longitude_range_check
            CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_events_coordinates
    ON events(latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
