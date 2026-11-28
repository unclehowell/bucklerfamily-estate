-- Estate event ledger v1.0.0
-- Metadata only. Original email/document bytes stay in the system of record or approved private object storage.
-- Do not add raw message bodies, contact details, addresses, credentials or attachment bytes to these tables.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS event_log (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  source_system TEXT NOT NULL CHECK (source_system IN ('gmail','github','cloudflare','hubspot','catalogue','archive','manual')),
  source_id TEXT NOT NULL,
  source_url TEXT,
  occurred_at TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  actor TEXT NOT NULL,
  related_ids_json TEXT NOT NULL DEFAULT '{}',
  content_sha256 TEXT NOT NULL,
  privacy_class TEXT NOT NULL DEFAULT 'private' CHECK (privacy_class IN ('private','public')),
  idempotency_key TEXT NOT NULL UNIQUE,
  processing_state TEXT NOT NULL DEFAULT 'received' CHECK (processing_state IN ('received','queued','processing','complete','quarantined','failed')),
  supersedes_event_id TEXT REFERENCES event_log(event_id),
  artifact_ref TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (source_system, source_id)
);

CREATE INDEX IF NOT EXISTS event_log_type_time_idx ON event_log(event_type, occurred_at);
CREATE INDEX IF NOT EXISTS event_log_state_idx ON event_log(processing_state, ingested_at);
CREATE INDEX IF NOT EXISTS event_log_privacy_idx ON event_log(privacy_class, ingested_at);

CREATE TABLE IF NOT EXISTS event_jobs (
  job_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES event_log(event_id),
  work_type TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending','claimed','complete','dead_letter')),
  claim_owner TEXT,
  lease_expires_at TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  retry_after TEXT,
  last_error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (event_id, work_type)
);

CREATE INDEX IF NOT EXISTS event_jobs_claim_idx ON event_jobs(state, retry_after, lease_expires_at);
