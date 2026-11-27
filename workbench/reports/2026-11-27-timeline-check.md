# Batch 22 item 109: the "What happened" timeline, checked

Checked 27 November 2026 against `main` at `2d9fca8` (decisions 0126 and 0130 merged). Pages: the panel and the
full timeline (`/timeline/<list>/<id>`) for pets, people, Home care jobs, vehicles and routines, in Smith, Garcia
and Taylor, at 320px and 1280px, and in print media. Two copies with made-up extra rows tested the hard cases:

- **"bars" (Smith copy), Rex:** 184 feedings every three days from May 2025, two weigh-ins on the same day
  (21.3 kg and 20.9 kg on 25 Nov), a heavier weigh-in on 10 Nov (22 kg), a deleted 30 kg weigh-in, feedings in
  grams, pouches and with no amount, and one waiting in Review;
- **"leak" (Garcia copy), Rosa:** three doses of two medicines with unique invented names.

## Findings, worst first

### Minor: two weigh-ins on one day say "since 25 Nov" on 25 Nov

- **Where:** Rex's full timeline. **"Weigh-in · Wed 25 Nov · 20.9 kg · down 0.4 kg since 25 Nov, from 21.3 kg to
  20.9 kg"**. Nothing says which of the two came later, and the two lines are not in time order.
- **Suggested words:** for a weigh-in after another on the same day, **"down 0.4 kg since the earlier weigh-in
  that day"**. Order same-day weigh-ins by when they were saved, newest first.

### Minor: the marks change meaning between lists, and there is no legend

- **What happens:** ● is a feeding on a pet and a service estimate on a vehicle; ✓ is a treatment on a pet, a dose
  on a person and work done on a job; ◆ is a weigh-in and an odometer reading. The Dose calendar uses ● for the
  same doses the timeline marks ✓. Marks are hidden from screen readers and every line starts with its words, so
  nothing is lost; a sighted reader comparing the calendar with the timeline may be confused.
- **Suggested change:** use the calendar's mark for the same records (● for a dose recorded, as on the Dose
  calendar). Add one line under the heading: **"Each line says what it is; the marks only help the eye."**

### Minor: a feeding with no amount just stops

- **Where:** "1 feeding recorded on Sat 21 Nov · See this day". The bar chart and day page say "no amount".
- **Suggested words:** **"1 feeding recorded on Sat 21 Nov, no amount written down · See this day"**.

### Minor: possessives on names ending in s

**"Home · Water the windowsill herbs's page"**, **"Rosa Garcia's page"**. Suggested: **"Home · Back to Water the
windowsill herbs"** (see also item 107).

## What held

- **Weigh-in change words:** "up 1.9 kg since 28 Sep, from 20.1 kg to 22 kg"; then "down 0.7 kg since 10 Nov,
  from 22 kg to 21.3 kg". The deleted 30 kg weigh-in on 12 Nov was skipped, both on the list and as the "since"
  reading. The first weigh-in had no change words.
- **Feedings summed per day:** "3 feedings recorded on Thu 26 Nov · 340 g put out", "2 feedings recorded on Tue
  24 Nov · 1.5 g put out", "1 feeding recorded on Fri 20 Nov · 2 pouches put out". Units were never added
  together. The feeding waiting in Review (23 Nov) was not listed, as the heading says ("Only what was written down
  and accepted is listed").
- **Doses name nothing before Show.** "2 doses recorded on Thu Nov 26 · See this day" and "Private history —
  press Show to see what each one was, on that page only." No medicine, amount or giver was in the page. After
  Show the page listed "8:00 am · Zqxmedname 500 mg twice a day" per dose, still without amounts or giver, as
  decision 0126 says.
- **Paging:** 30 lines a page, then **Earlier** (`?before=2026-09-23`). The next page started the day before; the
  code keeps a whole day on one page, so a busy day is never split across pages. The months heading repeats on
  the next page when a month continues.
- **Empty states:** "Nothing recorded yet for Maria Garcia." and "Nothing recorded yet for Water the windowsill
  herbs." The gap sentence never says "missed".
- **Width:** 320px on every page, panel and full timeline.
- **Print:** the Earlier/Newest links and the Show form are hidden; every line prints with its words.

## What vet and doctor visits should add to it

Pets already have **Vet visits** (■, "Vet visit · Mon 28 Sep · Limping on the front left leg"). From walking these
timelines, a household would want to add:

1. **A follow-up date on a vet visit** ("Recheck in 2 weeks"), shown as its own line on the day it falls
   ("Follow-up planned · Sat 12 Dec · from the vet visit on 28 Sep"), and once on Things to do, never "overdue
   visit".
2. **Who they saw**, already a link (`vet`): show the clinic's name on the line, not the cost.
3. **Vaccinations as their own kind of visit**, because they set a due date for the next one (Pets already have a
   due date; the timeline should say "Vaccination given · next due Nov 2027").
4. **For people, a Visits record** (designed in item 118): who, when, why in the household's own short words, and a
   follow-up date. Private like doses before Show (the reason can be sensitive), and never test results, ID or
   Medicare/insurance numbers.
5. **What was given at the visit** (a treatment started), linking to the existing Treatments given line rather
   than typing it twice.

Cost stays off the timeline (it is money; spending has its own bars).

## Limits

Taylor has no pets and no person timeline (Medicine doses is off). No real screen reader was used.
