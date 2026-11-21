# 0103. Set up my home: rooms, storage spots and which rooms connect, on one page

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
There is now a **Set up my home** page. On one screen you add your rooms and areas, the storage
spots inside them (Kitchen › Pantry › Shelf 3), rename or move any of them, and say which rooms
lead into which: Hallway to Kitchen through a door, the Front hall to outside through the front
door. It is offered straight after the welcome questions (you can skip it), and it is always on
the Home page and in Settings, not only behind an empty picker.

## What we chose
- **One page, the existing Places.** `/set-up-home` reads and writes the same Places table
  (`stock__places`, Household stock) with its nesting from decision 0049. Nothing is copied or
  forked: a room added here is a Place everywhere else, and a storage spot is a Place inside it.
- **A new table for connections**, owned by Household stock because it owns Places:
  `stock__connections` with *From* (`place`, required), *Connects to* (`connects_to`, another
  place, or blank for straight outside), *Through* (`kind`: Door, Open doorway or archway, Stairs,
  Door to outside, Other) and notes. It is added by the module's own numbered migration
  (`modules/stock/migrations/0006_connections_between_places.sql`), which only creates this
  module's table, under the confinement rule of decision 0055. The core gives it its permanent ID
  and revision after the module's migrations, as for every module table (decision 0100).
- **Doors that lead outside are marked by their kind**, "Door to outside". A door straight out
  has no place on the other side; a door into a yard the household has listed as a place (the
  Backyard, a balcony) keeps that place and is still a door to outside. Choosing *Outside* on the
  page saves a door to outside.
- **The rules sit in the core, declared in tables.toml**, so they hold on this page, the ordinary
  add and edit forms, a spreadsheet import and a helper's suggestion alike. A new table setting,
  `pair = { columns = ["place", "connects_to"], blank_when = { kind = "outside_door" } }`
  (DESIGN.md 5.6), means: a place is never joined to itself; two places are joined once, either
  way round (Hallway to Kitchen and Kitchen to Hallway are the same); and the second may be blank
  only for a door to outside. Two doors straight out from one hall are allowed.
- **A deleted room takes its connections with it** (`on_delete = "cascade"` on both columns), and
  restoring the room brings them back, as for any record (decision 0050). Restoring a connection
  whose two places were joined again meanwhile is refused, so there is never a duplicate.
  A room with storage spots or things kept in it is still not deleted (decision 0049).
- **Nothing here is private**, so every column travels (decision 0100): room names, kinds and
  notes are ordinary details, exported in `stock__connections.csv`, kept in backups and shown to a
  helper the household gave Household stock, like Places already are. No travels rule is needed.
- **Works without scripts.** Every change is an ordinary form with a Save button; the forms for a
  room are folded into `<details>` sections a keyboard can open. Common room and spot names come
  from `places.csv` through the browser's own suggestion list. The page fits a phone: room cards
  stack in one column.
- **Data shaped for a later exit map.** A future, simple drawn map of the way out ("lego level
  accuracy", ROADMAP) can be built from rooms as boxes and connections as the lines between them,
  with doors to outside as the exits. Nothing is drawn now (BACKLOG).

## Why we chose it
- Corey: "there should be a configure my home section on either the intro to the app or on the
  main page ... The real tool is the home config first: add rooms and connections between them,
  storage locations within the rooms etc."
- Reusing Places keeps one list of where things are; a second "rooms" list would drift.
- Declaring the rule as `pair` keeps it one rule for every way in, instead of page-only checks a
  helper or an import could get round.

## What else we considered
- **A separate Rooms table in Home layout.** Lost: rooms are already Places, and every module
  links to Places.
- **A tick box "Leads outside" beside the kind.** Lost: two ways to say one thing, which can
  disagree; the kind "Door to outside" says it once.
- **"Outside" as a special Place.** Lost: it would show up in every place picker as somewhere to
  keep things.
- **A database unique index.** Lost: deleted records stay in the table (so they can be restored),
  and a refusal from the index would read as a crash, not as plain words.

## What this costs us (the downsides)
- Household stock must be switched on to use the page; with it off, the page says so and links
  to Settings.
- One way between two rooms is kept, not two (a door and an archway between the same rooms is
  recorded once; the notes can say more).
- Connections are not shown on printed sheets yet, and nothing draws them.
- The core gains one more table setting (`pair`) to know and test.
- After Finish setup the household lands on this page instead of Home; one "Skip for now" press
  takes them Home.

## How hard it is to undo
Easy. Remove the page (`web/home_setup.py`, its template, the Home card and the Settings link)
and send Finish setup back to Home. To drop connections, delete the table's declaration and add a
new stock migration that drops `stock__connections`; Places are unchanged either way. The `pair`
setting can stay unused or be removed with the table.

## We should revisit this if
- Households want rooms that are not storage places, or keep asking for two ways between the
  same rooms.
- The exit map is built and needs more than boxes and lines (sizes, floors, positions).
