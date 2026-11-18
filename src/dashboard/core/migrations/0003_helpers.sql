-- Helpers (AI or human assistants) the household gave a key to. The key itself is never stored;
-- its fingerprint lives in data/secrets/helper_keys.json, matched by key_id.
CREATE TABLE core__helpers (
    id INTEGER PRIMARY KEY,
    key_id TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    access TEXT NOT NULL CHECK (access IN ('read', 'suggest')),
    modules TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at TEXT
);

-- One request from a helper: a group of suggestions sent together, with the reason and a retry key.
CREATE TABLE core__helper_batches (
    id INTEGER PRIMARY KEY,
    helper_id INTEGER NOT NULL REFERENCES core__helpers(id),
    request_key TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    why TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (helper_id, request_key)
);

-- Each suggested new record, waiting for a person to accept or reject it.
CREATE TABLE core__proposals (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES core__helper_batches(id),
    position INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    values_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    record_id INTEGER,
    reason TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);
CREATE INDEX core__proposals__status__idx ON core__proposals(status, batch_id);
CREATE INDEX core__helper_batches__helper__idx ON core__helper_batches(helper_id, created_at);
