-- automotive-big-loop: PostgreSQL schema
-- Power BI connects here via DirectQuery

-- ---------------------------------------------------------------------------
-- Telemetry snapshots (1 row per vehicle per second)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry (
    id              BIGSERIAL PRIMARY KEY,
    vehicle_id      VARCHAR(32)     NOT NULL,
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    driving_mode    VARCHAR(16),

    -- Engine
    engine_rpm          NUMERIC(7,1),
    throttle_pct        NUMERIC(5,1),
    engine_load_pct     NUMERIC(5,1),
    coolant_temp_c      NUMERIC(5,1),
    oil_temp_c          NUMERIC(5,1),
    oil_pressure_bar    NUMERIC(5,2),
    maf_gs              NUMERIC(7,2),
    map_kpa             NUMERIC(6,2),
    fuel_level_pct      NUMERIC(5,1),
    fuel_consumption    NUMERIC(7,2),
    lambda              NUMERIC(6,4),

    -- Transmission
    gear_engaged        SMALLINT,
    trans_temp_c        NUMERIC(5,1),
    torque_conv_slip    NUMERIC(7,1),

    -- BMS (12V)
    pack_voltage_v      NUMERIC(5,2),
    pack_current_a      NUMERIC(7,2),
    soc_pct             NUMERIC(5,1),
    cell_temp_max_c     NUMERIC(5,1),

    -- ADAS
    lane_departure      SMALLINT,
    fcw_active          BOOLEAN,
    ttc_ms              INTEGER,
    aeb_triggered       BOOLEAN,
    speed_limit_kmh     SMALLINT,

    -- Vehicle
    speed_kmh           NUMERIC(6,1),
    latitude            NUMERIC(10,6),
    longitude           NUMERIC(10,6),

    -- Fault flags
    mil_status          BOOLEAN,
    dtc_count           SMALLINT,
    anomaly_count       SMALLINT DEFAULT 0
);

-- ---------------------------------------------------------------------------
-- Anomaly events (one row per triggered rule)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anomaly_events (
    id              BIGSERIAL PRIMARY KEY,
    vehicle_id      VARCHAR(32)     NOT NULL,
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    rule            VARCHAR(64)     NOT NULL,
    severity        VARCHAR(16)     NOT NULL,
    signal          VARCHAR(64),
    value           NUMERIC(12,4),
    threshold       NUMERIC(12,4),
    description     TEXT
);

-- ---------------------------------------------------------------------------
-- OTA campaigns
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ota_campaigns (
    campaign_id     VARCHAR(128)    PRIMARY KEY,
    ecu_target      VARCHAR(32),
    fw_version      VARCHAR(32),
    state           VARCHAR(32),
    total_vehicles  SMALLINT,
    completed       SMALLINT DEFAULT 0,
    errors          SMALLINT DEFAULT 0,
    started_at      TIMESTAMPTZ     DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- OTA status per vehicle
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ota_status (
    id              BIGSERIAL PRIMARY KEY,
    vehicle_id      VARCHAR(32)     NOT NULL,
    campaign_id     VARCHAR(128),
    session_id      VARCHAR(64),
    status_code     SMALLINT,
    progress_pct    SMALLINT,
    error_code      SMALLINT,
    fw_version      VARCHAR(32),
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Indexes for Power BI DirectQuery performance
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_ts   ON telemetry (vehicle_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_vehicle_ts     ON anomaly_events (vehicle_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_rule           ON anomaly_events (rule);
CREATE INDEX IF NOT EXISTS idx_ota_status_vehicle     ON ota_status (vehicle_id, ts DESC);