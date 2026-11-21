-- Receipt lines a helper could not match, and possible repeat receipts (decision 0105).
-- A waiting row is now one of two kinds: a suggested record (as before) or a receipt line the helper read but
-- could not match to a Stock item. A line's `values_json` holds only the helper's hints (date, amount, unit),
-- which are never saved in the records; a person chooses the item and the amount. For a line, "accepted" means
-- a person added a Stock in for it (record_id is that Stock in) and "rejected" means the person skipped it.
ALTER TABLE core__proposals ADD COLUMN entry_kind TEXT NOT NULL DEFAULT 'record'
    CHECK (entry_kind IN ('record', 'receipt_line'));
-- A batch may say it is one receipt: its purchase date and an optional shop name, as the helper or the person
-- importing it gave them. Only such batches are compared to find a receipt sent twice.
ALTER TABLE core__helper_batches ADD COLUMN receipt_json TEXT;
-- A batch with receipt lines stays on Review until the person presses "Finish receipt review", so a skipped
-- line can be undone until then.
ALTER TABLE core__helper_batches ADD COLUMN finished_at TEXT;
-- "Keep this as another purchase": which earlier receipt the person looked at, and the state of its rows then.
-- Only row ids and states are kept, never the goods or amounts. It stops counting when either receipt changes.
ALTER TABLE core__helper_batches ADD COLUMN repeat_ok_json TEXT;
