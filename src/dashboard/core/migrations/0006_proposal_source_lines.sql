-- A helper's suggestion may carry the line it was read from, such as a receipt line and its price (decision 0097).
-- It is kept beside the suggestion as the helper wrote it, shown on Review as the helper's words, and never copied
-- into the household's records. Older suggestions have none.
ALTER TABLE core__proposals ADD COLUMN source_json TEXT;
