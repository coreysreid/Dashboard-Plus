# 0033. Screens generated from declarations, with a launch-link sign-in

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Every module gets its list, add and edit screens automatically from its files.
The dashboard only works in the browser window that *Open Dashboard* opens.

## What we chose
- **Generated screens.** For each declared table: a grid that shows a page of
  50 records and loads more as you scroll (or with "Show more"), sortable by its
  columns; an add form with "Save and add another" for fast entry; an edit form
  with delete, restore and a plain-language history ("You changed How many from
  "1 each" to "2 each""). Labels, help text, field order and grid columns come
  from `labels.toml`.
- **Friendly values.** Choices show their labels, links show the linked
  record's name, money shows two decimals, measures show their unit, private
  (`sensitive`) values are hidden in lists behind "Show".
- **Mistakes stay on the page.** A form with problems comes back with what was
  typed and a message under each field, and nothing is saved.
- **Launch-link sign-in.** Each start creates a secret. The shortcut opens the
  browser with it once; the browser swaps it for a cookie that other websites
  cannot use (`SameSite=Strict`, `HttpOnly`). A browser without it sees a page
  asking them to use the shortcut. Opening again while running reuses the window.
- **Form protection.** Every form carries a hidden per-start token, on top of
  the host and origin checks from step 1.
- **Save a report.** The error page offers to save a report with the version,
  system name and the end of the log. The log never contains what people typed.
- **Plain HTML with a little JavaScript** (only for loading more rows); no
  browser framework, following decision 0002.

## Why we chose it
- Generated screens are what make "a module is just files" true.
- Fast entry and kept-on-error forms serve the M1 goal of 20 items in under ten
  minutes.
- The launch-link sign-in keeps other programs and websites on the same computer
  from reading the household's records through the browser.

## What else we considered
- A password: more friction for a single-household program on its own computer.
- No sign-in, relying on the local-only address: any web page could try to
  reach it, and other user accounts on the same computer could read it.
- A JavaScript grid library: heavier, and decision 0002 prefers server pages.

## What this costs us (the downsides)
- Bookmarking a page does not work after a restart; the shortcut is the way in.
- Link choices list up to 500 records; very large linked tables will need a
  search box later.
- Generated screens look alike; modules can only shape them through labels.

## How hard it is to undo
Low to medium. The screens live in `src/dashboard/web/`.

## We should revisit this if
- Testers find the shortcut-only rule confusing.
- A module needs a screen the generator cannot express.
