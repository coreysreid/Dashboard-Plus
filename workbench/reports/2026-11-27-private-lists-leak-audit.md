# Batch 22 item 108: private lists, leak audit

Checked 27 November 2026 against `main` at `2d9fca8` (decisions 0120, 0121, 0123 and 0134 merged). Medicine doses
is the one private table (`private = true`); People's Important details are sensitive cells. A copy of the Garcia
example was given unique made-up markers that occur nowhere else:

- Rosa's medication detail changed to **"Zqxmedname 500 mg twice a day"**, and a second one added,
  **"Qwvsecondmed drops at night"**;
- dose amounts **7.25 ml** and **3.75 drop**.

Every route was then searched for the markers **before Show** was pressed.

## Routes tried

| Route | How | Markers found before Show |
|---|---|---|
| Every GET page reachable by links from Home | 1,500 pages, raw HTML including attributes, hidden inputs, titles and `data-` values: lists, record pages, calendars (all months reached), bar charts (every by and range), day pages, timelines, Things to do, Needs attention, Review, Settings, readiness and drills | none |
| Every link address on those pages | searched each URL | none |
| Typing suggestions `/t/<table>/suggest` | private table and sensitive columns | refused (404), as decision 0121 says |
| A list search (`?q=Zqxmedname`) | Medicine doses and Important details | ignored; the result was identical to a nonsense search, so nothing can be learnt by guessing |
| Sheets, GET | Emergency, First aid, Pets, Supplies | none |
| The private Emergency sheet after its pressed choice (POST) | `people/emergency_medical` | the medication details, by design (the household chose "with private medical details"); no dose amounts |
| Spreadsheet export (zip) | every CSV | no dose table, no medication detail |
| Helper API with a "Look and suggest" key for People, Medicine doses, Stock, Pets, Pet feeding, Medical | `/me`, `/guide`, `/tables`, records, one record, `/attention` | Medicine doses is not offered (404); medication details are not in People records |
| Helper suggestion of a dose | POST `/proposals` | refused |
| Show, then away and Back | Dose calendar | Back gave the browser's error page (ERR_CACHE_MISS, because of `no-store`); nothing came back from history |
| After Show | Dose calendar | names and amounts on that page only; the address stayed `/calendar/medicine_doses__doses`, with no marker in any link |

The private list itself held. Its guards (POST-only Show, `no-store`, no suggestions, no export, no helper
access, counts only on Home, calendars, bars and timelines) all worked.

## Other sensitive fields checked

Focused synthetic checks on the same main revision also passed for Home layout access details, Vehicle plate,
Bills amount/coverage/reference/notes, Vehicle quote amount/scope/notes, Stock prices and refunds, and an export
sentinel in every sensitive column. The ordinary list and sheet responses kept those values closed; export and
helper reads omitted sensitive columns, while a private sheet required its pressed Show action. The relevant
regression coverage is `tests/test_module_home_layout.py`, `test_module_vehicles.py`,
`test_module_bills_insurance.py`, `test_module_vehicle_running.py`, `test_purchase_prices.py` and
`test_export.py` (six focused tests passed). These checks did not find a new pre-Show private-column leak.

**Paired-computer exception:** decision 0111 was amended on 24 November: a Vehicle quote's amount and scope are
private on screen but deliberately `travels = "always"` to paired computers; its notes stay local. Bills details,
Stock price values, refund amounts, plates and Home access codes remain local under their declarations; a refund
record's existence and date can still appear in the filtered change log (decision 0134 leaves that policy open).
“Private until Show”
therefore describes the local screen, not a promise that every private value stays on one computer.

## Findings, worst first

### Important: the same medicine, typed as a Stock item, travels everywhere the private list does not

- **Where:** the shipped Garcia example, `examples/households/garcia.toml` line 442: Stock item
  **"Metformin 500 mg (Rosa)"**, category First aid, notes "Two a day. Refill at 30…".
- **What happens:** That one name says who takes which medicine, at what strength and how often, which is exactly
  what the Dose list and the medication detail keep behind Show. It appears on **Needs attention** ("Metformin
  500 mg (Rosa): 20 left, keep at least 30"), the **Stock** list, the printable **Emergency supplies** sheet, the
  spreadsheet **export**, and the helper API's **`/attention`** and **`/tables/stock__items/records`**.
- **Why it matters:** A household keeping a medicine in the cupboard (a sensible thing to track) gets no word that
  Stock is ordinary information. The example teaches the leak.
- **Suggested changes:**
  1. Example: rename the item **"Prescription tablets (blister packs)"** with notes **"Refill at 30."**, so the
     example shows the safe habit.
  2. On the Stock form, when the category is First aid or the name matches a People medication detail, say below
     the name: **"Stock is ordinary information: it shows on Home, printed sheets, the spreadsheet and to helpers.
     To keep a medicine private, name it here in general words and keep its details in the person's private
     medical details."**
  3. Decision 0140 (a sharing choice for every kind of information) should treat a Stock item in First aid as its
     own kind, so a household can keep it off helpers and other computers.

### Minor: "Given to #4" is a database number

Before Show the dose calendar and bars name the person "Given to #4" (also in item 106). It hides the name, but it
shows how records are numbered and confuses households. Suggested words: **"Person 1 of 2"**.

### Minor: the private Emergency sheet is a pressed choice, but its print has no reminder

The sheet with private medical details prints medication names, as chosen. Suggested footer on that sheet only:
**"This copy has private medical details. Keep it with the person, not on the fridge."**

## Not tried

Real browser history and autofill on a household's own browser profile (the container's Chromium was fresh), the
MCP connector process (the same `/api/v1` routes it calls were tried directly), and other computers (sync stage 2
is not built). Screenshots are not attached because the markers are the evidence; the rows above can be
reproduced by loading Garcia and editing the three values.
Review can display text a helper itself supplied in `why` or receipt source lines; exact-match warnings cannot
guarantee removal of a paraphrase. That is a trust-boundary limit of free text, not a confirmed private-column
escape in this audit.
