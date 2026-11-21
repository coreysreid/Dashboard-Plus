# Feeding log checks

Written **21 November 2026**. All data is invented. These checks cover the proposed UI and core additions as well as the draft schema.

1. Load Smith's two Rex rows and Garcia's two Luna rows. Taylor has no pet; no example feeding is invented for Taylor. A row must link to a real pet, and deleting a pet holding feedings is refused until a person resolves its history.
2. Add a bowl event, refill and treat; a refill adds only the new food. Correct a mistaken amount on the same event ID and revision; the accepted daily total changes once.
3. Save a measured 120 g and 1 pouch on one day: show two totals, never 121 of anything. Add an unmeasured row: show an incomplete recorded total and its unmeasured count. Never claim consumption.
4. Use the household's local day around midnight and a daylight-saving change. An event keeps its instant, zone and local-date attribution after phone sync; a late accepted event updates the original day.
5. Phone offline save survives restart; double tap or transfer retry creates one Review request. A staged event is distinct from accepted total; rejected event remains available for correction, and only a pulled acceptance changes Home.
6. A helper without the table grant cannot read or suggest feedings. With the grant, a new event waits on Review. Present two matching requests from different routes as possible repeats; a person can keep both real feedings or reject one. Source/reason never becomes a feeding note.
7. At 700 and 1,000 invented events per pet per year, the phone list is paged, day total and 14-day sheet stay responsive, and a requested print either includes every row in range or says it cannot. No silent 200-row truncation.
8. A no-entry day says **No feeding entry recorded today**. It does not trigger a missed-feeding warning or infer a dietary target. A member with an old pull shows the age of the data.
