-- One reminder per policy (decision 0117): which records of an older list (such as Vehicle insurance) the
-- household chose, one by one, to have reminded from a newer list (such as Bills and insurance) instead.
-- Both records are named by their local number and their permanent ID, never by a name. `state` says who
-- reminds now: "moved" (the newer record; the older one is kept, read-only, as its earlier record),
-- "returned" (moved back: the older record reminds again and the newer one is kept, silent) or "kept"
-- (the household chose to keep this one where it was; no newer record). Only IDs and the state are kept here,
-- never a name, date, note or private detail. One row per older record, so a second press never makes a
-- second reminder.
CREATE TABLE core__reminder_moves (
    id INTEGER PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    source_global_id TEXT,
    target_table TEXT NOT NULL,
    target_id INTEGER,
    target_global_id TEXT,
    state TEXT NOT NULL CHECK (state IN ('moved', 'returned', 'kept')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (source_table, source_id)
);
CREATE INDEX core__reminder_moves__target__idx ON core__reminder_moves(target_table, target_id);
