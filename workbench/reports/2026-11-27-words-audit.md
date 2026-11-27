# Batch 23 item 126: words audit, every page

Checked 27 November 2026 on Lane A's branch at `eeb6eac`. A script followed every link from Home (no month, range
or day variants) in Smith, Garcia and Taylor: 700, 700 and 613 pages. It collected each page's headings, buttons,
links, folded summaries and short paragraphs: about 4,400 distinct strings in all, with hidden screen-reader text
left out. They were then grouped by meaning to find one idea said several ways, technical words and blaming words.
The proposals below are **one agreed word per idea**, with the exact strings to change.

## The agreed words

| Idea | Agreed word | Seen today (all should become the agreed word) |
|---|---|---|
| Reveal something private on this page | **Show** + what: "Show the medicine", "Show the amount" | "Show", "Show private detail", "Show private sheet", "Show money back", "Show estimated cost and scope", "Show the chosen medicine", "Show details" (README) |
| See more rows of a list | **More** ("Next 50 rows") | "Show more" (Bills, Places copies are kept). It reads like the private Show. |
| Go to another page to look | **See** + what | "See this day", "See these days", "See these weeks", "See feeding log", "See pet feeding log", and "Look" (backups column), "Open" (row links) |
| Open one record | **Open** + its name | "Open", "Open record to update", "List of every entry" |
| Reverse the last action | **Undo** + what, as a button: "Undo this tick", "Undo restore" | "Undo", "Undo this", "Undo this tick", "Undo restore", "Put back on the calendar", "Transfer back", "Undo: take all 93 off again" |
| Rows from a file, checked on Review | **Import from a spreadsheet** (checked on Review) | the same, plus "import rows from a spreadsheet" on Review |
| Rows from a file, added at once with one Undo | **Bring in earlier entries** | Settings calls the section "Earlier entries of a dated log" |
| Remove a record for good | **Delete** + name | "Delete", "Delete Kitchen" |
| Take a link or a day off, keeping the record | **Remove** + what | "Remove" (a connection), "Not a done day — remove from the calendar" |
| Something written down | **entry** in a list, **record** only in Settings and help | "entry", "record", "Done or skipped", "times done recorded" |
| A dated task finished | **Done** | "Mark done", "Mark this occurrence done", "Return done", "Test done", "Save done or skipped", "Save work done" |
| A task whose date has passed | **Due since <date>** | "Late" (Things to do heading), "due or late today" (Home) |

## Changes, worst first

### Important: two features called import and bring in, with near-identical words

**"Import from a spreadsheet: bring rows from a CSV file into a list"** (Settings) and **"Bring in earlier entries"**
(lists) do different things. One waits on Review; the other adds at once with one Undo. The first is described
with the second's verb, "bring". Review then says "import rows from a spreadsheet".
- Settings link: **"Import from a spreadsheet: rows wait on Review before anything is added"**.
- Settings heading "Earlier entries of a dated log" → **"Bring in earlier entries: added at once, with one Undo"**.

### Important: "Show more" means the next page, next to a private "Show"

On Bills and Places copies are kept, **"Show more"** pages the list. On the same kind of page, "Show" reveals a
private value. → **"Next 50 rows"**.

### Important: "Late" on Things to do, and "due or late" on Home

Decision 0107 chose **"Due since"** so that nothing reads as failing. Things to do still has a **"Late"** heading
over "Put the bins out · Due since 24/11/26", and Home says **"2 due or late today · 2 this week"**.
- Heading → **"From before today"**.
- Home → **"2 due today or before · 2 this week"**.

### Important: a broken heading on Readiness questions

**"Flood none fit your settings"**, **"Heat none fit your settings"** and **"Storm none fit your settings"** (Smith,
`/questions/readiness`) → **"Flood: none of these fit your settings"**.

### Minor: technical or system words

| Now | Where | Replace with |
|---|---|---|
| "Mark this occurrence done" | routines, Things to do | **"Mark done"** (the date is beside it) |
| "Open record to update" | Things to do | **"Open <name> to update it"** |
| "List of every entry" | calendar and bars pages | **"All <list name>"**, such as "All vehicle services" |
| "Add an older Work done entry (does not change the job dates)" | Home care job | **"Add an earlier time it was done"**, with the bracket as help text below |
| "Add to done or skipped" / "Add to work done" | form headings | **"Add a time it was done or skipped"** / **"Add a time the work was done"** |
| "Done?" | Garden jobs column | **"Done"** |
| "(an earlier time, from its history)" | calendars | **"(an earlier date you recorded)"** (item 112) |
| "0 times done recorded", "1 time done recorded" | folded bars | **"not done yet in these 12 months"**, **"done once"** (item 107) |
| "Given to #4", "Person #3" | private calendars and bars | **"Person 1 of 2"** (item 106) |
| "Look" (column and link) | Restore from a backup | **"See what is in it"** |
| "Download my records" under "Export my records" | Settings | keep both, but say **"Export: a copy of your records for spreadsheets"** once |
| "Money back appears here after you record a refund on a Stock in that has a price." as a heading | Stock in pages | a paragraph, not a heading |

### Minor: empty states said five ways

"Nothing here yet. Add the first one .", "None recorded yet.", "Nothing recorded yet.", "No helpers yet.", "No
connections yet.". One pattern: **"No <things> yet."** plus an action link: **"No storage spots yet. Add one."**
Fix the stray space before the full stop after a link ("Add the first one ."). **"No places copies are kept yet."**
→ **"No places for copies yet."**

### Minor: Keep and Save

"Keep in Vehicles" and "Keep reminders in Vehicles" (Bills moves) are the same choice; use **"Keep reminders in
Vehicles"** on both. "Keep my records as they are" (restore) is clear. Keep "Save", "Save changes" and "Save and add
another" as they are.

### Minor: possessives

"Water the pot plants's page", "Rosa Garcia's page" → **"Back to <name>"** (items 107 and 109).

## Words that are fine and should stay

"Accept", "Reject", "Accept ticked", "Not now", "Not relevant", "Not yet", "Mark returned", "Restore this backup",
"Save and exit", "Start this practice", "Turn off access" and "Make a new key" are each used for one thing only.

## Limits

GET pages reached by links only. Forms after a POST (Show results, confirmations) were read in items 106 to 115,
not in this crawl. Words in help text under fields were not audited.
