-- FarmGuard_V2/Database/schema_postgres.sql
-- Placeholder schema for PostgreSQL.
-- You would typically manage this with migrations (e.g., Alembic with SQLAlchemy).

DROP TABLE IF EXISTS guardian_events CASCADE;
DROP TABLE IF EXISTS subunit_events CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
-- Add other tables to drop if they exist

CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    asset_name VARCHAR(255) NOT NULL,
    description TEXT,
    rfid_tag_assigned VARCHAR(100) UNIQUE, -- EPC of the tag
    asset_type VARCHAR(100),
    purchase_date DATE,
    current_status VARCHAR(50), -- e.g., 'in_field', 'in_storage', 'maintenance'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guardian_events (
    id SERIAL PRIMARY KEY,
    unit_id VARCHAR(50) NOT NULL, -- ID of the RPi Guardian Unit
    timestamp_iso VARCHAR(50) NOT NULL, -- ISO format timestamp string from Guardian
    tag_id VARCHAR(100) NOT NULL,
    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL, -- Link to an Asset
    video_url_remote VARCHAR(512),
    direction VARCHAR(20), -- 'ingress', 'egress', 'unknown'
    raw_event_payload JSONB, -- Store the full JSON received from guardian unit
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- When API server received it
);

CREATE TABLE subunit_events (
    id SERIAL PRIMARY KEY,
    unit_id VARCHAR(50) NOT NULL, -- ID of the LoRaWAN SubUnit
    tag_id VARCHAR(100),
    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    location_description VARCHAR(255), -- e.g., "Field_3_North_Entrance"
    battery_level REAL,
    rssi INTEGER,
    snr REAL,
    raw_lorawan_payload TEXT,
    reported_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Timestamp from LoRaWAN metadata or payload
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TODO: Add more tables:
-- - users (for web app authentication)
-- - geofences
-- - fsma_traceability_log (for specific KDEs)
-- - alerts

-- Indexes for performance
CREATE INDEX idx_guardian_events_tag_id ON guardian_events(tag_id);
CREATE INDEX idx_guardian_events_timestamp_iso ON guardian_events(timestamp_iso);
CREATE INDEX idx_subunit_events_tag_id ON subunit_events(tag_id);
CREATE INDEX idx_assets_rfid_tag ON assets(rfid_tag_assigned);

-- Basic function to update 'updated_at' columns (optional)
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_assets_timestamp
BEFORE UPDATE ON assets
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- You might add more triggers or initial data seeding here.