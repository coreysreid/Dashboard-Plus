# src/dashboard/core/  (summary: core services, nothing topic-specific)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Core services: database, migrations, modules, records, backups, helpers and their suggestions. | adding a core service |
| backups.py | Automatic backups: one a day, one at every safe close, kept in two places. | changing when or where backups are made |
| restore.py | Restore from a backup: check copies without changing them, put one back safely, and undo it. | changing how a backup is checked, put back or undone |
| db.py | Open the SQLite database with settings that are safe on USB drives. | changing how the data file is opened or backed up |
| dates.py | Dates the household's way: typed and shown as 20/05/27 or 05/20/27, always stored as 2027-05-20. | changing how dates are typed or shown |
| naming.py | What to call a record wherever it appears: its name, or for a batch "Kidney beans, 3 tins". | changing how records are named |
| units.py | Say an amount of 1 with its unit in the singular: "1 tube", not "1 tubes". | changing how amounts and units read |
| migrations.py | Apply numbered migrations, one track for the core and one per module. | changing how database changes are applied |
| migrations/ | The core's own numbered database changes | adding a core table |
| modules.py | Find module folders, check their files, and explain any mistakes in plain words. | changing what module files may say |
| records.py | Create, change, delete and read records, checking every value and keeping a history. | changing how records are saved or checked |
| settings.py | Read and write household settings kept in the database (core__settings). | storing a new setting |
| schema.py | Turn a module's declared tables into SQL, and work out its next migration. | changing how tables are built |
| suggest.py | Suggestions while typing: a household's own records first, then a module's list of common things. | changing how picking from a list matches |
| watch.py | Work out what is running low, what expires soon, how many days of supplies are on hand, and what is worth filling in. | changing running low, expiring, days of cover or gaps |
| startup.py | Prepare the database at start-up: load modules, back up if needed, and migrate. | changing what happens at start-up |
| helpers.py | Helpers the household has given a key to: making a key, checking it, and turning it off. | changing how helper keys work |
| proposals.py | Suggestions from helpers and rows imported from a spreadsheet: checked, kept waiting, added only when a person accepts. | changing suggestions, limits or accepting |
| export.py | Export my records: one zip with a spreadsheet file for every table, a manifest and a plain-words README. | changing what the export contains |
| csv_import.py | Read a spreadsheet saved as CSV, match its columns to a table's fields, and check every row before it goes to Review. | changing how spreadsheets are read or matched |
