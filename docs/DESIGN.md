# Design

This document says how Dashboard Plus will be built. It is written so a
newcomer can follow it. Section 15 lists the decisions that Corey needs to
confirm before code is written; each has a recommendation in plain language.

Contents: 1 Layers · 2 Folders · 3 Object model · 4 Links · 5 Time ·
6 Modules · 7 Migrations · 8 Review and inbox · 9 Agent API ·
10 Annotations and the question loop · 11 Audit, backup, export ·
12 Security and privacy · 13 Packaging · 14 Testing and CI ·
15 Decisions and their records · 16 Build order · 17 Agent-friendly layout

## 1. Layers

```text
Browser (on this computer)
   |  http://127.0.0.1:<port>
Web layer         pages, forms, grid, review screen, JSON API
   |
Core services     records, links, time, review, audit, annotations,
                  question loop, backups, module loader, migrations
   |
SQLite file       data/dashboard.db  (stable, single file)
   ^
Modules           files that describe tables/labels/insights,
                  optionally Python that fetches or proposes data
```

Rule: modules talk to core services, never to SQLite directly. Core services
never mention any particular topic.

## 2. Folders

The program and the data are separate. Updating means replacing the program
folder and keeping `data/`.

```text
Dashboard/                      <- the portable folder (or the git clone)
  Open Dashboard.bat            starts the program and opens the browser
  Close Dashboard safely.bat    stops it cleanly
  app/                          program code (replaced on update)
    core/  web/  modules/  python/  (bundled interpreter + libraries)
  data/                         YOUR data (kept on update, never committed)
    dashboard.db
    config.toml                 real settings, written by the wizard
    secrets/                    API keys and agent token hashes
    backups/  exports/  attachments/  reports/
```

In the git repository only `config.example.toml` exists. `data/` is in
`.gitignore`, and CI fails if a database, a `config.toml`, a token-looking
string or a personal path is committed (section 14).

