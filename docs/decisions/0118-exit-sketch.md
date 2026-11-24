# 0118. Our way-out sketch: rooms as boxes, connections as lines, drawn on the server with a complete text version

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Claude (technical decision delegated by Corey)
- **Builds on:** 0103 (Set up my home: Places and Connections), 0109 (server-drawn SVG with an equal table), 0108 (drills never certify a route; emergency numbers by country), 0054 and 0077 (Home layout and its private access details), 0100 (what travels), Lane B's draft `workbench/drafts/exit_map/` (batch 20 item 93 and batch 21 item 103; now removed, its RESEARCH, SKETCH, PRINT, NOTES and ACCEPTANCE are in git history), Corey's request in docs/BACKLOG.md

## In plain words
**Our way-out sketch** draws the rooms you entered in Set up my home as boxes, one floor at a time,
with lines for the doors, doorways and stairs between them and an arrow for each door to outside,
plus your outside meeting place. It is "lego level": nobody draws anything; the program lays the
boxes out the same way every time. Underneath is the same thing as a list you can read aloud or
print. You give each room a floor, tick the rooms people sleep in, say where each door to outside
really leads (Outside, a shared building area, or Needs checking), and answer three questions: a
broad meeting place, whether help to leave has been discussed privately, and what your building's
own fire plan says if you live in a flat. The printed page says, on every page, that it is a
practice aid and not a certified or safe route, to check two ways out in person, and in a fire to
get out, stay out and call 000 (or your country's number). If the home does not fit on one page it
prints numbered continuation pages; nothing is cut off. Codes, private People details and notes
never appear.

## What we chose
- **Facts on the existing records.** Household stock gains migration 0007 (four `ADD COLUMN`s, no
  record changed): on Places, `floor` (Below street level, Street level, One to Three or more floors
  up, or Leave off the sketch), `sleeping` and `window_exit` (a possible window exit the household
  ticked after checking it locally; never inferred); on Connections, `destination` for a door to
  outside (Outside, Shared building area, Needs checking; blank reads Needs checking). All travel
  and export like the rest of Places and Connections; nothing here is private (0103).
- **Household answers in Settings.** The meeting place (120 characters, broad words), help to leave
  (Discussed privately / Needs discussion), the building's plan (Checked / I need to check / Not a
  shared building) and the last review (date and a fingerprint) are four `exit_sketch.*` keys in
  `core__settings`, like the household's other answers about itself.
- **Read fresh every time** (`core/exit_sketch.py`). Rooms are top-level Places not left off; a storage
  spot's connection counts for its room; notes are never read. A rename, move or delete shows at once,
  and with Household stock off the page says it cannot show current rooms or ways out (print is 404).
- **Words, never verdicts.** Each room gets only these notes: *No way out recorded for this room*,
  *Only one way out recorded…*, *No possible way outside is recorded from this room yet*, or *These
  ways may share the same exit. Check them in person. Shared: Hallway, the same door to outside* when
  every recorded path to a door the household confirmed as Outside passes one room or one door.
  "Other" connections and unconfirmed doors are dashed and never counted. There is no "two ways out",
  safest or fastest route, and the app never chooses leave or stay put for a flat.
