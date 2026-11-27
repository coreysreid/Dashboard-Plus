# A medication plan, not just a log (batch 23 item 119)

Written 27 November 2026 against `main` at `2d9fca8`: Medicine doses (0120), the Dose calendar and private lists
(0121, 0123), bars (0124), the timeline (0126, 0130), and Bring in (0137). Today the app records doses a person
says were given. It has no idea what was meant to happen, so it can never say "not recorded yet". This plan adds
that, without ever saying "missed", giving advice or letting a helper write.

## What a planned dose is

A **plan** belongs to one person and one of their own medication details (the same `link_rule` as a dose: same
person, kind = medication). It says:

| Field | Words | Notes |
|---|---|---|
| For | Rosa Garcia | the person; required |
| Medicine | one of her medication details, after Show | required, private |
| Times of day | "8:00 am, 8:00 pm" (one to six times) | the household's own clock (0110) |
| Days | Every day · Some days of the week (Mon … Sun) · Every N days | |
| From | a date, default today | required |
| Until | optional date; "Leave blank if there is no end date" | |
| Amount each time | optional, with Unit, copied from the pack | private, like a dose's amount |
| Paused | yes or no | a paused plan shows nothing |

A plan is **the household's own note of what the pack or the doctor says**. The form says: **"Copy this from the
pack, the label or the care plan. Dashboard Plus does not tell you what to give or when."**

A plan **never changes a dose** and **never creates one**. Only a person's Record a dose does.

## How a planned time meets a recorded dose

A planned time (Rosa, Metformin detail, 26 Nov 8:00 am) is **recorded** when a dose of that medication detail
for that person is recorded within a window around it: by default 2 hours either side, matching the shipped repeat
question (120 minutes). Each dose can meet one planned time, the nearest. That is all the app works out. It never
guesses why a time has no dose.

| State | When | Words |
|---|---|---|
| Planned | the time is later today or in the future | **"8:00 pm · planned"** |
| Recorded | a dose met it | **"8:00 am · recorded at 8:10 am"** |
| Not recorded yet | the window has passed with no dose | **"8:00 am · not recorded yet"** |
| (nothing) | before the plan's From, after Until, while paused | nothing is shown |

**Never:** "missed", "late", "overdue", "skipped", red, a cross, a streak or a percentage of doses taken. A
dose may have been given and not written down, given at another time, or rightly not given. The page says
once, under the day: **"Not recorded yet only means no dose was written down near that time. Check the pack or
care instructions; Dashboard Plus does not know whether a dose was needed."**

A household can close a "not recorded yet" time with **"Not needed this time"**. It writes a history line (like 0132's
"Not a done day"), never a dose, and has **Undo**.

## Where it shows

**Dose calendar (0121), before Show.** A day with planned times shows ◇ and how many, using the calendar's
existing **Planned date** look and words. A day with recorded doses shows ● as today. The day list in words:
**"Thu 26 Nov: 2 doses recorded · 1 planned time not recorded yet"**. No medicine, time or amount appears before
Show. The legend adds **"◇ Planned in this person's medication plan"**. The blank-day sentence stays: "A blank day
has no dose entry recorded. It does not mean anything was missed."

**After Show**, on the day page:

> **Thursday 26 November · Rosa Garcia**
> ● 8:00 am · Metformin 500 mg … · recorded at 8:10 am
> ◇ 8:00 pm · Metformin 500 mg … · not recorded yet · **Record a dose** · **Not needed this time**

**A person's page:** "Medicine given today" (the existing panel) gains one line before Show: **"3 planned today: 1
recorded, 2 still to come"**. Later in the day, with nothing recorded near a passed time: **"1 planned time not
recorded yet"**. It is a count, never a name.

**Home and Needs attention:** not shown. A medication plan is private (0121). If the household turns on **"Show a
count on Home"** (off by default), Home says only **"Medicine plan: 1 planned time not recorded yet today"**, with
no name or medicine, and links to the person's page.

**Things to do:** not shown (a private list), as today.

**Timeline:** unchanged. "What happened" lists what happened (doses), not plans.

**Bars:** unchanged; a plan is not a measurement. No "taken versus planned" chart (see item 132's warnings).

## Empty states

| Place | Words |
|---|---|
| Person with no medication details | **"Add a medicine to Rosa Garcia's private medical details first; a plan uses one of them."** |
| Person with details but no plan | under Medicine given today: **"No medicine plan. Add one if you want planned times shown on the Dose calendar."** (a link, folded) |
| Plan with no times | the form refuses: **"Add at least one time of day, like 8:00 am."** |
| A paused plan | on the plan's page: **"Paused: nothing is planned until you turn it back on."** |
| A plan that has ended | **"Ended on 30/11/26. Its past planned times stay on the calendar."** |

## Privacy

- The plan table is **private** (0121): counts only until a pressed Show; never on sheets, the spreadsheet
  export, the helper API or the connector; `suggestions = false` so no helper can suggest one or a dose.
- Its times and days are private too: "8:00 am and 8:00 pm" for a named person says a lot.
- **Other computers (0140):** starts **Only on this computer**. Sharing asks "Start sharing these private
  things?" and names "Medicine plan: who, which medicine, times and days, and amounts".
- Bring in (0137) is not offered for plans: a plan is a few rows, typed once.

## Checks

1. A plan with 8:00 am and 8:00 pm and a dose at 8:10 am: the calendar shows 1 recorded and 1 planned, with no
   medicine named before Show.
2. A dose at 10:30 am meets the 8:00 am time (within 2 hours); a dose at 11:00 am does not, so 8:00 am is "not
   recorded yet" and the 11:00 am dose stays an ordinary dose.
3. Two doses near one time: one meets it, the other stays an ordinary dose; nothing is called extra or a double dose.
4. No page, export, sheet or helper response contains "missed", "late" or "overdue" for a plan (search the HTML).
5. "Not needed this time" writes history, adds no dose, and Undo restores "not recorded yet".
6. Changing the plan's times changes only future times; earlier days keep the plan that applied then (plans are dated).
7. A daylight-saving change day uses the household's clock, so 8:00 am is still 8:00 am (0110, 0114).
8. Before Show, the dose calendar's HTML has no medicine name, time of a planned dose or amount (item 108's markers).
9. A helper key cannot read or suggest plans (404 and refused), and Import to Review refuses the table.
10. A paused or ended plan adds nothing new; past days keep their planned marks.
11. At 320px, the day page's two buttons wrap and stay labelled with their time and medicine for screen readers.
12. The Home count is off by default; when on, it names nobody.

## What the core must add

- **A dated plan that expands into planned times** for a day range, in the household's zone, with plan history
  so changing a plan does not rewrite past days.
- **A matching rule** between a private plan and a private log (nearest dose within a window, one each), declared
  in `tables.toml` without naming the module.
- **The calendar's Planned look on a private calendar** (0119's `planned` look exists; 0121's private calendars do
  not use it yet).
- **"Not needed this time"** as a history entry with Undo, like 0132.
- **An optional, nameless Home count** for a private list.
- **A table-level `travels = "never"`** (0140, on Lane A's branch).

## Not in this plan

Reminders that pop up or make a sound, refill counts from Stock (a later link to item 120's thinking), and any
advice. Decision 0120 stays: a record, never advice or a schedule the app enforces.
