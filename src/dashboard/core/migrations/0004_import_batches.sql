-- Rows imported from a spreadsheet wait on Review in the same place as helpers' suggestions (decision 0080).
-- A batch now says where it came from: a helper (helper_id set) or an import by a person (source_name set,
-- the file's name, and no helper). Each waiting row may keep the spreadsheet row it came from.
-- SQLite cannot loosen NOT NULL in place, so both tables are rebuilt: new ones are made and filled, the old
-- ones dropped (the waiting rows first, as they point at the batches), and the new ones take the old names.
CREATE TABLE core__batches_new (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'helper' CHECK (kind IN ('helper', 'import')),
    helper_id INTEGER REFERENCES core__helpers(id),
    source_name TEXT,
    request_key TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    why TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (helper_id, request_key),
    CHECK ((kind = 'helper' AND helper_id IS NOT NULL AND source_name IS NULL)
        OR (kind = 'import' AND helper_id IS NULL AND source_name IS NOT NULL))
);
INSERT INTO core__batches_new (id, kind, helper_id, source_name, request_key, body_hash, why, created_at)
    SELECT id, 'helper', helper_id, NULL, request_key, body_hash, why, created_at FROM core__helper_batches;

CREATE TABLE core__proposals_new (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES core__batches_new(id),
    position INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    values_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    record_id INTEGER,
    reason TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    source_row INTEGER
);
INSERT INTO core__proposals_new (id, batch_id, position, table_name, values_json, status, record_id, reason,
                                 created_at, decided_at)
    SELECT id, batch_id, position, table_name, values_json, status, record_id, reason, created_at, decided_at
    FROM core__proposals;

DROP TABLE core__proposals;
DROP TABLE core__helper_batches;
ALTER TABLE core__batches_new RENAME TO core__helper_batches;
ALTER TABLE core__proposals_new RENAME TO core__proposals;
CREATE INDEX core__proposals__status__idx ON core__proposals(status, batch_id);
CREATE INDEX core__helper_batches__helper__idx ON core__helper_batches(helper_id, created_at);
