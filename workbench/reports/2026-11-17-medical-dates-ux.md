# UX check after Medical and local-date merges

Checked **2026-11-17** against `main` at `348d9c8`. Loaded Smith, Garcia and Taylor into separate temporary folders with `tools/load_example.py` (85, 80 and 36 records). Opened Home, Needs attention, Stock places/items/movements, all three Medical lists, the First aid at home print sheet and Settings through the local web app. Read [Smith's First aid kits screenshot](../../docs/screenshots/smith/18b-first-aid.png), [Garcia's](../../docs/screenshots/garcia/18b-first-aid.png), and [Taylor's](../../docs/screenshots/taylor/18c-first-aid-sheet.png). Tested day-first and US month-first date parsing and display, including impossible dates and leap years. Only invented example data was used. This was a route, screenshot and source review, not a timed browser or screen-reader session.

## Findings, worst first

### 1. Important — a kit in the car satisfies the question about a kit at home (J3, J5)

**Did:** Opened Smith's First aid kits list and Needs attention. The only kit is **Car first aid kit**, at **Car › Car boot**. The list and screenshot show its place clearly. Needs attention has no kit-at-home question.

**Expected:** A kit stored in a car should not answer **“Is there a first aid kit at home?”** The household should either record a home kit or explicitly answer that they rely on the car kit.

**Happened:** The Medical `none` gap checks whether *any* kit exists. One car kit suppresses the question, although the question specifically says “at home.” This could overstate readiness when the car is away.

**Suggested change and exact words:** Until the core can check a kit's place against the household's home places, ask **“Where can you find a first aid kit when you are at home?”** and require a household answer. Once that place check exists, show **“No first aid kit is recorded at home. Add one, or confirm that the car kit is available when needed.”** The core needs a place-scoped gap, or a separate explicit confirmation; a plain `none` rule cannot establish this. Do not infer availability from the kit name.

### 2. Minor — a wrong-order date gives no preview or correction (J2, J5)

**Did:** Read the new date field and its preview logic, then checked `20/05/27` and `05/20/27` in day-first and US month-first styles. The server correctly saves the locally ordered date and refuses the other one. In the field's preview logic, a syntactically valid date in the wrong order returns `null`, so the preview stays blank. An impossible in-order date instead says **“Not a real date”**.

**Expected:** A household typing the other country's order should learn the expected order before pressing Save. This matters for a plausible but ambiguous date such as `05/06/27`.

**Happened:** The hint gives `DD/MM/YY` or `MM/DD/YY`, but the live preview does not explain why `05/20/27` in an Australian form, or `20/05/27` in a US form, has no preview. The eventual server error is correctly format-specific.

**Suggested change and exact words:** When a nonempty entry does not parse in the household's style, show **“Use DD/MM/YY, for example 20/05/27.”** in day-first households, **“Use MM/DD/YY, for example 05/20/27.”** in the US, or **“Use YYYY-MM-DD, for example 2027-05-20.”** in Canada. Reserve **“Not a real date”** for an impossible day, month or leap day *in the expected order*. Keep the in-words preview for a valid date.

## Journey coverage and what worked

- **J1, first ten minutes:** The existing Smith, Garcia and Taylor examples loaded without the prior Medical kit-check loader error. Home, People-linked Medical records and Stock routes rendered. A fresh setup wizard was not timed in this check.
- **J2, shopping:** Stock items, Places and Stock in and out rendered for all three. A typed `20/05/27` saves and displays as `20/05/27` in day-first style; US `05/20/27` stores the same day and displays as `05/20/27`. The live-preview wording issue is finding 2. Lots and receipt entry have not landed.
- **J3, power out:** Needs attention and First aid at home rendered for each household, with the kit's full place path and local dates. Smith's car-only kit creates finding 1. These checks did not simulate an outage or verify a physical kit.
- **J4, handing it on:** Settings rendered for all three. Copying a folder, backup recovery and restore were outside this screen check; the household restore design remains in batch 5 item 11.
- **J5, something expires:** Needs attention renders Medical kit-check dues with **“due”** in the US example, and locally ordered dates. The date parser refused `31/04/27` and `29/02/27`, accepted `29/02/28`, and kept two-digit years in 2000–2099. Date-input feedback is finding 2. Stock lots have not landed.

The findings describe current program behaviour and screenshots checked on 2026-11-17. They make no external medical or preparedness claim.
