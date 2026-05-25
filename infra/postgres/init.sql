CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'operator',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    external_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, external_id)
);

CREATE TABLE IF NOT EXISTS face_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    person_id UUID REFERENCES people(id),
    model TEXT NOT NULL,
    embedding VECTOR(512) NOT NULL,
    quality_score NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recognition_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    person_id UUID REFERENCES people(id),
    distance NUMERIC,
    matched BOOLEAN NOT NULL,
    source TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS work_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name TEXT NOT NULL,
    scheduled_start_time TIME,
    scheduled_exit_time TIME NOT NULL,
    tolerance_minutes INTEGER NOT NULL DEFAULT 10,
    timezone TEXT NOT NULL DEFAULT 'America/Lima',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS schedule_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    person_id UUID REFERENCES people(id),
    schedule_id UUID REFERENCES work_schedules(id),
    valid_from DATE NOT NULL,
    valid_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS edge_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    site_id UUID,
    device_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attendance_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    person_id UUID REFERENCES people(id),
    schedule_id UUID REFERENCES work_schedules(id),
    device_id UUID REFERENCES edge_devices(id),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL,
    scheduled_exit_time TIME,
    tolerance_minutes INTEGER,
    decision TEXT NOT NULL,
    confidence NUMERIC,
    accepted BOOLEAN NOT NULL DEFAULT true,
    duplicate BOOLEAN NOT NULL DEFAULT false,
    evidence_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS edge_sync_manifests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    device_id UUID REFERENCES edge_devices(id),
    version BIGINT NOT NULL,
    embedding_count INTEGER NOT NULL DEFAULT 0,
    rules_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exit_reason_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    attendance_event_id UUID REFERENCES attendance_events(id),
    reason_text TEXT NOT NULL,
    ai_provider TEXT NOT NULL,
    ai_is_valid BOOLEAN NOT NULL,
    ai_category TEXT NOT NULL,
    ai_confidence NUMERIC,
    ai_risk_score NUMERIC,
    ai_explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workforce_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    person_id UUID REFERENCES people(id),
    attendance_event_id UUID REFERENCES attendance_events(id),
    violation_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    evidence_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS supervisor_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    incident_id UUID REFERENCES workforce_incidents(id),
    supervisor_user_id UUID REFERENCES users(id),
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS behavior_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    person_id UUID REFERENCES people(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    early_exit_count INTEGER NOT NULL DEFAULT 0,
    incident_count INTEGER NOT NULL DEFAULT 0,
    approved_exception_count INTEGER NOT NULL DEFAULT 0,
    risk_score NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
