-- Database schema for DevTrace

CREATE TABLE IF NOT EXISTS developer_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    developer_id TEXT NOT NULL,
    source_tool TEXT NOT NULL,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS context_switches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    developer_id TEXT NOT NULL,
    switched_at TIMESTAMPTZ NOT NULL,
    from_project TEXT NOT NULL,
    to_project TEXT NOT NULL,
    reason TEXT,
    confidence_score REAL,
    detected_by TEXT
);

CREATE TABLE IF NOT EXISTS project_onboarding_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    active_objectives JSONB DEFAULT '[]'::jsonb,
    current_blockers JSONB DEFAULT '[]'::jsonb,
    recent_switches JSONB DEFAULT '[]'::jsonb,
    raw_summary TEXT
);

CREATE TABLE IF NOT EXISTS traces (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    session_id TEXT,
    prompt TEXT,
    response TEXT,
    latency_ms REAL,
    cost REAL,
    status TEXT
);

CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    trace_id TEXT REFERENCES traces(id),
    metric_name TEXT,
    score REAL,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
