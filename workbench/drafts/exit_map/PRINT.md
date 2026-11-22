# Batch 21 item 103: the exit sketch on paper

Designed 21 November 2026 from [RESEARCH.md](RESEARCH.md) and [SKETCH.md](SKETCH.md). Fire and Rescue NSW's [home escape plans](https://www.fire.nsw.gov.au/page.php?id=883) and London Fire Brigade's guidance for [houses and converted flats](https://www.london-fire.gov.uk/safety/the-home/escape-plan/escape-plan-houses-and-converted-flats/) and [purpose-built blocks](https://www.london-fire.gov.uk/safety/the-home/escape-plan/escape-plan-blocks-of-flats/) were checked 21 November 2026. The sheet uses our own labels, not their illustrations. It is a prompt to check and practise with local guidance, never a certified route or an instruction during a fire.

## One page a household can understand

The page title is **“Our way-out sketch — draft for practice”**, with **“Reviewed by household on [date]”** or **“Not reviewed yet”** directly beneath it. A date is the person's last review, not an automatic safety expiry. No full street address is needed. The top third is a short warning and a box for **“Outside meeting place: [broad household words / Not recorded]”** and **“Building's own fire plan: Checked / Needs checking / Not a shared building”**. No manager's access code, key location or private person detail appears.

The central area holds simple labelled room boxes grouped by floor, drawn from shared `stock.places`. Connections from `stock.connections` are lines labelled by kind. A possible way outside is an arrow with its destination status. A line is never green or labelled safe. The diagram does not calculate a fastest path or announce two independent exits. If two apparent paths share one hallway or stair, the paper still shows the shared section plainly and says **“These ways may share the same exit. Check them in person.”** Unknown rooms, floors and destinations are visibly marked **“Not mapped”** or **“Needs checking”**, not silently dropped.

The right or lower side is a **“Check together”** panel with five unresolved facts: each sleeping room reviewed, outside destination confirmed, a broad meeting place recorded, help needs discussed privately, and building instructions checked when relevant. Each has **“Recorded / Needs checking”**, never a scored safety badge. A footer names the source record date and prints **“This is a drawing of what you recorded. Check ways out in person, practise together and follow your building's and local fire service's instructions. It does not say a route is safe.”** Before Print, the screen says **“This page shows your home's layout. Keep copies where your household wants them.”**

## Legend printed on the same page

| Mark on paper | Exact meaning |
|---|---|
| Solid rectangle with room name | A recorded room or area, not a measured floor plan. |
| Solid line labelled **Door**, **Open doorway** or **Stairs** | A connection the household recorded; its width, access and usability are unverified. |
| Arrow labelled **Possible way outside · check in person** | A recorded door to outside whose destination the person marked Outside; the program does not validate it. |
| Dashed line or `?` with **Needs checking** | A connection or destination not confirmed. It must not be counted as a second route. |
| **Possible window exit · check locally** | A marker the person explicitly added; never inferred from a room or treated as a safe jump. |
| **No way out recorded** | The household has not entered a connection for that room; it does not prove no way exists. |

Use words and line patterns as well as shape, never colour alone. If a route crosses floors, label the stair on both floor groups and the matching connection ID, rather than drawing an unexplained line off the page. Cupboards, shelves and private access fields stay off the diagram. The sheet may link or print a short source ID for a connection, but no internal database key has to be read aloud to use it.

## Accessible text version

The same print action offers **“Print as text”** and the on-screen drawing has **“Read the connections as text”** immediately after it. The text is a real ordered list, not alt text saying only “map”: floor heading; each room; every recorded connection and its kind; destination status; shared segments; then the meeting-place and unresolved-facts panel. Example with invented Smith data:

> Upstairs — Main bedroom: Door to Hallway. Hallway: Stairs to Front hall on ground floor. Ground floor — Front hall: Door to outside; destination needs checking. Another possible way from Main bedroom: not recorded. Outside meeting place: Letterbox at the front path. Help to leave: needs private discussion.

This does not tell the Smiths to use that route. The text and drawing use the same record IDs and date so a rename or move updates both. A screen reader gets headings, a list and link text naming the room/connection; it never has to trace an arrow. Text print uses high contrast and a readable font. Neither version prints a private People detail, Home layout `access_details`, utility account number or spare-key location.

## One-page limit without losing facts

Offer A4 and Letter. Fit one ordinary home on one page only if every room label, line, legend, warning and text list remains readable. A many-room or multi-floor home may need **“This sketch needs 2 pages to show every recorded place and connection. Print all pages or choose the text version.”** Never shrink below the tested legible size, cut off a floor, truncate the connection list or claim “one-page complete” because only the first 200 rows printed. Every continuation page repeats **“Draft — check ways out in person”**, the floor name and page count. The text version may likewise continue; it must carry the same facts and warning.

For a purpose-built flat, the sheet says **“This sketch does not replace your building's fire plan. Ask the responsible manager or local fire service what applies here.”** The app never chooses “leave” or “stay put” from its room graph. If the building answer is missing, that remains a visible **Needs checking** item on both versions.

## Paper acceptance checks

1. On A4 and Letter, Smith's invented two-floor path and Taylor's flat print with all labels, legend, warnings and meeting-place state; no clipped word at 100% scale. Check dark and light print.
2. Two connections using the same hall/stair never produce “two independent ways out”; the shared segment remains visible in drawing and text.
3. Blank outside destination, balcony and shared corridor read **Needs checking**, not **Outside**. A window has no marker until the household explicitly adds one.
4. An unconnected sleeping room says **No way out recorded**, not “no exit”. A renamed/moved room changes in both versions from its stable ID.
5. Text and drawing enumerate the same room and connection IDs, floor grouping, destination states, meeting place and unresolved facts. Compare a generated inventory, not just visual similarity.
6. Force an oversized three-floor/long-name fixture. The print preview either shows a complete numbered continuation or refuses a one-page claim with the exact message above; nothing is silently omitted.
7. Plant invented private access, medical and utility strings plus a key-safe location. They appear in neither PDF, text print, preview HTML nor helper-facing map description.
8. At 320px, the drawing scrolls inside its labelled region while the text list, warnings and Print as text stay within the viewport and work by keyboard.

The existing core lacks floor/room classification, destination confirmation, a meeting-place record, help-needs acknowledgement, the drawing/print renderer and a shared-data text alternative. [NOTES.md](NOTES.md) remains the implementation handoff. This paper design adds no workaround in a shipped module.
