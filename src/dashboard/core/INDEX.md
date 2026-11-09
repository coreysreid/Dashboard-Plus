# src/dashboard/core/  (summary: core services, nothing topic-specific)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Core services: database, migrations, modules and records; review and backups come next. | adding a core service |
| backups.py | Automatic backups: one a day, one at every safe close, kept in two places. | changing when or where backups are made |
| db.py | Open the SQLite database with settings that are safe on USB drives. | changing how the data file is opened or backed up |
| migrations.py | Apply numbered migrations, one track for the core and one per module. | changing how database changes are applied |
| migrations/ | The core's own numbered database changes | adding a core table |
| modules.py | Find module folders, check their files, and explain any mistakes in plain words. | changing what module files may say |
| records.py | Create, change, delete and read records, checking every value and keeping a history. | changing how records are saved or checked |
| settings.py | Read and write household settings kept in the database (core__settings). | storing a new setting |
| schema.py | Turn a module's declared tables into SQL, and work out its next migration. | changing how tables are built |
| watch.py | Work out what is running low, what expires soon, and how many days of supplies are on hand. | changing running low, expiring or days of cover |
| startup.py | Prepare the database at start-up: load modules, back up if needed, and migrate. | changing what happens at start-up |
