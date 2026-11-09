# 0038. Printable sheets are declared by modules and printed by the browser

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
A module can describe a one-page sheet, such as the emergency sheet with who
lives here and who to call. The dashboard shows it ready to print, and it works
with no internet.

## What we chose
- `sheets.toml` (DESIGN 5.2): each sheet has sections, each listing one table,
  simple filters (`where`), the columns to print and the order. The module
  checker explains mistakes like any other.
- The page is ordinary HTML with print styling: the header, footer and buttons
  disappear when printed, text is black on white, and a **Print** button opens
  the browser's print dialog (which can also save a PDF).
- Deleted records are left off. Values print the way they read on screen
  (choice labels, linked people's names).
- Private (`sensitive`) columns print only when a section lists them, and then
  the sheet says "This sheet includes private details".
- The home page shows a **Print:** button for each sheet of the modules that are
  switched on; a switched-off module's sheets are hidden.
- Each section prints at most 200 rows, so a sheet stays one sheet.

## Why we chose it
- A paper copy is a resilience tool: it works with the power or internet off.
- Using the browser's printing avoids a PDF library and works on any printer.
- Declaring sheets in files keeps them in the module's hands, so other modules
  (pets, medical) can add their own sheets with no code.

## What else we considered
- Generating a PDF file: one more dependency and harder to make look right on
  every system.
- A fixed emergency sheet in the core: the core must not know about people.

## What this costs us (the downsides)
- How it looks on paper depends a little on the browser and printer.
- Filters are simple equality only; anything cleverer needs a later change.

## How hard it is to undo
Low. One page and one checker function.

## We should revisit this if
- Testers' sheets spill onto a second page.
- Modules need filters that equality cannot express.