A second automatic backup is also written to a folder on the computer itself
(for example under the user's local app data), because a USB stick can be lost
or corrupted. The location is a setting.

## 3. Object model

Everything a person tracks is a **record** in a **table**. Tables are declared
by modules (section 6); the core turns them into real SQLite tables.

Every table automatically gets these system columns, so features like review,
audit and undo work for every module without module code:

| Column | Meaning |
|---|---|
| `id` | Integer primary key |
| `created_at`, `updated_at` | Timestamps (UTC, ISO 8601 text) |
| `review_status` | `confirmed`, `needs_review` or `rejected` |
| `source` | `person`, `agent:<name>`, `import:<source>` or `module:<name>` |
| `batch_id` | The batch that created it, if any (for undo) |
| `edited_by_person` | 1 once a person has edited it (locks out agents) |
| `deleted_at` | Soft delete; undo and history rely on this |

### Field types

`text`, `longtext`, `integer`, `decimal`, `boolean`, `date`, `datetime`,
`choice` (one value from a dropdown), `link` (one record in another table),
`links` (many records, section 4), `money` (integer minor units plus a currency
code), `measure` (a number with a unit, used by analysis), `file` (path inside
`data/attachments/`).

Each column may declare: `required`, `default`, `min`, `max`, `unit`,
`choices` (the dropdown values, each with a stable key and a friendly label),
`sensitive` (hidden by default, kept from helpers unless granted; see
section 12) and `help` text.

Dropdown values are stored by stable key (`dry_food`), shown by label
("Dry food"). Renaming a label never changes stored data.

### Declared, not hard-coded

The same declaration drives the entry grid, the forms, the review screen, the
API's live column list, validation and the export. There is exactly one place
to change a field.

### Real tables, not a single generic table

Each declared table becomes a real SQLite table named `<module>__<table>`
(for example `pets__weights`). This keeps queries fast and the file readable
by any SQLite tool, which supports the no-lock-in promise. Generated column
types and constraints come from the declaration; the core adds indexes on link
columns and date columns automatically.

## 4. Links between records

Links exist from day one. Three kinds:

1. **Belongs to (many-to-one).** A column of type `link` pointing at another
   table. A vet visit belongs to a pet. Stored as a foreign key. The
   declaration says what happens when the parent is removed: `restrict`
   (default; refuse and explain), `cascade` (soft-delete the children too) or
   `clear` (set the link empty).
2. **Many-to-many.** A column of type `links`. The core creates a small join
   table. A project can involve many people; a person can be on many projects.
3. **About (generic).** A core table `core__about` ties a *note, annotation,
   event, attachment or inbox item* to any record in any table
   (`target_table`, `target_id`). This is how a note "about the cat" or a photo
   "about the leaking tap" works without every table needing a notes column.

Cross-module links are allowed only through an explicit `requires` entry in
`module.toml`, so removing a module cannot silently orphan another module's
data. The loader refuses to switch off a module that another enabled module
depends on, and says which one.

## 5. Time

Time is first-class because the question loop depends on it.

- **Dates and times.** Stored as ISO 8601 text. A household has one configured
  time zone; "a day" always means a local calendar day.
- **Events.** A core `core__events` table: a title, a start date (and optional
  end date), an optional recurrence, an optional "about" link, and a kind
  (`note`, `milestone`, `appointment`, `annotation`, `external`). Events are
  what analysis searches when it looks for explanations.
- **Recurrence.** A small, closed set: daily, weekly (chosen weekdays),
  monthly (day of month or "last Friday"), yearly; an interval; and an end date
  or count. Occurrences are calculated on demand for a date range and not
  stored in bulk. No free-form calendar rules.
- **Daily facts.** Each module may expose a *daily facts* view: one row per
  local day with the numbers that matter (for Pets: grams eaten, weight,
  medication given). Charts and analysis read these views only, so the idea of
  "the number for a day" is defined in one place per module. Where the person's
  sheet disagrees on detail but agrees on the day's total, the total wins
  (section 6, Pets).

### 5.1 Watch views (resilience in the core)

A table opts in with a `watch` section in `tables.toml`. The core then shows the
results across all modules on the home page and on shared pages. They are views,
not alarms: nothing is sent anywhere.

```toml
[tables.items.watch]
# Running low: rows where quantity < minimum (both columns of this table).
running_low = { quantity = "quantity", minimum = "minimum" }
# Expiring soon: rows whose date falls within warn_days (default 30); past dates show as expired.
expiring = { date = "expires", warn_days = 30 }
# Days of cover for the household, for rows matching `where`.
supply = { quantity = "quantity", per_person_per_day = 3, per_pet_per_day = 0,
           target_days = 3, unit = "litres", label = "water", where = { category = "water" } }
```

- `running_low` and `expiring` name columns of the same table; `quantity` and
  `minimum` must be number columns, `date` a date column. Checked when the
  module loads, with plain-language errors like everything else.
- `supply` adds up `quantity` for matching rows and divides by the household's
  daily need. **Household size** comes from the People module (rows of
  `people__people` with `lives_here` set) when it is installed, otherwise from
  the `household.people` setting the wizard writes. Pets count from the
  `household.pets` setting in M1. The page shows the working ("2 × 10 litres
  for 3 people at 3 litres a day = about 2 days") and says the daily figures
  are a starting point, local advice comes first.
- Watch results always leave out deleted rows.

### 5.2 Printable sheets

A module may declare one-page printable sheets in `sheets.toml`, rendered by the
core at `/sheet/<module>/<name>` with print-friendly styling and no internet
needed. The People module uses this for the emergency sheet.

```toml
[[sheet]]
name = "emergency"
title = "Emergency sheet"
intro = "Keep a printed copy on the fridge."

[[sheet.section]]
title = "Who lives here"
table = "people"                      # a table of this module
where = { lives_here = true }         # equality filters only
columns = ["name", "phone"]
order_by = "name"

[[sheet.section]]
title = "Who to call"
table = "roles"
columns = ["role", "person", "person.phone"]
order_by = "priority"
```

A column written as `link.column` (for example `person.phone`) prints a column
of the record the link points at, within the same module. Sensitive columns are
printed only if a section lists them explicitly, and the page says they are
included.

### 5.3 Records that change a count (stock in and out)

A table may declare that each of its records adds to or takes from a number on a
linked record. Household stock uses it so buying, using or throwing something
away updates the item's count by itself.

```toml
[tables.movements.adjusts]
link = "item"          # a link column of this table, to a table of this module
quantity = "quantity"  # the number column on the linked record that changes
amount = "amount"      # the number column of this table: how much
direction = "reason"   # a choice column of this table
adds = ["bought"]      # choices that add; every other choice takes away
```

- The change happens in the same step as saving the record, and appears in the
  linked record's history.
- Taking away more than there is is refused with a plain message; correcting the
  count itself (a stocktake) is done by editing the linked record directly.
- Changing a record corrects the count; deleting it undoes its effect;
  restoring it applies it again.
- A date column may use `default = "today"`.
- On a record's page, every table that links to it offers an "Add to …" button
  with the link filled in, and saving returns to that record.

### 5.4 Gaps: details worth filling in

A table may list `gaps` in its `watch` section: details a household would want
written down before they are needed. The core asks each one as a question under
*Worth filling in* on the Needs attention page, with a link to the place to
fill it in, and counts them on the home page. Nothing is sent anywhere.

```toml
[[tables.roles.watch.gaps]]
none = { role = "emergency_contact" }     # asked when no row matches
message = "Who would you call first in an emergency? Nobody is listed as an emergency contact yet."

[[tables.roles.watch.gaps]]
missing = "person.phone"                  # asked for each row where this is blank
where = { role = "doctor" }               # optional equality filters
message = "What is {person}'s phone number?"
```

- Each gap uses either `none` (equality filters; asked when no row matches,
  linking to a new-record form with the filters filled in) or `missing` (a
  column of this table, or `link.column` within the module; asked per row where
  it is blank, linking to the record that holds the blank). `missing` asks once
  per linked record, even when several rows point at it.
- `{column}` in a `missing` message is filled in from the row as a person reads
  it (a link shows the record's name, a choice its label). A `none` message has
  no row, so it cannot use `{...}`.
- Messages ask; they do not assert or judge. Ask only what nearly every
  household would want answered; anything that depends on the household's
  situation belongs in prompts (section 10.5), which can be answered "not
  relevant". Gaps have no "not relevant" answer in M1: they stop when filled in.
- Deleted rows are left out.

## 6. Modules

A module is a folder:

```text
modules/<name>/
  module.toml       name, version, description, core_api needed,
                    requires, outbound hosts
  tables.toml       tables, columns, types, dropdown values, links
  labels.toml       friendly names and form layout
  migrations/       numbered migration files for this module's own track
  sources.py        optional: pulls data in
  insights.toml     optional: what the question loop should watch
```

### Tier 1: declarative modules (files only)

Only `.toml` files. No code runs. The core builds everything. Safe by
construction. Anyone can write one, and an AI assistant can write one from a
sentence. The loader validates every file against a schema and gives errors in
plain language ("In `tables.toml`, table `weights`, column `kg`: unknown type
`numbr`. Did you mean `number`? Allowed: ...").

`module.toml`:

```toml
name = "pets"
title = "Pets"
version = "1.0.0"
description = "Track pets, their weight, food, medication and vet visits."
core_api = "1"                 # the contract version this module was written for
requires = []                  # other modules this one links into
outbound_hosts = []            # empty for modules that never contact anything
kind = "declarative"           # or "code"
```

`tables.toml` (shortened):

```toml
[tables.pets]
title = "Pets"
columns.name     = { type = "text", required = true }
columns.species  = { type = "choice", choices = ["cat", "dog", "rabbit", "other"] }
columns.born     = { type = "date" }

[tables.weights]
title = "Weigh-ins"
columns.pet      = { type = "link", to = "pets", required = true, on_delete = "restrict" }
columns.weighed  = { type = "date", required = true }
columns.weight   = { type = "measure", unit = "kg", min = 0 }
daily_fact = { date = "weighed", subject = "pet", measures = ["weight"] }
```

`labels.toml` supplies friendly names, help text, column order and which
columns appear on the quick-entry form.

### Tier 2: code modules

Add `sources.py` (and may add custom checks). Code modules run with the user's
own permissions, exactly like any program the user installs. The interface
says so plainly before a code module is switched on ("This module includes
program code that can read and change files on this computer. Only turn it on
if you trust where it came from"), and the README repeats it. The core does not
try to sandbox Python; it limits the damage a *buggy* module can do (section
below) but does not claim to stop a *malicious* one.

A code module imports only the **toolkit**, a small stable surface:

```python
from dashboard_toolkit import fetch, propose, alert, log, secret

def pull(ctx):
    data = fetch.json(ctx.source.url)          # honours the host allow-list
    propose(table="weather__readings",
            entries=[{"day": ..., "max_temp": ...}],
            why="Daily weather from <source>")  # lands as needs_review or
                                                # confirmed, per module setting
```

- `fetch.json / fetch.text` enforce the allow-list, timeout, retries and rate
  limit, and record every attempt.
- `propose` writes through the same path as the Agent API (batch, audit,
  review flag).
- `alert` raises a visible notice. `log` writes to the module's log.
- `secret(name)` reads from `data/secrets/`; modules never see other modules'
  secrets.

### Failure isolation

The loader runs each module's startup, each source and each insight inside its
own guarded call. An exception or timeout marks that module "unavailable",
shows a plain message and a *Save a report* button, and everything else keeps
running. A module that fails to load never prevents the app starting.

### Version contract

`core_api = "1"` means "written for contract version 1". The core supports
contract version 1 for the whole 1.x life of the program. A module asking for a
newer contract is refused politely. Contract-breaking changes require a new
number and the core can load both for a transition period.

### v1 modules

- **Pets** (declarative). Tables: pets, weights, meals (item, amount, time),
  daily food totals, medications and doses given, vet visits, litter or walk
  logs. Not tied to one animal: species is a choice, and every record links to
  a pet. Supports entering data off paper (below).
- **People** (declarative; on by default; a pillar of resilience). Tables:
  - *people*: name, preferred name, lives here (yes/no), relationship, birthday,
    phone, email, address, notes.
  - *roles*: a person and a role (emergency contact, family, neighbour, doctor,
    dentist, vet, tradesperson, school, workplace, key holder, other) with a
    priority order, so "who do I call first" has an answer.
  - *important_info*: a person and a kind (allergy, condition, medication,
    care or mobility need, dietary, access instructions, other) with detail.
    These columns are marked `sensitive`.
  - *dates*: birthdays, anniversaries and appointments; these recur through
    core events.
  - Behaviour: a **Who do I call?** view by role, a **printable emergency
    sheet** (one page, offline, household members first), and a **gaps** check
    ("your emergency contact has no phone number"). The first-run wizard writes
    "who lives here" into this module. Pets link their owner and vet to people,
    through `requires = ["people"]`. This is a notebook with a print button, not
    a medical record (see the non-goals).
- **Medical** (declarative; requires People and Household stock). Tables:
  - *kits*: a first aid kit (name, where it is kept, when it was last checked,
    how often to check it).
  - *kit contents* are ordinary Household stock items in the first-aid
    category, each with a minimum and an expiry date, so the shared "running
    low" and "expiring soon" views cover the kit with no extra code.
  - *training*: a person, a course (first aid, CPR, other), the provider, the
    date completed and when it needs renewing; renewals appear in the same
    expiry view.
  - Medical contacts (doctor, pharmacist, nearest hospital) are People roles.
    Allergies, conditions and medications stay in People's sensitive details.
  - Behaviour: *kit check due*, *training due*, and prompts such as "Is there a
    first aid kit?" and "Does anyone here know how to use it?". The module does
    not give medical instruction or diagnose; it records what the household has
    and links to guidance from recognised first aid and health bodies.
- **Readiness** (declarative; the home of the prompts in section 10.5).
  Tables: plans (a situation the household has thought through: what we would
  do, who does what, the answer to "could we get down from upstairs?"), drills
  (date, who took part, what we learned), and the household's answers to
  prompts. It ships household-wide prompts for every pillar plus optional
  **country packs** (below). Behaviour: the "Have you thought about…?" panel,
  the coverage view, and review reminders.
- **Household stock** (declarative; the resilience heart of v1). Tables:
  items (name, category such as pantry, water, medical, tool, hardware, fuel;
  unit; location), stock (current quantity, minimum, target, expiry date, where
  stored), purchases (a weekly shopping receipt: shop, date, total, with lines
  linking to items and quantities), movements (stock in and out, each with a
  reason: used, expired, discarded, gifted, bought, so waste can be measured),
  and places (shelf, cupboard, garage box, so "where is the ladder?" has an
  answer). Behaviour comes from files plus
  the core's watch views (section 5.1), not module code:
  - *Running low* and *Expiring soon* lists.
  - *Supply cover* for emergency basics: the household's people and pets come
    from the first-run wizard; the module declares a per-person and per-pet
    daily need and a target number of days. The household sees plain language
    ("about 2 days of water; about 12 litres short of 3 days"). The default
    figures are a starting point the household can change, and the advice of
    its own country or local authority takes priority.
  - *Receipt in, stock up:* a receipt entered by hand or proposed from a photo
    through the inbox arrives as reviewable rows; approving them raises the
    stock levels. Nothing changes stock until a person approves.
  - Tools and hardware work the same way as pantry items (a quantity, a
    minimum, a place), so "which screws do I have, which do I need" is a list.
- **Vegetable garden** (declarative; the worked example for module authors).
  Tables: beds (name, kind, size, sun), crops (name, variety, days to harvest),
  plantings (crop, bed, sown or planted date), harvests (date, planting,
  quantity, unit, weight), garden jobs (watering, feeding, pest notes, which
  recur as events), and water used. It is the best teaching example because it
  touches everything: seeds are stock items, seasons are time, weather arrives
  from the API connector, jobs are recurring events, and the outcome is a
  money-saved figure. A step-by-step "build this module" guide uses it. It is
  an optional module, off unless chosen in the wizard.
- **Wine collection** (declarative; a serious module for collectors, kept compact on purpose so it also shows how little a new module takes). Tables: wines (name, producer, vintage,
  region, grape), bottles or stock (quantity, location, bought, price), tasting
  notes. About one page of files; its purpose is to prove how easy a module is.
- **Graphing** (module). Charts over any table or measure or daily-fact view,
  using one well-trodden JavaScript charting library (see section 15). Chart
  configurations are saved as records. Annotations and events are drawn on
  charts.
- **Analysis** (module, section 10.3).
- **API connector** (module, section 6.1).

#### Entering data off paper (Pets)

The module's quick-entry and agent guidance follow the lessons from the
original project:

- File in two passes: first the items (bowls, doses, meals), then the checks
  and totals. Link related rows by id.
- Verify with a dry run on a copy of the database before committing.
- A day's total is what the person cares about most. Where two sheets
  disagree on the detail but agree on the total, keep one version and add a
  note with the other.
- When a written total disagrees with the parts, file the calculated figure
  and add a note mentioning the written figure.
- The aim is "a quick picture", not exact grams.

#### 6.1 API connector module

One generic connector that can be aimed at any API.

- A **source** record has: name, URL, optional key (stored in
  `data/secrets/`), schedule (every N hours or daily at a time), target table
  and a **mapping** from JSON paths in the response to columns.
- **Raw responses are kept** (`data/raw/<source>/<timestamp>.json`, with
  retention so it does not grow forever) so rows can be rebuilt when the
  mapping changes.
- **Attempts are recorded** for every fetch: when, HTTP status or error, rows
  added, duration. A failing source shows "unavailable" with the last good
  time; it never crashes the app.
- Built-in timeouts (default 15 s), retries with backoff (default 3), rate
  limit per host, and a response size cap.
- **Safety.** Only hosts the user has added to the allow-list are contacted.
  URLs are never taken from stored data (no user-supplied URLs inside rows),
  so a stolen or imported row cannot redirect traffic. Requests include no
  personal data. Redirects to a host not on the list are refused. Private and
  loopback addresses (for a smart-home hub) are allowed only if the user has
  added that exact address, with an explanation of what it means.
- **Documented examples:** weather alerts, exchange rates, a smart-home hub's
  local API. Home Assistant integration is a future idea.
- Mapping parsers are tested with **fixtures**: saved real responses with
  anything personal removed.

## 7. Migrations

- Numbered, linear, forward-only: `0001`, `0002`, ... Each is a SQL file (or a
  small TOML description the core turns into SQL) plus a checksum.
- **One track per module.** The core has its own track (`core`). A module's
  track starts at `0001` when it is first switched on. Adding, removing or
  re-ordering modules cannot disturb any other track's numbering.
- A table `core__migrations(track, number, name, checksum, applied_at)` records
  what has run. A checksum mismatch (a migration edited after release) stops
  startup for that track with a clear message.
- The database also stores its overall version in `PRAGMA user_version` and the
  list of enabled modules with their versions, so a file can be inspected
  without the program.
- **Generated migrations.** For declarative modules, a developer command
  compares `tables.toml` with the last recorded schema and writes the next
  migration (add table, add column, add index). Destructive or ambiguous
  changes (rename, drop, change type) need a hand-written migration. Generated
  migrations are committed; the program never changes the database from a
  `tables.toml` edit alone.
- **Order on start:** back up automatically if any migration is pending → run
  core track → run each enabled module's track in dependency order → record the
  result. If any migration fails, the transaction rolls back, the pre-update
  backup is offered for restore, and a plain message appears.
- **Switching a module off** hides it and keeps its data. **Removing its data**
  is a separate, confirmed, backed-up action.
- Storage changes are made only through migrations, never by ad-hoc code.

## 8. Review and inbox

### Review queue

Rows with `review_status = needs_review` appear on the **Review** screen,
grouped by batch, each showing who or what proposed it and why. The person can
approve, edit-then-approve, or reject. Approving or editing marks
`edited_by_person` where applicable. Rejected rows stay in history (hidden by
default).

### Inbox

The **Inbox** holds unsorted items: a photo, a pasted note, a forwarded email's
text. Each item has a type, a file or text, and a received time. The core asks
the sorting logic for a **proposed destination** (a table and pre-filled values,
or "just a note about <record>"), shown as a suggestion the person accepts,
changes or discards. In v1, proposals come from simple rules in modules
(for example, a filename pattern or keyword) and from agents using the Agent
API; the core does not call an AI service by itself.

## 9. Agent API

Assistants, whether AI or human helpers, enter data through the API and never
touch the database. The API listens on `127.0.0.1` only, the same as the rest
of the program.

### Authentication

`Authorization: Bearer <token>`. Tokens are 32 random bytes, shown once when
issued, and stored only as a SHA-256 hash (adequate for high-entropy random
tokens). A command-line tool issues, lists and revokes them:

```text
dashboard agent add "<name>" --tables pets__weights,pets__meals
dashboard agent revoke "<name>"
```

Each agent has a name and a list of tables it may touch. Anything else is
refused.

### Routes

| Route | Purpose |
|---|---|
| `POST /api/propose` | Propose rows (below) |
| `GET /api/tables` | Live column spec: field names, types and dropdown keys. The source of truth; agents must read it rather than guess |
| `GET /api/rows` | Read rows (only tables the agent is allowed) |
| `POST /api/amend` | Change one of the agent's own *unreviewed* rows |
| `POST /api/undo` | Withdraw the agent's own *unreviewed* rows (a row, or a whole batch) |
| `GET /api/batches` | List the agent's batches and their state |

`POST /api/propose` body:

```json
{
  "request_key": "2026-06-03-sheet-14",
  "why": "Transcribed from the paper feeding sheet for 3 June",
  "entries": [
    { "table": "pets__meals", "values": { "pet": 1, "...": "..." } }
  ]
}
```

### Rules

- `request_key` is **required**. Repeating a call with the same key from the
  same agent returns the original result and writes nothing new (idempotent
  retries). Keys are remembered for 30 days.
- At most **50 entries per call** and **200 rows per agent per day**.
- Rows land with `review_status = needs_review`, `source = agent:<name>` and a
  `batch_id`. Every call is one batch, so it can be undone together.
- Once the **person edits** a row, `edited_by_person` is set and the agent can no
  longer amend or undo it.
- An agent can fix or withdraw **only its own unreviewed rows**.
- Columns marked `sensitive` (allergies, conditions, medications) are never
  returned to an agent and cannot be written by one unless the token was issued
  with `--sensitive`, and the Settings screen shows which agents have it.
- Validation uses the same declaration as the forms. Errors name the table,
  the field and the allowed values, in plain language, so an AI helper can
  correct itself.
- Rows written outside the API have no batch and cannot be undone together,
  so the core provides no other write path for agents.

## 10. Annotations and the question loop

### 10.1 Annotations

An **annotation** is a confirmed statement of the form "something happened here
that may matter": a date or date range, a short text, an optional "about" link,
and an optional **effect**: `exclude` (leave these days out of averages),
`explain` (this is a known reason), or `note` (display only). Annotations are
drawn on charts and used by analysis. Annotations are only ever created by a
person, either directly or by answering a question.

### 10.2 The loop

```text
 detect  ->  gather candidates  ->  ask  ->  remember
```

1. **Detect.** `insights.toml` declares what to watch. A detector runs over a
   daily-facts measure and flags a **change**: for example, a shift in the mean
   between two periods found by change-point detection that passes the
   guardrails in 10.3.
2. **Gather candidates.** Around the change date (a window of about ±14 days by
   default) the core collects events, notes, annotations, and notable changes in
   other watched measures. Candidates are ranked by closeness in time and by
   text match with what was changed.
3. **Ask.** A **Question** is created and shown in a *Questions* panel:
   > "Food eaten went up about 30% from 3 June (based on 41 days). Your notes
   > say a new job started on 3 June. Is that related?"  
   > **Yes / No / Not sure**
4. **Remember.**
   - **Yes** creates an annotation (`explain`, linked to the event and the
     measure) shown on the chart. The person may also choose whether later
     averages should treat the new period separately.
   - **No** records that this pairing was rejected, and it is not asked again.
   - **Not sure** snoozes it; it may return once more when there is more data.
   - Unanswered questions expire quietly after a configurable time.

Questions are always phrased with "may", "could" and "is this related", never
"because". A question states how many days it is based on. The number of open
questions shown at once is capped so the panel is helpful and not nagging.

#### Asking sensible questions

Time closeness alone is a bad reason to ask. Tyre wear and the garden hose will
both drift over a summer, which proves nothing. So a candidate must pass a
**plausibility gate** before time closeness is even considered:

1. **Declared topics.** Modules tag their measures and events with topics
   (`food`, `weather`, `routine`, `pet-health`, `money`, `garden`, `vehicle`).
   A watch lists the topics it may be explained by. Anything outside those
   topics is never a candidate. By default only the same subject (the same pet)
   or the same module qualifies; crossing modules needs an explicit declaration.
2. **Both tests.** A candidate needs plausibility *and* time closeness. Close in
   time but not plausible: dropped. Plausible but far away: dropped.
3. **A fourth answer: "That doesn't make sense."** Besides Yes / No / Not sure,
   this stops that topic pairing for this household for good, and is counted so
   we learn which declarations are poor. After repeated dismissals the program
   quietly mutes that kind of question.
4. **Budget.** A small cap on questions per week, and a preference for the ones
   that are most plausible and best supported by data.
5. **Explore mode.** A person can deliberately compare any two measures they
   like. This is labelled exploratory, uses a stricter correction for the
   number of comparisons, and says "no obvious reason these would be linked"
   when topics do not overlap. The decision to look is theirs.

A side benefit: asking about fewer pairs also shrinks the multiple-comparison
penalty in section 10.3, so real findings are easier to detect.

`insights.toml` (example):

```toml
[[watch]]
measure = "pets__daily_food.grams_eaten"
subject = "pet"                       # compute separately for each pet
detect = "change_point"               # change_point | trend | threshold
min_points = 20
look_in = ["core__events", "core__notes"]
may_relate_to = ["routine", "weather", "pet-health", "food"]   # plausibility gate
window_days = 14
phrase = "{measure_label} {direction} about {percent}% from {date}"
```

### 10.3 The Analysis module

Basic, honest statistics running locally. Standard library by default, with at
most one small, pinned dependency if it is clearly worth it (decision record 0005).

- **Correlation:** Pearson, and Spearman for skewed data.
- **Lagged correlation:** "hotter yesterday" (shift one series by N days).
- **Forecast error:** RMSE and mean error between a forecast and actual values.
- **Change-point detection:** "something shifted in June."
- **Day-of-week and month averages.**

**Guardrails are mandatory and live in one place, not scattered:**

1. A **minimum number of paired points** (about 20) before anything is shown;
   below that, the page says how many more days are needed.
2. Every result states **how many days** it is based on.
3. **Multiple-comparison correction.** When many pairs are tested at once
   (for example every measure against every other), significance thresholds
   are corrected (Benjamini–Hochberg false-discovery control; Holm–Bonferroni
   for small families). The number of comparisons made is displayed.
4. Language: "associated with", never "caused by". Correlation results show the
   direction, strength in words, and a small plot.
5. Findings flow into the question loop as questions, not as conclusions.
6. Annotations with effect `exclude` are honoured; excluded days are listed.

v1 includes **one correlation view**: pick two measures, see the scatter or
paired lines, the correlation, the lag that fits best, the number of days and
the correction note. Example questions the person cares about: do days with
less eating tend to be hotter? Do takeaway purchases line up with recurring
meetings?

### 10.4 Outcomes: showing the difference it made

The loop explains changes. Outcomes answer the question "was it worth my
time?". Two parts, both local.

**Metrics.** A module can declare metrics in `insights.toml`:

```toml
[[metric]]
name = "Food waste"
measure = "stock__movements.discarded_value"   # a daily-facts measure
per = "month"
compare = "previous_period"
good_direction = "down"
phrase = "Food waste is {change} from last {period} ({days} days of records)"
```

The core computes the figure for each period, compares it with the previous
one, and states the basis. Nothing is shown until there are at least two full
periods to compare, and the screen says "collecting your baseline" until then.
When a metric moves right after a change the household made (started using the
reorder list), the program asks whether the two are related, using the same
question loop and plausibility rules. It never claims the cause itself.

**Wins.** A *win* is a record in `core__outcomes`: a kind (money saved, time
saved, waste avoided, caught early, shortage avoided), a title, an amount and
unit if there is one, the records it rests on (linked through "about"), and a
status (`proposed`, `confirmed`, `dismissed`). Wins come from three places:

- *Computed from records*, with the basis shown: "no stock-outs on the essentials
  list this month".
- *Proposed as a question*, then confirmed by a person: "You had soup kits on
  four nights and no takeaway on those nights. Did the kits replace takeaway?"
  A Yes records the win. A saving in money uses the household's own typical
  takeaway cost, entered once, never a guess.
- *Recorded by the person*: after a vet visit, "Did your records help?" and a
  note. "Caught early because you tracked three months of food intake" is a win
  linked to those months of records.

**The monthly screen** ("What your records did for you") shows the metrics
against last period, the confirmed wins with their evidence, items rotated
before expiry, days of cover against target, and what is still collecting a
baseline. Every item has *Was this useful? Yes / No*.

**Learning whether it works, privately.** Usefulness answers, the share of
questions answered, and the count of "that doesn't make sense" replies are kept
locally. A *Usefulness report* button saves a small file of counts only (no
names, no content) that a household may choose to send to the maintainers. There
is no automatic reporting of any kind (see the non-goals). Over time this is how
we find out whether the product delivers the experience intended.

### 10.5 Prompts: helping a household think

The question loop (10.2) explains a change in the numbers. **Prompts** surface
blind spots before anything has changed. They are a small core feature (an
engine that reads prompt files, matches them to the household, records answers,
and schedules reviews). The content lives in modules, so the core still knows
nothing about fire, floods or first aid.

**A prompt** is a declared question in a module's `prompts.toml`:

```toml
[[prompt]]                      # illustrative example
id = "escape-upper-floor"
pillar = "shelter-and-escape"
ask = "If you were on an upper floor and the stairs were blocked, could you get down?"
applies_when = { storeys_min = 2 }
when_missing = { table = "readiness__plans", where = { situation = "upper-floor-escape" } }
why = "People plan for the front door and forget the second way out."
how_to_check = "Walk it through in daylight and write down what you found."
record_in = "readiness__plans"
review_every_days = 365
sources = [ { title = "<public safety body>", url = "<link>", retrieved = "<date>" } ]
```

- **`applies_when`** matches the household profile (storeys, pets, region,
  hazards, mobility needs). A prompt that does not apply is never shown. This is
  the same plausibility principle as 10.2: ask sensibly.
- **`when_missing`** stops a prompt appearing when the answer is already in the
  data (for example a first aid kit item already exists in stock).
- **Answers:** *Yes, sorted* (records the date and an optional note, and can
  create a plan), *Not relevant to us* (stops it, and the reason is kept),
  *Not yet, remind me* (snoozes), *Tell me more* (shows why, how to check and
  sources). Answers are dated and return after `review_every_days`.
- **Pillars:** people, medical, water, food, shelter and escape, power and light,
  communication, documents and money, pets, home and tools. The **coverage
  view** shows, for each pillar, how many applicable prompts have been looked at.
  The words are always "looked at", never "safe" or "prepared".
- **Budget and calm:** a small number of prompts at a time, most important
  first, never alarming in tone. They are questions, not warnings.
- Wording rule: prompts ask and point; they never instruct on emergency or
  medical action. Where action matters, they link to the official source.

**Country packs.** A pack is data under `modules/readiness/packs/<country>/`:
`pack.toml` (country, authorities and their links, emergency numbers, the
hazards those authorities list, licence of any text reused, date gathered, a
`review_by` date) and a `prompts.toml` for that country. Rules:

1. Every fact has a **cited, dated source** from an official or recognised
   body, written as "According to <source>, <year>, …", never as our own claim.
2. Only text whose licence allows reuse is reproduced. Otherwise we link and
   describe in our own words.
3. **No unsourced statistics.** A line such as "the most common causes of home
   incidents are…" appears only if a citable source says so, with its year;
   otherwise the pack links to where the household can find it. No such
   statistic is included yet.
4. Every pack ends with a prompt to check the household's own local authority,
   council or emergency service, because risk varies by address.
5. Packs are built from research with citations and reviewed by someone who
   lives there where possible. Start with countries that publish official,
   openly usable guidance (recommended first: Australia and the United States).
6. The weekly health-check Action (section 14) checks that every pack link still
   works and flags packs past their `review_by` date.

**For countries without a pack,** a generic *Find your local guidance* set of
prompts helps people do their own research: which hazards affect my address,
what do the council's maps show, where is the evacuation route, who is my local
emergency service, what do the national emergency management pages say.

**Profile and privacy.** The profile stays on the computer. The country is used
only to choose which pack applies; nothing is looked up online.

## 11. Audit, backup, export

- **Audit.** `core__audit(id, at, actor, action, table, record_id, before,
  after, batch_id)`. The actor is `person`, `agent:<name>`, `module:<name>` or
  `system`. Every write goes through core services, so every write is audited.
  A history panel on each record shows what changed.
- **Undo.** Undo reverses a person's last change, or an agent's batch,
  using the audit before/after. Undo is itself audited.
- **Backups.** A consistent copy using SQLite's online backup, daily and before
  any migration, plus a copy on the computer's own disk. Kept for a configured
  number of days; the latest of each kind is never deleted automatically.
  Backups are verified by opening them and running `PRAGMA integrity_check`.
- **Restore.** One click on the Backups screen. Restoring first backs up the
  current state, so a restore can be undone too.
- **Export everything.** One click writes a folder: one CSV per table (with
  dropdown labels and keys, link columns resolved to readable names), the
  attachments, the notes and annotations as plain text/Markdown, and a
  `README.txt` explaining each file. Nothing in it requires this program.

## 12. Security and privacy

- **Local only.** The web server binds to `127.0.0.1`, never `0.0.0.0`.
- **Browser protections.** A random per-start session secret is placed in the
  launch URL and stored in a cookie. The server checks the `Host` header
  (defends against DNS-rebinding), uses `SameSite` cookies and checks the
  `Origin` header on writes (defends against other web pages talking to the
  local server).
- **The Agent API** uses bearer tokens as described. It is on the same local
  port; there is no remote option.
- **Outside contact is opt-in and listed.** Each module's `module.toml` lists
  the hosts it may contact. The Settings screen shows them all in one place.
  Nothing contacts anywhere until the person switches a source on.
- **Sensitive details.** Columns marked `sensitive` (allergies, conditions,
  medications, access instructions) are masked on screen until the person
  chooses to show them, are kept from helpers unless granted, and are included
  in the person's own export and backups like all other data. They never appear
  in the repository, in logs, or in a *Save a report* file.
- **Secrets** (API keys, token hashes) live in `data/secrets/`, never in the
  repository, never in exports, and never in backups of the config unless the
  person chooses.
- **Code modules** run with the user's permissions and are labelled as such
  (section 6).
- **Dependencies** are few, pinned to exact versions, and bundled.
- **Privacy in the repository.** No real names, personal data, tokens, `.db`
  files or personal paths. Tests and demos use synthetic data. CI enforces this
  (section 14).
- **Errors.** The user sees plain language. Stack traces go to a log file; a
  *Save a report* button writes a zip with the log and non-personal diagnostics
  for the person to share if they choose.

## 13. Packaging

### Portable Windows folder

- Bundles Python and all libraries inside `app/python`. Does not touch the
  registry, PATH or any system Python, and needs no admin rights.
- `Open Dashboard.bat` runs the bundled Python, starts the server on a free
  local port, opens the default browser, and waits.
- **Close Dashboard safely** is a button in the app (and a second shortcut). It
  stops accepting writes, finishes the current one, checkpoints and closes
  SQLite, writes a backup, and only then says "You can unplug the drive now."
- **SQLite settings for removable drives:** `journal_mode=DELETE` (not WAL: WAL
  keeps extra files and is unsafe on some removable and network filesystems),
  `synchronous=FULL`, `foreign_keys=ON`, short transactions, and a busy
  timeout. If the app detects the data folder vanished, it shows a calm message
  and stops writing.
- **Update:** replace `app/`, keep `data/`. On first start the program notes the
  new version, backs up, migrates.
- **First-run wizard** in the browser: who lives here (people, pets), a short
  **household profile** (country and region, type of home, number of storeys,
  whether anyone has mobility or care needs, vehicles, garden, hazards the
  household already knows about), which modules to switch on, backup location,
  time zone. It writes
  `data/config.toml`; the person never edits it by hand.
- **Plain-language errors** throughout, with *Save a report*.
- **Windows "unknown publisher" warning.** Without paid code signing, Windows
  SmartScreen will warn when the folder is first run. The README explains, with
  screenshots, to choose *More info → Run anyway*. Signing is a possible later
  improvement.
- **Release build.** A GitHub Actions workflow builds the portable zip on each
  release tag, runs the test suite on the built folder, computes a checksum, and
  attaches both to the release.

### Choosing the bundling method

See decision record 0003. Both options keep the same folder layout so the choice can be
changed later.

## 14. Testing and CI

- **Unit tests** for each core service and for the module loader (valid and
  invalid module files, with plain-language error messages checked).
- **Migration tests:** build a database from empty by running every track;
  upgrade a saved older-version fixture database; ensure a failed migration
  rolls back.
- **Agent API tests:** idempotency, limits, allow-lists, lock-out after edit,
  undo of batches.
- **Analysis tests** against hand-computed values and with data below the
  minimum, to prove the guardrails refuse to speak.
- **Source tests** use **fixtures**: saved real responses with personal data
  removed. A parser change must keep the fixtures passing.
- **Synthetic data only.** A seed script generates a fake household for tests
  and screenshots.
- **Privacy check (CI, required).** Fails the build if a `.db`/`.sqlite` file,
  a `config.toml`, a token-looking string (for example long hex/base64
  strings and known key prefixes), or a personal path (a Windows user-profile folder,
  a Linux or Mac home folder) is committed. It scans the diff and the whole
  tree.
- **Weekly health check (scheduled GitHub Action).** Runs each source's live
  test against its real host and opens (or updates) an issue when one stops
  parsing, naming the module and showing the failing field. This is how
  outside changes get noticed without anyone watching. It also checks that every
  country-pack link still works and flags packs past their `review_by` date.
- **Portable build test.** The built zip is unpacked in a clean runner
  and started; the acceptance list in `CORE.md` is checked where it can be
  automated.

## 15. Decisions and their records

Corey does not choose languages or structures; he judges whether the finished
application gives the household the experience he wants. So technical
decisions are made by the assistant and **every one is written down** in
`docs/decisions/` with the same shape: what we chose and why, what else we
considered, the honest downsides, how hard it is to undo, and the observable
sign that it was the wrong call. Any decision can then be judged good or bad
later and reversed, with the reversal recorded as a new decision that
supersedes the old one.

Rule for the build: **no real technical decision is merged without a record**,
and the pull request checklist asks for one. A record is not a defence of the
choice; its "costs" and "revisit if" sections must be honest.

| Topic | Choice | Record |
|---|---|---|
| Web side | Python, server-built pages, light browser scripting | 0002 |
| Bundling | Official embeddable Python in a plain folder | 0003 |
| Charts | Apache ECharts, bundled locally | 0004 |
| Statistics | Standard library only for v1 | 0005 |
| Backups | A second copy on the computer itself | 0006 |
| Modules from others | Two trust levels, honest warning, no fake sandbox | 0007 |
| Local network | Exact addresses only, typed by the person | 0008 |
| Database on USB | SQLite delete-journal, full sync, no WAL | 0009 |
| Table shape | One real table per declared table | 0010 |
| Access | This computer only | 0011 |
| Migrations | One track per module | 0012 |
| Agent-friendly files | INDEX.md in every folder, CI-checked | 0013 |
| Licence | MIT | 0014 |

The process itself is decision 0001. The questions Corey stays involved in are
about the product: screens, wording, what the household sees and does.

## 16. Build order

Work follows the milestones in [`ROADMAP.md`](ROADMAP.md). Each step is a small
branch with tests first and a pull request that includes screenshots, so the
experience can be reviewed without reading code.

**Done:** repository skeleton (layout, `config.example.toml`, `.gitignore`,
privacy check, the `INDEX.md` convention and checker, `AGENTS.md`, CI).

**M1**
1. Portable spike: the embeddable-Python folder, *Open Dashboard* and *Close
   Dashboard safely* on Windows, built by CI, opening a placeholder page. First,
   because it is the riskiest promise.
2. Core: database layer with the USB-safe settings, migrations (core and module
   tracks), module loader and the validator for `module.toml`, `tables.toml`
   and `labels.toml`.
3. Core: record services (create, edit, soft-delete, links, audit history).
4. Core: web layer, local-only protections, forms and the paged grid built
   from declarations, plain errors with *Save a report*.
5. Core: watch views (running low, expiring soon, days of cover), automatic
   daily backup and backup on safe close.
6. Core: first-run wizard and a minimal settings page.
7. Module: People (files only) with *Who do I call?*, the emergency sheet and
   the gaps check.
8. Module: Household stock (files only) with stock in and out, places and days
   of water. Fix the core here if files alone are not enough.
9. M1 release: README with the unknown-publisher guidance, final checks
   against the M1 list in `ROADMAP.md`.

**M2:** restore and export screens, review queue, inbox, Agent API and token
command, receipt entry, the chosen import route.
**M3:** prompt engine (10.5), Medical, Readiness, first country pack, optional
passphrase for the data folder.
**M4:** Graphing, Analysis with the question loop (10.2, 10.3), outcomes (10.4),
time features (events, recurrence, annotations).
**M5:** Pets, Garden (and the "build your first module" guide), Wine, API
connector with the weekly health check.

## 17. Agent-friendly layout (progressive disclosure)

Goal: an AI agent (or a new human) can understand the whole project by reading
a few short pages, and only opens deeper files when an index tells it to.
Nobody should have to read thousands of lines to learn where things are.

### The convention

1. **Every folder has an `INDEX.md`.** It is a compressed summary of that
   folder: what it is for, then one line per entry (file or subfolder) saying
   what it holds and *when you would need to open it*. Target: **25 lines or
   fewer**, plain language, no code.
2. **Indexes nest.** The root index lists the top-level folders; each of those
   indexes lists its children; and so on. An agent reads the root, picks the
   branch it needs, reads that index, and stops as soon as it has enough.
3. **Each module has an `INDEX.md` too**, so the question "what does module
   alpha cover?" is answered in one short read. The root `modules/INDEX.md`
   lists every module in one line each.
4. **Every code file starts with a one-line summary** (a module docstring
   whose first line says what the file is for). Indexes quote these lines, and
   the checker confirms they match.
5. **`AGENTS.md` at the repository root** (about 20 lines) tells any agent how
   to work here: read `INDEX.md` first, follow the indexes downward, the hard
   rules from section 2 (no personal data), that every technical decision needs
   a record in `docs/decisions/`, how to run the tests, and where
   `PROJECT_MAP.md` and `docs/` are. A one-line `CLAUDE.md` points to it so
   tools that look for either name find it.
6. **`PROJECT_MAP.md`** remains the single page listing every part of the
   project. It is generated from the indexes, so it cannot disagree with them.

### Shape of an index

```markdown
# modules/  (summary: optional features; each folder is one module)
Open a module's own INDEX.md before its files.

| Entry | What it is | Open it when |
|---|---|---|
| pets/ | Pets, weight, food, medication, vet visits (files only) | changing pet tables or forms |
| medical/ | First aid kit checks, training, medical readiness (files only) | changing kit, training or medical prompts |
| readiness/ | Prompts, plans, drills, coverage, country packs (files only) | adding a prompt or a country pack |
| people/ | Contacts, roles, important details, emergency sheet (files only) | changing who-to-call, emergency sheet or sensitive fields |
| garden/ | Vegetable garden; the worked example module (files only) | learning to build a module |
| stock/ | Pantry, emergency water, tools and hardware, receipts (files only) | changing stock, reorder or supply-cover behaviour |
| wine/ | Wine collection (files only; compact module) | changing wine tables |
| graphing/ | Charts over any table | changing chart behaviour |
| analysis/ | Statistics and the question loop | changing how findings are made |
| api_connector/ | Pulls data from outside APIs | adding or fixing a source |
```

### Keeping it true (enforced, not hoped for)

A small script, `tools/check_indexes.py`, runs in CI and as a local command:

- fails if a folder has no `INDEX.md`;
- fails if an index is over the line limit;
- fails if an index omits a file or subfolder that exists, or lists one that
  does not (stale entries);
- fails if a code file's first-line summary is missing, or differs from the
  line quoted in the index;
- can regenerate the skeleton (the list of entries) so a contributor only
  writes the one-line descriptions.

Descriptions are written by a person or an assistant; the script guarantees
completeness and freshness, not wording. Generated or vendored folders (bundled
Python, libraries, build output) are listed in the checker's ignore list and
get a single index line each.

### Why `INDEX.md` and not `README.md`

`README.md` is for people arriving on GitHub and can be long and friendly.
`INDEX.md` is deliberately short and structured for skimming, so the two do not
fight over what they are for. The root `README.md` links to the root index.

### Also helps people

A non-technical reader, or a module author, gets the same benefit: open one
short page, learn what is below, and go deeper only if needed. This is also how
the project stays small enough for a new maintainer to adopt.