- **Check together:** five facts, each Recorded or Needs checking (sleeping rooms each with a floor
  and a connection, every door out's destination confirmed, a meeting place, help discussed, the
  building's plan when relevant). *We reviewed this sketch together today* is refused, naming what
  is missing, until all five are recorded. **Ready to print for practice** needs that review and no
  change since it (the fingerprint); otherwise the page says *Draft home sketch* or *Changed since
  the household's review*.
- **Drawing** (`web/exit_drawing.py`): SVG on the server as in 0109, no script. Each floor's rooms go
  in a grid of three in a steady order (from rooms with a door out, through their neighbours, ties by
  name then ID), in blocks of up to three rows. Lines join rooms in the same block (a line skipping a
  room bows over it); a connection to another floor, block or a place left off is written under the
  room with its page. Meanings use words and dash patterns, not colour; every box and line links to
  its record; light, dark, high-contrast and print styles. At 320px it scrolls inside its labelled box.
- **Sheet** (`/exit-sketch/print?paper=a4|letter`): page 1 has the title, review line, warnings,
  meeting place, help, building plan, the drawing that fits, legend and Check together; blocks never
  split and go to numbered continuation pages, each repeating *Draft — check ways out in person*, the
  floors and *Page n of N*. More than one page says so before printing. A room with very many
  connections draws the first few and says *And N more: every one is in the text version*.
- **Text version** on the page (`#as-text`, every line a link) and as **Print as text**
  (`/exit-sketch/text`): floor headings, each room, every connection with its kind and destination,
  the route notes, places left off, meeting place, help, building plan, Check together and the
  same warnings. Tests compare the room and connection IDs in the drawing with the text.
- **Links:** Set up my home and the Home card link to it; a drill step whose record match is ways
  out or connections (the bedroom-fire *other way out* step, the kitchen-fire ways-out step) shows
  *See your way-out sketch*. The emergency number comes from a drill module's checked list for the
  household's country, otherwise *your local emergency number*.

## Why we chose it
- Corey asked for simple exit maps "with maybe lego level accuracy"; the rooms and connections he
  already records are enough for boxes and lines with no drawing tool.
- Fire and Rescue NSW and London Fire Brigade (checked by Lane B on 21 November 2026) support drawing
  ways out, a meeting place, practice and planning for help, and say flats follow their building's plan;
  none supports software certifying a route, so the sketch shows only what was recorded and its gaps.
- One read for drawing, text and sheet keeps them equal; reading fresh means nothing stale prints.

## What else we considered
- **A drag-and-drop drawing tool:** needs scripts, is hard to make equal to a text version, and asks for
  precision the household does not need. Not now.
- **Letting the person nudge the order or grouping:** the draft did not ask for it; the floor is the
  grouping the household chooses. Can be added as a sort field later.
- **Meeting place and help as records in a table:** they would export and travel, but a one-row list
  would appear on Home and in pickers. Settings is simpler for four answers.
- **Reading Home layout's Ways out:** they have free-text floors and routes and private access
  details; the sketch stays with Places and Connections so no route text or code can reach it.
- **Shrinking a large home onto one page:** rejected by the draft; continuation pages instead.

## What this costs us (the downsides)
- The meeting place, help and building answers sit in Settings, so they are not in Export my records
  and will not travel to another computer in sync stage 2 without extra work. The review fingerprint
  also lives there.
- The layout is crude: lines may cross, and a line between two rooms in different rows can pass near a
  third box. It is a reminder to walk the route, not a plan.
- The "may share the same exit" check compares every room against every other, slow for a home with
  many hundreds of rooms.
- Page fitting is worked out in drawing units, checked against Chromium's A4 and Letter print, not every
  browser; another browser may need its own print scale.
- Room flags (floor, sleeping, window) are edited on the sketch page, not on the ordinary Places form,
  so a storage spot never shows them.
- Stock module gains four columns; the page depends on Household stock being on.

## How hard it is to undo
Easy. Remove `core/exit_sketch.py`, `web/exit_drawing.py`, `web/exit_sketch.py`, the three `exit_*`
templates and `_exit_parts.html`, the blueprint line in `app.py`, the links on Set up my home, Home
and the drill step, and the browser check step. The four columns can stay unused, or a new stock
migration can drop them; the `exit_sketch.*` settings can be deleted. No other record depends on them.

## We should revisit this if
- Households want to arrange boxes themselves, or the drawing is too tangled to read for an ordinary home.
- A printed sheet is ever read as a certified route, or a fire service asks for different words.
- Sync stage 2 ships and the meeting place should travel (then: move the answers into a table).
