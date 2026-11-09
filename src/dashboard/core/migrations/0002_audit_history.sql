-- Every change to every record: who or what made it, and the values before and after.
-- before/after hold JSON of only the fields that changed.
CREATE TABLE core__audit (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    before TEXT,
    after TEXT,
    batch_id INTEGER
);
CREATE INDEX core__audit__record__idx ON core__audit(table_name, record_id);
CREATE INDEX core__audit__at__idx ON core__audit(at);
