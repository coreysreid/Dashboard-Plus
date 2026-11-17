# 0056. Home page grouped by area

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The home page had one large tile for every list: about twenty for a household
with everything switched on. It now has one card per area (People, Household
stock, Home layout, Medical readiness, Pets). Each card shows its main list
large with an Add button, its other lists as one short line of links with
their counts, and its sheets to print.

## What we chose
- **One card per module**, headed by the module's title as a real heading.
  Order: People, Household stock, Home layout, Medical readiness, Pets, then
  any other module from A to Z by title. The order is the same every day.
- **A new optional word in `labels.toml`:** `home = "main"` or
  `home = "more"` on a table. Main lists are shown large with the number of
  records and an Add button. Other lists are links in one line, each followed
  by its count. If no table in a module says `main`, the first table that says
  nothing is the main one. So a module with no `home` at all still looks right.
  Any other word is refused when the module loads, with a plain message.
- **Shipped modules:** Household stock marks Stock items as main (Places comes
  first in the file but is not where a household starts). Home layout marks
  Ways out and Shut-offs and power board. People, Medical readiness and Pets
  use the default: their first list.
- **Print links live in their area's card**, still worded "Print: Emergency
  sheet (fridge copy)" so the guides stay true.
- **The last line** now reads "You are tracking: People, Household stock, ..."
  instead of the file names of modules.
- The top cards (Start here, Days of drinking water, Needs attention), the
  backup line and the footer are unchanged.
- The screenshot tool also takes the home page at 320 pixels wide
  (`04b-home-phone.png`), so a narrow screen is checked every time.

### A fault found on the way
Making the screenshots showed that **no form could be saved in a current
Chromium browser**: the committed "home" screenshots were in fact the setup
page, because the setup form had been refused. The pages sent
`Referrer-Policy: no-referrer`; with that, browsers send `Origin: null` with a
form, and the program rightly refuses a form that does not say it came from
this computer. The pages now send `Referrer-Policy: same-origin`: other sites
still learn nothing, and our own forms say where they came from. The check
itself is unchanged, and a test holds both halves.

## Why we chose it
- Calm: five cards replace about twenty tiles, and the page fits roughly one
  screen and a half instead of four.
- Nothing is lost: every switched-on list is still one click from home, and a
  test checks that for the real modules.
- Declarative: a module author chooses the main list with one word in a file
  they already write. No Python names a list.
- Accessible: each area is a section with its own heading, so a screen reader
  can jump between areas; each Add button says which list it adds to; links
  say what they open; the cards stack in one column on a phone.

## What else we considered
- **A `home = "hidden"` choice.** Left out: a list nobody can reach from home
  is a trap for a household. It can be added later without changing the rest.
- **Ordering areas by a number in `module.toml`.** Numbers chosen by separate
  authors collide, and the household-first order is a product choice, so it is
  one short list in `src/dashboard/web/home.py`. New modules need no entry;
  they follow from A to Z.
- **Keeping all the Print buttons in one row at the top.** Six buttons made
  the top of the page busy; beside their own lists they are easier to find.
- **Accepting `Origin: null` on forms.** That would weaken the check; changing
  the header keeps it whole.

## What this costs us (the downsides)
- Secondary lists have no Add button on home; adding to them takes two clicks
  (open the list, then Add) or happens from the parent record's page.
- The household-first order names five modules in code. A sixth "core" area
  would need a line added there.
- A printed sheet is now found in its area rather than in one row; someone
  used to the old row has to look once.
- Counts on secondary lists are a bare number after the link, which is brief
  rather than explanatory.

## How hard it is to undo
Easy. The `home` word is optional and affects only the home page; removing the
grouping means restoring the old loop in `home.html`. No data is involved.

## We should revisit this if
- Corey or a tester cannot find a list or a sheet from home.
- A module needs three or more main lists and its card grows long.
- A module author asks for a say in where their area sits.
