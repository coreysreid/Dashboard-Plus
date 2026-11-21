-- "Allow 200 more today" (decision 0101): each press adds to one helper's daily limit for one day only.
-- `day` is the household's own date (this computer's clock) the press was for; a row for another day counts
-- for nothing. Each press is its own row, so the history shows who pressed it and when. Only the Review and
-- Settings pages write here, through a one-use form token; the helper API never does.
CREATE TABLE core__helper_allowances (
    id INTEGER PRIMARY KEY,
    helper_id INTEGER NOT NULL REFERENCES core__helpers(id),
    day TEXT NOT NULL,
    extra INTEGER NOT NULL CHECK (extra > 0),
    granted_at TEXT NOT NULL,
    granted_by TEXT NOT NULL
);
CREATE INDEX core__helper_allowances__helper_day__idx ON core__helper_allowances(helper_id, day);
