-- Settings written by the first-run wizard and the settings page.
CREATE TABLE core__settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Every module this data folder has used, its version, and whether it is on.
CREATE TABLE core__modules (
    name TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
