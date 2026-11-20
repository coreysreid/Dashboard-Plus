-- A helper's key can be replaced without making a new helper (decision 0093). The helper keeps its id, key_id,
-- slug, grant and history. key_pending_at is set while a new key is being made: no key of that helper works
-- until it is cleared. key_generation goes up with each new key, so a suggestion checked with the old key is
-- refused at the write. rotated_at is when the key was last replaced.
ALTER TABLE core__helpers ADD COLUMN rotated_at TEXT;
ALTER TABLE core__helpers ADD COLUMN key_pending_at TEXT;
ALTER TABLE core__helpers ADD COLUMN key_generation INTEGER NOT NULL DEFAULT 0;
