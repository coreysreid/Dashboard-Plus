-- What your other computers get (decision 0140): the household's own sharing choice for a list
-- (column_name = '') or for one detail of a list. Only choices that differ from the module's own rule are kept;
-- no row means the module's rule, exactly as before. Only table and column names and a choice word are kept
-- here, never a record's value. Each change is also a line in core__audit (table_name core__sharing_choices).
CREATE TABLE core__sharing_choices (
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL DEFAULT '',
    choice TEXT NOT NULL CHECK (choice IN ('local', 'shared_not_private', 'kinds', 'shared')),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (table_name, column_name)
);
