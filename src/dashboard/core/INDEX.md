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
| actions.py | Actions that add a linked record through a small form, like Mark done: one saved operation, a one-use number and Undo. | changing Mark done, its checks or Undo (also Undo of a one-press button, decision 0112) |
| records*.py | Two parts of saving records: "Create, change, delete and read records, checking every value and keeping a history." (records) and "Confirmed purchase prices on a Stock in (decision 0128): what a person typed, whether it is the total or the price for each, the line total worked out from it, and its currency." (records_prices) | changing how records are saved or checked, or how a typed price is checked and its line total worked out |
| prompts.py | Read and check a module's prompts.toml: "Have you thought about…?" questions, their groups, exact record matches and "Think it through" drills. | changing what prompts.toml may say |
| drills.py | Think it through: which drills fit the household, what each step may find in its records, and the practice runs kept with their dates. | changing how drills fit, cite sources, save runs or keep own words private |
| exit_sketch.py | The way-out sketch's facts: rooms by floor, recorded connections and doors to outside, and what still needs checking. | changing what the way-out sketch reads, its route words or Check together |
| questions.py | Which "Have you thought about…?" questions fit the household, what may already be recorded, and how many were looked at. | changing how questions fit, match records, come back or are counted |
| settings.py | Read and write household settings kept in the database (core__settings). | storing a new setting |
| schema.py | Turn a module's declared tables into SQL, and work out its next migration. | changing how tables are built |
| confirm.py | Gentle checks before a form saves, like an odometer reading lower than the last one: shown, never a block (0111). | changing Go back / Save as entered checks |
| suggest.py | Suggestions while typing: a household's own records first, then a module's list of common things. | changing how picking from a list matches |
| watch.py | Work out what is running low, what expires soon, how many days of supplies are on hand, and what is worth filling in. | changing running low, expiring, days of cover or gaps |
| checklist.py | Things to do: Today, This week, This month and This year over the due dates modules already keep (decision 0107). | changing which tasks show, their windows, week start or what counts as done |
| daily.py | Daily totals by the household's own day: accepted entries only, amounts added only in matching units (decision 0110). | changing the household day, daily totals or the possible-repeat match |
| calendars.py | Month calendars from a table's dated or timed records by the household's own day; an empty day is never called missed (decision 0119). | changing the calendar grid, its looks, which records and due dates it shows, or a calendar of a table's own records (0122) |
| bars.py | Bars over time: how often, or how much in one unit, per day, week or month by the household's own day; an empty period is never called missed (decision 0124). | changing which records a bars chart counts, its periods or how amounts add up (a whole list, a category group or money: 0128) |
| timeline.py | One record's timeline: dated entries from every table that links to it and declares `timeline`, newest first, by the household's own day (decision 0126). | changing which entries a timeline lists, their order, a day's summary or its pages |
| startup.py | Prepare the database at start-up: load modules, back up if needed, migrate, and give permanent record IDs. | changing what happens at start-up |
| helper*.py | Two parts of helpers: "The small address file a connector reads to find Dashboard after a restart: only the address and a run ID (0092)." (helper_address) and "Helpers the household has given a key to: making a key, checking it, replacing it, and turning it off." (helpers) | changing how a connector finds Dashboard, or how helper keys work |
| hello.py | Proof that an address is the real Dashboard Plus, worked out from a key without ever sending it (decision 0086). | changing the check the connector makes before sending a key |
| receipts.py | Receipt lines a helper could not match, and receipts sent twice: kept on Review, decided only by a person (0105). | changing receipt lines, Finish receipt review or the repeat-receipt warning |
| proposals.py | Suggestions from helpers and rows imported from a spreadsheet: checked, kept waiting, added only when a person accepts. | changing suggestions, limits or accepting |
| move_in.py | Move-in checks on helper suggestions: a starting amount counted twice, a link sent as a name, private details copied into text. | changing the double-count warning, name matches in refusals or the private-copy warning on Review |
| export.py | Export my records: one zip with a spreadsheet file for every table, a manifest and a plain-words README. | changing what the export contains |
| optional_links.py | Links into an optional module (decision 0115): kept by exact ID while it is off, shown in neutral words, never guessed. | changing what an optional link shows when its module is off or its record is gone |
| reminder_moves.py | One reminder per policy: a household chooses, row by row and by exact ID, to move an older list's reminder into a newer one, and can move it back (0117). | changing takes_over, Move, Keep, Transfer back or which record reminds |
| sync.py | Permanent record IDs, revisions and the filtered change log (sync stage 1): nothing leaves this computer. | changing record IDs, the change log or what may travel to another computer |
| csv_import.py | Read a spreadsheet saved as CSV, match its columns to a table's fields, and check every row before it goes to Review. | changing how spreadsheets are read or matched |
