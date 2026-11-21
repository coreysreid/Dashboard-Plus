-- Sync stage 1 (decision 0100): permanent record IDs, revisions and a filtered change log. Nothing here is
-- sent anywhere; it is kept so that a later stage can share records with another computer of the household.
-- The permanent ID and revision columns of the modules' own tables are added by the core after each
-- module's migrations (src/dashboard/core/sync.py), never by a module.

-- The household's random ID, the current restore epoch and the exchange format version, by key.
CREATE TABLE core__sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- One line per epoch: when it started and why (first IDs, a restore, an undone restore, a rebuilt table).
-- An epoch only goes up, so a change log or a later copy from before a restore is never mistaken for now.
CREATE TABLE core__sync_epochs (
    epoch INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    new_ids INTEGER NOT NULL DEFAULT 0
);

-- Each module table that has been given permanent IDs, so a table rebuilt without them is noticed.
CREATE TABLE core__sync_tables (
    table_name TEXT PRIMARY KEY,
    since TEXT NOT NULL
);

-- The change log: one line per record (or link between two records) changed by one operation.
-- `patch` holds only values that may travel; links are given as the other record's permanent ID.
-- `withheld` names the changed fields whose values stay on this computer: never their value, length or hash.
CREATE TABLE core__sync_changes (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch INTEGER NOT NULL,
    operation_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'restore', 'link', 'unlink')),
    table_name TEXT NOT NULL,
    global_id TEXT NOT NULL,
    target_id TEXT NOT NULL DEFAULT '',
    base_revision INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    columns TEXT NOT NULL DEFAULT '[]',
    patch TEXT NOT NULL DEFAULT '{}',
    withheld TEXT NOT NULL DEFAULT '[]',
    effect INTEGER NOT NULL DEFAULT 0,
    exchange_schema INTEGER NOT NULL,
    at TEXT NOT NULL,
    UNIQUE (operation_id, table_name, global_id, target_id)
);
CREATE INDEX core__sync_changes__record__idx ON core__sync_changes(table_name, global_id);

-- Values held on this computer after their row changed kind across the travel boundary (such as an access
-- instruction re-labelled as a medication): they stay local until the value itself is typed again.
CREATE TABLE core__sync_held (
    table_name TEXT NOT NULL,
    global_id TEXT NOT NULL,
    column_name TEXT NOT NULL,
    since TEXT NOT NULL,
    PRIMARY KEY (table_name, global_id, column_name)
);
