# src/dashboard/core/  (summary: core services, nothing topic-specific)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Core services: database, migrations and modules now; records, review and backups next. | adding a core service |
| db.py | Open the SQLite database with settings that are safe on USB drives. | changing how the data file is opened or backed up |
| migrations.py | Apply numbered migrations, one track for the core and one per module. | changing how database changes are applied |
| migrations/ | The core's own numbered database changes | adding a core table |
| modules.py | Find module folders, check their files, and explain any mistakes in plain words. | changing what module files may say |
| schema.py | Turn a module's declared tables into SQL, and work out its next migration. | changing how tables are built |
| startup.py | Prepare the database at start-up: load modules, back up if needed, and migrate. | changing what happens at start-up |
