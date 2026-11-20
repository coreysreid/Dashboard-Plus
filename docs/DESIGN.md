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
  Save and exit Dashboard.bat   stops it cleanly
  app/                          program code (replaced on update)
    core/  web/  modules/  python/  (bundled interpreter + libraries)
  data/                         YOUR data (kept on update, never committed)
    dashboard.db
    config.toml                 real settings, written by the wizard
    secrets/                    API keys and agent token hashes
    backups/  exports/  attachments/  reports/
    restore.json                the last restore, so it can be undone (no secrets)
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
- **Dates the household's way** (decision 0052). People type and read dates in
  their country's order: 20/05/27 in Australia, the UK, New Zealand and most
  places; 05/20/27 in the United States; 2027-05-20 in Canada. 2027-05-20 is
  understood everywhere. Two-digit years mean 2000 to 2099. Impossible dates
  (31/04/27) are refused, never rolled over. One parser and formatter
  (`core/dates.py`) serves forms, lists, *Needs attention* and sheets; the
  form previews the date in words ("1 February 2027") while typing. Changing
  the country changes how dates look, never what is stored. The record
  service and the Agent API take only 2027-05-20.
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

- `expiring` may add `wording = "due"` for things to do by a date rather than
  use-by dates ("due in 3 days", "overdue since …"), and `what` to name it
  ("vaccinations due …").
- `expiring` may add `where`, equality filters on columns of the same table,
  so finished rows are never reminded about: `where = { status = "out" }`
  skips a loan already returned, `where = { done = false }` a job already
  done. Every filter must match. A blank yes/no counts as "no", as the form
  shows it; a blank choice matches nothing. Filters are checked like the
  `where` of gaps and sheets: an unknown column, a choice that does not exist,
  or a yes/no written as anything but `true` or `false` is a plain error
  (decision 0072). There is no "only while blank" filter yet; a module that
  needs one uses a choice or yes/no column instead.
- `running_low` and `expiring` name columns of the same table; `quantity` and
  `minimum` must be number columns, `date` a date column. Checked when the
  module loads, with plain-language errors like everything else.
