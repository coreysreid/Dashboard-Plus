# Batch 23 item 112: re-walk after the tidy (0131 to 0136)

Checked 27 November 2026 on Lane A's branch `claude/eloquent-hypatia-0gw2qn` at `eeb6eac` (main plus 0139 and
0140; 0131 to 0136 are on `main`). Smith, Garcia and Taylor were loaded fresh. At 320px, Chromium (Playwright)
opened Home, Needs attention, Things to do (Today, This week, Calendar), a pet's page and two people's pages. On
each page the walk pressed Tab until focus came back round, recording each stop's name, whether it had a visible
focus mark and whether it ran off the right edge. It also read the page's accessibility tree, which is what a
screen reader announces. Not a done day and its Undo were run end to end on Smith's car service, using the keyboard.

## Findings, worst first

### Important: a record's page puts the cursor in its first field

- **Where:** every record page: Rex (`/t/pets__pets/1`), John Smith, Rosa Garcia, Sam Taylor.
- **What happens:** The page opens with the cursor already in **Name** (`autofocus` in `_field.html`). A screen
  reader starts at "Name, edit text, John Smith" and skips the page heading. A keyboard user must Tab through
  every field, Save, Cancel and the folded Add list before reaching the weight chart, the calendar or "What
  happened". On Rex's page that is about 25 stops. A stray key press types into the name.
- **Why it matters now:** since 0119 to 0130, a pet's or person's page is mostly a page to *look at* (weights,
  feedings, timeline), not only a form.
- **Suggested change:** only put the cursor in the first field on **Add** (`/new`) and after a failed save. On an
  existing record, start at the top, as other pages do.

### Important: after "Not a done day", focus goes back to the top of the page

- **Where:** Smith, `/calendar/vehicles__services?month=2026-09`, after an earlier service date (1 Sep, changed
  to 10 Sep ten days later) was read from history.
- **What happens:** The button's full name is good: "Not a done day — remove from the calendar: Family car:
  Routine service: Service or check done (an earlier time, from its history), Tue 1 Sep". After Enter, the notice
  says **"Taken off the calendar: Family car: Routine service, Tue 1 Sep. Its history keeps this, and Undo puts it
  back."** with **Undo**. But focus is on the page itself. A keyboard user must Tab through the header, Show and
  month links to reach Undo. A screen reader may not announce a `role="status"` that is already on the page when
  it loads.
- **Suggested change:** move focus to the notice after the redirect (give it `tabindex="-1"` and focus it), as the
  error summary already does in `form-helpers.js`. Then Tab reaches **Undo** next. Undo worked: **"Put back on the
  calendar: Family car: Routine service, Tue 1 Sep."**, and the day came back.

### Minor: Home's card names are not part of the headings

- **Where:** Home, all three households. The screen reader hears plain text "Things to do", then a level-2
  heading **"2 due or late today · 2 this week"**. The same happens for "Days of drinking water" with "About 2.5
  days of drinking water", and "Needs attention" with "5 running low · 16 expiring · 3 to fill in".
- **Why it matters:** someone moving by headings hears the numbers without knowing which card they belong to.
- **Suggested change:** put the card's name in the heading (**"Things to do: 2 due or late today · 2 this
  week"**, with the name styled small as now), or make each card a region named after its title, as "Food put
  out today" already is.

### Minor: history lines mix date styles and show empty quotes

- **Where:** John Smith's page, History: **"2026-11-27 15:38 · You changed: Birthday from "" to "14/03/1984";
  Email from "" to …"**. On the car service: "2026-09-11 08:00 · You changed: Last done from "01/09/26" to
  "10/09/26"".
- **Suggested words:** the time in the household's style (**"27/11/26, 3:38 pm"**), and **"You added: Birthday
  14/03/1984; Email …"** when the old value was empty.

### Minor: "(an earlier time, from its history)" on the calendar line

This is accurate, but it is the system's word. Suggested words: **"(an earlier date you recorded)"**.

### Minor: the chart dots' focus mark is faint

On Rex's weight chart, Tab reaches each dot ("30/07/26: 19.4 kg"), but the mark is only a thicker outline on a
small dot and an underline (`.chart-svg a:focus { outline: none }`). Suggested: keep the browser outline, or draw
a 3px ring around the focused dot in the text colour.

### Minor: no "Skip to main content"

Every page has 7 header stops before the page's own content (Dashboard Plus, On this computer only, Things to do,
Needs attention, Review, Settings, Save and exit). Home has about 104 stops in all. Landmarks exist, so this is not
a failure, but a first hidden **"Skip to main content"** link helps keyboard users who do not use landmarks.

## What held

- No page was wider than 320px; no focus stop ran off the right edge; every stop except the chart dots had a
  visible outline.
- **Folded Add list:** people's pages show one **"Add something linked to John Smith…"** (18 choices; 15 for
  Sam Taylor), closed, opened by Enter, announced as a group with its name. Folded bars (**"Show the bars: Rex · 14
  days … · 240 g put out"**) open with Enter and say what is inside before opening.
- **Link names:** "Look at this: Have you thought about two ways out of the rooms people sleep in?" and "Not now:
  …" name their question. No two links with the same name went to different places on the pages walked.
- **Not a done day and Undo** changed only the calendar. The record's history kept both lines ("You said 01/09/26
  was not a done day: taken off the calendar" and "You put 01/09/26 back on the calendar").

## Limits

A real screen reader (NVDA, VoiceOver, TalkBack) was not used; the accessibility tree was read from Chromium. The
history dates were aged by hand in a throwaway copy to make an earlier day count, because a same-day correction is
correctly not a done day (decision 0129).