- `supply` adds up `quantity` for matching rows and divides by the household's
  daily need. **Household size** comes from the People module (rows of
  `people__people` with `lives_here` set) when it is installed, otherwise from
  the `household.people` setting the wizard writes. Pets count from the Pets
  module's records when it is switched on, otherwise from the `household.pets`
  setting. The page shows the working ("2 × 10 litres
  for 3 people at 3 litres a day = about 2 days") and says the daily figures
  are a starting point, local advice comes first. The home page shows the
  daily amounts it assumes next to the result ("Based on 3 litres per person a
  day, 1 per pet"), so the basis is never hidden (decision 0046).
- `supply` may add `counts_only` (a yes/no that must be yes to count, such as
  "safe to drink") and `unit_from` with `unit_words` (rows recorded in another
  unit, like "6 bottles", are left out and named until their total is
  entered in the supply's unit).
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
of the record the link points at. The link may point into this module, or into
a module listed under `requires` (Vehicles prints `roadside_contact.phone`
from People). A link into another module is checked once every module has
loaded: the column must exist there, and it must not be private, because a
sheet is printed and left out, and another module's private detail should not
reach it through a link (decision 0072). Sensitive columns of the module's own
tables are printed only if a section lists them explicitly, and the page says
they are included. A section's `where` filters still use this module's tables
only.

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
  linking to a new-record form with the filters filled in; `none = {}` asks
  when the table has no records at all) or `missing` (a
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

### 5.5 Picking from a list while typing

A text column can offer matches while someone types, from a CSV list in the
module folder. Household stock uses it for the name of an item:

```toml
# labels.toml
[tables.items]
columns.name = { suggest_from = "catalogue.csv", fills = { category = "category", unit = "unit", drinking = "counts_as_drinking_water" } }
```

- The CSV needs a `name` column; `also_called` (other names separated by `|`)
  is searched too, and `fills` copies cells into other fields when a match is
  picked (a choice must be one of the column's choices; yes/no is `yes` or
  `no`; blank cells fill nothing).
- Matches come in this order: the household's own records (shown as "you
  already have this: open it", so nothing is added twice), then names that
  start with what was typed, names with a word that does, then other names.
  Case, accents and punctuation are ignored.
- Whatever was typed can always be kept as it is.
- Any linked-record drop-down with more than eight choices also gets a box to
  type into, and offers to add a new record when nothing matches.
- A yes/no column can be required only for some records
  (`required_when = { category = "water" }` in tables.toml). It is then asked
  as two choices with neither picked (`answers` in labels.toml give the
  words), so nobody agrees by not noticing a ticked box.
- A field can be shown only when a choice has a particular value
  (`show_when = { category = "water" }` in labels.toml).

### 5.6 Records inside records (nested places)

A table can nest its records by naming a link to itself as `parent`:

```toml
[tables.places]
parent = "inside"
columns.inside = { type = "link", to = "places", on_delete = "restrict" }
```

- Everywhere a nested record is shown (lists, drop-downs, record pages,
  printed sheets) it reads as its full path: **Kitchen › Pantry › Shelf 3**.
  Drop-downs are sorted by path, so a room is followed by what is inside it,
  and the find box matches any part of the path.
- Moving a record moves everything inside it; paths update at once because
  only the link is stored.
- Saving refuses a record inside itself or inside something it contains, and
  paths deeper than eight levels.
- With `on_delete = "restrict"`, a room cannot be deleted while places are
  still inside it.

### 5.7 Batches: layered use-by dates

An item's stock can be split into batches, each with its own amount, use-by
date and place: 3 tins of kidney beans on Shelf 3 use by next month, 10 in the
garage in six months (decision 0053). Declared in files:

```toml
[tables.lots]
record_name = "{item}, {quantity}[ {item.unit}][ at {place}][, use by {expires}]"

[tables.lots.total]            # batches add up into their item
link = "item"
amount = "quantity"
into = "quantity"              # the item's amount is the sum of its batches
earliest = { date = "expires", into = "expires" }   # its Use by: the earliest batch still holding some
starts_from = ["quantity", "place", "expires"]      # an item typed in with these starts its first batch

[tables.lots.watch]
expiring = { date = "expires", warn_days = 30, only_positive = "quantity" }

[tables.movements.adjusts]     # stock in and out changes one batch
link = "lot"
belongs_to = "item"
new_batch = { expires = "expires", place = "place" }
oldest_first = "expires"
counts = { more = "counted_more", less = "counted_less", note = "notes" }  # stocktake (decision 0070)
# plus quantity, amount, direction and adds as in 5.3
```

- The item's amount and Use by are worked out, never typed over: changing them
  directly is refused with "is worked out from its batches". A stocktake
  correction changes the batch, and the item follows, both in history.
- **Count this batch** (decision 0070), on a batch whose table is the target of
  an `adjusts` rule with `counts`: the person types what they counted; a review
  says "You counted 5 tins; 3 tins are recorded here. This adds 2 tins as a
  stocktake correction"; Save records one movement of the difference with the
  `more` or `less` reason, the batch, the item and a note of both amounts. The
  count is never added on top. Saving compares the amount the review showed with
  the batch now and refuses an out-of-date review; a batch that already holds
  the count saves nothing (so a second click adds nothing). A `counts` reason
  with no batch chosen is refused. Undo, edit and restore move only the
  difference, as for any movement. The item total has no count form.
- Stock in with no batch chosen starts a new batch with the use-by date and
  place given. Adding to an existing batch is an explicit choice of that batch.
- Using some with no batch chosen takes from the batch with the earliest known
  use-by date; an undated batch comes after dated ones. If that batch holds
  too little, the person is asked to record it batch by batch (no silent
  split); more than the item holds is refused with "only 13 left".
- A chosen batch must belong to the movement's item.
- On the form, the batch list follows the item (decision 0057): a link whose
  table has a `total` rule is tied to the other link on the form that points
  at the same table, each choice carries `data-owner`, and a few lines of
  script show only the chosen item's batches. The blank choice is worded from
  the `adjusts` rule ("Start a new batch" for reasons in `adds`, otherwise
  "Use the batch with the earliest use-by date"); labels.toml can reword it
  with `blank = { adds = "…", takes = "…" }`. The `new_batch` boxes are
  hidden once a batch is chosen. Saving checks again, scripts or not.
- Each batch that still holds something gets its own use-by warning, named by
  `record_name` ("Kidney beans, 3 tins at Kitchen › Pantry › Shelf 3"); a part
  in [square brackets] is left out when it is blank. A used-up batch stays as
  history but never warns and is not printed.
- Delete and restore keep amounts right: a deleted batch leaves the item's
  total, and comes back into it when restored.
- Upgrading: each item recorded before batches becomes one batch with its
  amount, use-by date and place; earlier stock in and out is linked to it, not
  replayed. A backup is made first (startup, decision 0050).

### 5.8 One-step actions and date order

A table can offer a one-press button on a record's page that sets a few fields
(decision 0075):

```toml
[[tables.loans.actions]]
key = "returned"                                     # in the address: /t/lent_out__loans/3/do/returned
label = "Mark returned"                              # the button
show_when = { status = "out" }                       # shown only while every filter matches
set = { status = "returned", returned_on = "today" } # fixed values; "today" / "now" for dates and times
done = "Marked as returned today."                   # the notice afterwards

columns.returned_on = { type = "date", not_before = "lent_on" }
```

- All five action settings are needed. Checked when the module loads: `set`
  and `show_when` name columns of this table; choices are real choices; values
  fit the column; links, files, private columns and columns worked out from
  other records (batch totals, amounts changed by stock in and out) can't be
  set; private columns can't decide when a button shows; `set` must change a
  `show_when` column, so the button goes away once pressed; and it must fill in
  any field its values make `required_when`.
- labels.toml can reword a declared action:
  `actions.returned = { label = "Back now", done = "Marked as back." }`.
- The button is a small POST form with the page's token, on the record's page
  only (not the list). Saving goes through the ordinary change: every check,
  history, batches and totals, in one transaction. If the record no longer
  matches `show_when` (a double click or an old page), nothing changes and the
  page says so.
- `not_before` (on a date column, naming another date column of the same
  table) refuses an earlier date when adding, editing or pressing an action:
  "Returned on can't be before Lent on.", from the labels. The same day is
  fine; a blank date is not compared.

**Actions that add a record** (decision 0091). An action with `adds` opens a
small form instead of saving at once, and one save adds a linked record and
changes this one:

```toml
[[tables.jobs.actions]]
key = "done"
label = "Mark done"
title = "Mark “{record}” done"                      # optional; {record} is the record's name
intro = "Nothing changes until you save."           # optional
done = "Marked done on {done_on}. Work done was saved."  # may name asked fields
undo = "Undo this completion"                       # optional: offers Undo after saving
adds = { table = "work_done", link = "job", ask = ["done_on", "done_by", "notes"],
         values = { }, add_button = "Add an older Work done entry (does not change the job dates)" }
latest = { date = "done_on", into = "last_done" }   # optional: the asked date becomes this record's
next_date = { into = "next_due", question = "When do you want to do it again?",
              repeat = { count = "repeat_count", unit = "repeat_unit" } }  # optional; repeat optional
help = { done_on = "The day the work was finished." }  # optional words under asked fields
messages = { stale = "...", same_day = "... {date} ...", undo_refused = "..." }  # optional
```

- `show_when` and `set` are optional here. `ask` names fields of the added
  table (public, typed in, not the link); `values` fixes others with the same
  rules as `set`; every required field of the added table must be asked,
  fixed or have a default. `latest.date` must be an asked date; `latest.into`
  and `next_date.into` public date columns of this table; `repeat.count` a
  whole-number column and `repeat.unit` a choice of weeks, months or years.
  All checked when the module loads, with plain messages.
- The `latest` date may not be after today, nor before the record's current
  value (older work goes through the ordinary add form, which changes no
  dates), nor a day that already has a linked record. `next_date` asks for
  one explicit choice, none preselected: a date (not before the `latest`
  date; a date already passed is explained and needs a second Save), the
  date the record's repeat offers from the `latest` date (calendar months
  and years, clamped to the month's last day; weeks of seven days), or no
  date, which clears the reminder.
- One save is one transaction: the linked record through the ordinary create
  path, this record through the ordinary change path, and one `action` entry
  in history holding the fields before and after and the new record's id.
- The form carries the record's **revision** (its newest history entry) and
  a one-use **operation number**. A different revision saves nothing and says
  `messages.stale`; the same operation number sent again returns the first
  result and saves nothing new.
- **Undo** is offered on the notice after saving while nothing about either
  record has changed since (both revisions are what the operation left). It
  deletes the added record (kept in history) and puts the fields back, in one
  transaction, with an `undo` history entry; otherwise it says
  `messages.undo_refused` and changes nothing.
- labels.toml may reword `label`, `done`, `title`, `intro` and `undo`.

## 6. Modules

A module is a folder:

```text
modules/<name>/
  module.toml       name, version, description, core_api needed,
                    requires, outbound hosts
  tables.toml       tables, columns, types, dropdown values, links,
                    one-step actions (5.8)
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
columns appear on the quick-entry form. A table may also give `empty`, a short
first step such as `empty = "Add a few things from the pantry."`: while that
table has no records, the home page shows it under *Start here* with a button to
add one (the first such table wins, so the home page never shows a list of
chores).

The home page has one card per module (decision 0056). A table may say where
it sits in that card: `home = "main"` shows it large with its count and an Add
button; `home = "more"` puts it in the card's one line of links. With no
`home` anywhere, the module's first table is the main one and the rest are
links. Any other word is reported when the module loads. Cards come in the
order People, Household stock, Home layout, Medical readiness, Pets, then
other modules from A to Z; a module's printable sheets are linked from its
card.

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

- **Pets** (declarative; shipped in M1, decision 0047). Tables: pets (kind,
  breed, birthday, microchip, vet and carer linked to People, vaccinations
  due), treatments and medicine (with how often and next due), treatments
  given, weigh-ins and vet visits (with cost). Gaps ask for a missing vet or vet
  phone number; due dates appear under *Needs attention*; a pet details sheet
  prints for a sitter, kennel or evacuation. Setup asks each pet's name and
  kind. Later: meals and daily food totals, litter or walk logs, entering data
  off paper (below).
- **People** (declarative; on by default; a pillar of resilience). Tables:
  - *people*: name, preferred name, lives here (yes/no), relationship, birthday,
    phone, email, address, notes.
  - *roles*: a person and a role (emergency contact, family, neighbour, doctor,
    dentist, vet, tradesperson, roadside assistance, school, workplace, key
    holder, other) with a
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
- **Home layout** (declarative; requires Household stock; shipped, decision
  0054). Tables: ways out (floor, place, how to get there), shut-offs and power
  board, alarms and safety equipment (last tested, battery changed, test or
  check again by), and meters. Every "where it is" links to `stock.places`, so
  the household's places are shared and none were moved. Behaviour: gaps ask
  for a way out, the water shut-off, the power board and a smoke alarm (not
  gas, which many homes lack); a check is *due* on the date the household
  chose, never one worked out for it; an **Our home** sheet prints everything
  with full place paths and no notes. Each of the four lists also has an
  optional private `access_details` box for alarm codes and key-safe numbers
  (`sensitive`, shown only on Show, never in the sheet; decision 0077).
- **Vehicles** (declarative; requires People and Household stock; shipped,
  decision 0058). Tables: vehicles (registration or plate number, marked
  `sensitive`; registration or vehicle tax due; who to call if it breaks
  down, a link to `people.people`; where it is usually kept, a link to
  `stock.places`; its car emergency kit, a link to `stock.items`), insurance
  renewals and services and checks. Behaviour: each date is *due* on the day
  the household chose, never one worked out from the last; one gap asks, per
  vehicle, "Who would you call if it broke down?"; a household with no
  vehicle is asked nothing; a **Vehicles** sheet prints the vehicles and
  dates without plate or policy numbers.
- **Important documents** (declarative; requires People and Household stock;
  shipped, decision 0062). A list of where papers are kept, not a document
  vault. One table: documents (name, kind such as passport, insurance, will
  or warranty; whose it is, a link to `people.people`; where it is kept, a
  link to `stock.places`; a review or renew-by date; notes). There is no
  field for a document number, password or copy of the paper. Behaviour: the
  date is *due* on the day the household chose; one gap asks, per paper,
  "Where is it kept?"; a household with no papers listed is asked nothing; a
  **Document review dates** sheet prints names, kinds and dates only, never
  where papers are kept.
- **Home care** (declarative; requires People and Household stock; shipped,
  decision 0063). Tables: home care jobs (what kind, which of the household's
  `stock.places` it is at, who usually does it, a link to `people.people`;
  last done; do again by; an optional repeat the household chose) and work
  done (a dated note of each time, and who did it). Behaviour: a job is *due*
  on the date the household chose, never one worked out for it; **Mark done**
  (decision 0091, section 5.8) adds Work done and sets Last done and the
  chosen Do again by in one save, offering one date from the job's repeat
  only if the household set one, and can be undone; adding an older Work done
  entry changes no dates; one gap asks where a job is done; smoke alarms and
  extinguishers stay in Home layout; a **Home care** sheet prints the jobs and
  dates without notes. No field holds alarm codes or how to get in.
- **Vegetable garden** (declarative; requires Household stock; shipped,
  decision 0076). Tables: beds (a link to `stock.places`), crops, plantings
  (a name, bed, crop, planted on, quantity), harvests (a planting, a date, an
  amount) and jobs (a due date and "Done?"). Behaviour: a job is "due" from two
  weeks before its date, only while not done (`where` on `expiring`, decision
  0072); one gap asks where a bed is; a **Garden plan** sheet prints beds,
  plantings and jobs not done, without notes. No growing advice is stored.
- **Things lent out** (declarative; requires People and Household stock;
  shipped, decision 0073). Table: loans (what was lent; an optional
  `stock.items` link that changes no count; the borrower, a link to
  `people.people`; lent on; due back; "is it back?"; returned on, required
  once it is back; notes). Behaviour: "return due" or "overdue" from a week
  before the agreed date, only while the loan is out (`where` on `expiring`,
  decision 0072); a returned loan stays as history; one gap asks how to reach
  a borrower with no phone, once per borrower, only while something is out; a
  **Things still lent out** sheet prints open loans with the borrower's phone
  from People, without notes. Nothing is ever sent to the borrower.
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

Helpers' suggestions are **not** stored as `needs_review` rows in module tables
(decision 0068): creating a row applies its side effects at once, and lists and
totals do not filter on review status. They wait in the core tables
`core__helper_batches` and `core__proposals`. The **Review** screen (`/review`)
shows waiting batches newest first, each with the helper, the reason and every
suggestion in plain words. The person can accept or reject each one, or a whole
batch. Accepting creates the record by the normal path in one transaction,
credited to `agent:<helper>`, marked `edited_by_person`; if it can no longer be
added it stays waiting with the reason. Rejected rows stay in history. The
`review_status` column is not used by helpers.

### Importing from a spreadsheet

Rows from a CSV file wait on the same Review screen (decision 0080). Settings,
*Import from a spreadsheet* (`/settings/import`): choose a list, upload a CSV
(UTF-8, comma or semicolon, up to 1 MB and 2,000 rows), match each column to a
field (guessed from the headings by label or key; any can be changed or
skipped), and see a dry run: "38 rows ready, 2 need fixing" with the plain
problem for each row by its spreadsheet row number. The dry run converts each
cell (dates the household's way or ISO; links by name, places by full path)
and then runs the same `check_create` as a helper's suggestion. *Send to
Review* stages the ready rows as one batch with `kind = 'import'`, no helper
and `source_name` set to the file's name; each row keeps its `source_row`.
Accepting creates the record credited to `import:<file name>`. Helpers never
see import batches. The file is read in memory and never written to disk;
private (sensitive) columns cannot be imported.

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
touch the database. The API is part of the same local server (`127.0.0.1`
only) under `/api/v1/`. The port changes at each start, so Settings, Helpers
shows the current address (decisions 0066 to 0068, hardened by 0074, with a
published description in 0084, a Review queue limit in 0085, and a check that
the address is really Dashboard in 0086).

### Authentication

`Authorization: Bearer <key>`. A key is `dph_` plus 32 random bytes, made on
Settings, Helpers with a name, a level (look only, or look and suggest new
records) and the modules it may use (none ticked by default). It is shown once
and kept only as a SHA-256 fingerprint in `data/secrets/helper_keys.json`
(mode 0600), never in the database. A request carrying an `Origin` header is
refused (helpers are programs, not web pages). Cookies, query strings and form
fields are never read for a key.

**Checking it is really Dashboard (0086).** `POST /api/v1/hello` is the one
route without a key. A program sends `key_name` (`SHA-256("dph-id:" +
fingerprint)`, which cannot be worked back) and a fresh 32-byte `nonce`;
Dashboard answers `proof` = `HMAC-SHA256(SHA-256("dph-hello:" + fingerprint),
"dashboard-plus-hello-v1|" + nonce + "|" + host:port)`. An unknown or
turned-off name gets the same shape, signed with a secret made at each start.
Origin and Host rules apply; 1 KB body; its own limit of 600 a minute shared by
everyone (`HELLOS_PER_MINUTE`), separate from each helper's.

### Routes

| Route | Purpose |
|---|---|
| `GET /api/v1/me` | The helper's name, level, modules and limits |
| `GET /api/v1/tables` | Live column spec for allowed tables; private columns left out |
| `GET /api/v1/tables/<t>/records` | Records, paged by id (`after`, `limit` up to 200) |
| `GET /api/v1/tables/<t>/records/<id>` | One record |
| `GET /api/v1/attention` | Running low, expiring, supplies and gaps for allowed modules |
| `POST /api/v1/proposals` | Suggest new records (below) |
| `GET /api/v1/batches`, `/batches/<id>` | The helper's own batches and their state |
| `GET /api/v1/openapi.json` | The published description of this API (OpenAPI 3.1), read-only, same key (0084) |
| `POST /api/v1/hello` | No key: proves this is the Dashboard that made a key, before the key is sent (0086) |

`POST /api/v1/proposals` body: `request_key`, `why`, `entries` (each
`{"table", "values"}`).

### Rules

- Suggestions are **new records only**. `request_key` is required; the same key
  and body returns the original batch, a different body is refused (409).
- At most **50 entries per call** and **200 suggested rows per helper per day**;
  body at most 64 KB; JSON only.
- Every suggestion is tried by a full dry run before it is stored; any problem
  refuses the whole call and names entry, table and field.
- Columns marked `sensitive` are never returned and never accepted. There is no
  grant for them in v1.
- A link into a part the helper was not given is invisible: left out of
  `/tables`, of records and of `/attention`, and refused (403 `not_allowed`, the
  same reply whatever value is sent) in a suggestion. A table that requires such
  a link cannot be suggested into. A table in a part not given answers exactly
  like a table that does not exist (404 `not_found`); `/me` says what it may use.
- Text in a suggestion that looks like a helper key (`dph_...`) is refused
  without being repeated; so are invisible control characters and marks that
  turn text around (400). Review shows the reason and values as the named
  helper's own words.
- At most **500 of a helper's suggestions waiting on Review** at once (setting
  `HELPER_REVIEW_QUEUE_LIMIT`). A request that would go over is refused whole
  (429 `review_queue_full`, no `Retry-After`: only a person's decision frees
  room); accepting or rejecting frees room, imported spreadsheet rows never
  count, and `/me` shows `review_queue_limit` and `suggestions_waiting` (0085).
  Both this cap and the daily limit are checked again inside the write lock, so
  requests sent at the same moment cannot pass them (0088). Any `/api/` address
  other than `/api/v1/` answers 404 JSON `not_found`, never a page (0088).
- At most **120 requests per helper per minute** (429 `too_many_requests` with
  `Retry-After`). Accept and Reject decide a suggestion once, even if two clicks
  arrive together.
- Money is read and sent in whole units (stored in cents). Columns worked out
  from batches (a stock item's amount) cannot be suggested; suggest a Stock in.
- A helper can never accept, change or delete records, see history, see other
  helpers, or reach settings, backups, files or keys: there are no such routes.
- The API is described by one file, `src/dashboard/web/openapi-v1.json`, served
  at `/api/v1/openapi.json` behind the same key as every route. A contract test
  (`tests/test_api_contract.py`) fails when a route, method, error code or reply
  shape in the code is missing from it, or the reverse (0084).
- Deferred: suggested changes and deletions, amend and undo, a private-details
  grant, per-table scope, a command-line tool, forgetting request keys.

### Connecting an AI assistant (MCP)

`python -m dashboard.connector` is a small local program an assistant's app
starts (decision 0083). It speaks MCP over stdio (JSON-RPC 2.0, one message
per line, protocol `2025-06-18`), opens no port, and uses no library beyond
Python's own. Its eight tools map one to one to the routes above:
`dashboard_me`, `dashboard_tables`, `dashboard_list_records`,
`dashboard_get_record`, `dashboard_attention`,
`dashboard_suggest_new_records`, `dashboard_list_suggestion_batches`,
`dashboard_get_suggestion_batch`. It can do nothing the key does not allow.

- The address and key come only from `DASHBOARD_PLUS_URL` and
  `DASHBOARD_PLUS_KEY` or a `--config` file, never from a tool's arguments.
  Only `http://127.0.0.1:<port>` or `http://localhost:<port>` is accepted.
- Before every request it sends the hello above on a new connection; only if
  the proof matches (`hmac.compare_digest`) does the request, with the key, go
  down that same connection. Otherwise the tool fails with "This address is
  not Dashboard Plus, or it is an old address..." and the key is never sent;
  the other program's words are never passed on (0086).
- Requests have a timeout, ignore proxy settings and never follow a redirect.
  The key, and anything shaped like a key, is removed from everything it
  writes; stderr has one-line notes, never a stack trace.
- Every result says it is household data, not instructions, then gives the
  API's JSON (as text, and as `structuredContent`). API refusals become tool
  errors with the API's own message; nothing is retried with wider access.
- Settings, Helpers and the new-key page show "Connect an AI assistant":
  settings to paste into the assistant's app with `YOUR-KEY-HERE` in place of
  the key, and the warning that an online assistant sees what the helper reads.

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
  after, batch_id)`. The actor is `person`, `agent:<name>`, `import:<file>`,
  `module:<name>` or `system`. Every write goes through core services, so every write is audited.
  A history panel on each record shows what changed.
- **Undo.** Undo reverses a person's last change, or an agent's batch,
  using the audit before/after. Undo is itself audited.
- **Backups.** A consistent copy using SQLite's online backup, daily and before
  any migration, plus a copy on the computer's own disk. Kept for a configured
  number of days; the latest of each kind is never deleted automatically.
  Backups are verified by opening them and running `PRAGMA integrity_check`.
  Each backup records how it went in `backups/status.json` in the data folder;
  Settings shows when each copy was last made, and if the copy on the computer
  failed, Settings and the home page say so plainly, with the reason and the
  date of the last good copy (decision 0046).
- **Restore** (decision 0079). Settings → Backups lists the copies in the data
  folder and in the second folder on the computer, newest first. Each is
  opened read-only and checked (`quick_check` in the list, the full
  `integrity_check` before a restore); nothing is ever written to a backup.
  A copy from a newer version, with a part (module) this program lacks, or
  with a changed database step is refused; an older copy is brought up to
  date on a copy. The preview shows the date, size, "Check passed" and the
  number of records in each list then and now. Restoring prepares the copy as
  a new file in the data folder, waits until no page has the data file open,
  makes a checked `before-restore-` backup, and swaps the prepared file in
  with one atomic rename. `restore.json` names that backup, so **Undo
  restore** works after a restart until the household keeps the restored
  records or restores again. Undo is itself a restore (with a `before-undo-`
  backup). Any failure leaves the records in use and says "Nothing was
  changed." Helper keys (`data/secrets/`) are never part of a backup or a
  restore. Later: restoring into a new folder and switching folders,
  removable drives, attachments, and a catalogue of copies across computers.
- **Export everything.** One click writes a folder: one CSV per table (with
  dropdown labels and keys, link columns resolved to readable names), the
  attachments, the notes and annotations as plain text/Markdown, and a
  `README.txt` explaining each file. Nothing in it requires this program.

- **Export my records** (decision 0078, built). Settings has a page with one
  button that downloads `dashboard-plus-export-YYYY-MM-DD.zip`: one CSV per
  installed table, a `manifest.json` (app and module versions, tables, row
  counts, every column's heading and internal name, and which columns were
  left out as private, by label only) and a `README.txt` in plain words.
  Headings are the household's labels; links show the record's name (the full
  path for nested places) and its id in a separate column; dates are ISO,
  money is in whole units, yes/no is Yes/No and choices are their labels.
  Deleted records are left out unless a checkbox asks for them, and then get a
  "Deleted on" column. **Private (`sensitive`) columns and `data/secrets/` are
  never exported**; the export is not the place for them, and it is a copy for
  spreadsheets, not a backup. Text cells that begin with `=`, `+`, `-`, `@`,
  a tab or a line return get a leading apostrophe so a spreadsheet cannot run
  them. It is read inside one read transaction, so every file is from the same
  moment. Not built yet: writing a folder with attachments, notes and the
  change history, and a way to export private details deliberately.
## 12. Security and privacy

- **Local only.** The web server binds to `127.0.0.1`, never `0.0.0.0`.
- **Browser protections.** A random per-start session secret is placed in the
  launch URL and stored in a cookie. The server checks the `Host` header
  (defends against DNS-rebinding), uses `SameSite` cookies and checks the
  `Origin` header on writes (defends against other web pages talking to the
  local server).
- **The Agent API** uses bearer keys as described. It is on the same local
  port; there is no remote option. `/api/v1/` is the only exemption from the
  cookie and page token, and it refuses any request with an `Origin` header;
  every other path is exactly as strict as before (decision 0067).
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
- **Declarative modules are confined** (decision 0055). Their numbered
  database changes run under a guard that allows only creating, changing and
  filling the module's own tables, and adding entries to the change history.
  Reading or changing another module's or the core's tables, triggers, views,
  attaching files, settings (PRAGMA), committing part-way and copying the
  database elsewhere are refused; the module is left out and nothing changes.
  A module's names for records, questions (gaps) and units may not use a
  private column.
- **Files on a shared computer.** On Mac and Linux the data folder, database,
  backups and the running-state file (which holds the session key) are
  readable by the person's own account only. The second backup copy's folder
  name must be one the program made, so it cannot be pointed elsewhere.
- **Private pages.** Every page is sent with `Cache-Control: no-store` and may
  not be shown inside another site (`X-Frame-Options: DENY`).
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
- **Save and exit** is a button in the app (and a second shortcut). It
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
- **Real-browser check (decision 0064).** `tools/browser_check.py` starts the real program on a
  throwaway data folder and clicks through it in Chromium (en-AU and en-US): the setup wizard, Home,
  typing dates the household's way, stock in with batches, private details and sheets, and Save and
  exit, failing on any browser console error or refused request. It runs in its own Linux CI job;
  `tests/test_browser_check.py` runs it locally when Node.js and Playwright are installed and skips
  with the reason otherwise. The Flask test client cannot see browser behaviour such as the
  `Origin: null` that a `no-referrer` policy causes.
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
| Licence | AGPL-3.0-or-later | 0065 (was MIT, 0014) |

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
