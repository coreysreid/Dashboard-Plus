# UX check after nested Places and data-safety merges

Checked **2026-11-17** against `main` at `435a2e9` (nested Places and subsequent data-safety fixes). Loaded the three made-up example households in separate temporary folders, opened the same local web routes used for J1–J5, read the generated [Smith Places screenshot](../../docs/screenshots/smith/11-places.png), and changed one place only in a temporary copy. Also made a separate 502-place stress fixture to test the long-list find box. No real household data was used. These are local web-route and screenshot checks, not a timed or screen-reader browser session.

## Findings, worst first

### 1. Important — a long Places picker loses a parent and cannot find the child by that parent (J2)

**Did:** In a fresh synthetic household, created `Zzz kitchen`, `A child shelf` inside it, and 500 other made-up places. Opened **Add to stock items** and searched for `Zzz kitchen` in the Place find box. This deliberately crosses the form's 500-place initial list limit.

**Expected:** The child option should read **`Zzz kitchen › A child shelf`**, and typing either `Zzz kitchen` or `A child shelf` should find it. Its full path is the only way to distinguish it from another shelf with the same name.

**Happened:** The initial option reads only **`A child shelf`**, because its parent is outside the first 500 alphabetic rows used to build paths. The fallback search for `Zzz kitchen` returns the parent record only; it searches place names but not their paths. The child therefore cannot be found by the parent part of its path in this large household. This is a scale edge case, but it can cause someone to pick the wrong shelf.

**Suggested change and exact words:** Compute option names from the saved parent chain, regardless of which rows were loaded for the dropdown. Search indexed or computed full paths on the server when the find box reaches past its initial choices. The result should say **`Zzz kitchen › A child shelf`** and keep the existing option **`Not on the list? Add “…” as a new one`** only when no saved path matches. Add a check with a parent outside the first 500 and a child inside it.

### 2. Minor — the Places list makes a reader assemble the path from two columns (J1, J2)

**Did:** Opened the Smith example's **Places** list. Its Shelf 3 row says **`Shelf 3`** under Name and **`Kitchen › Pantry`** under Inside. The [current screenshot](../../docs/screenshots/smith/11-places.png) shows this. The same row's opened page correctly says **`Kitchen › Pantry › Shelf 3`**.

**Expected:** The list's main label should say the full path, like the opened page, Stock items and printed supplies sheet. A household can then scan several identical `Top drawer` rows without mentally joining columns.

**Happened:** The two columns convey the location, but the Name column does not present the full path. Sorting by Name also leaves a child apart from its parent.

**Suggested change and exact words:** In the list's first column, show **`Kitchen › Pantry › Shelf 3`** and call that column **“Place”**. If the Inside column remains for editing context, it can say **`Kitchen › Pantry`**; avoid making it the only way to see the parent. Sort the list by full path so a room is followed by its contents.

## Journey coverage and what worked

- **J1, first ten minutes:** A fresh folder still opens setup. All three loaded households opened Home, People and Places. Their current Places have full paths on opened records; the list presentation is described above.
- **J2, shopping:** Stock items and Stock in and out loaded for Smith, Garcia and Taylor. The Smith stock list and printed supplies sheet showed `Kitchen › Pantry › Shelf 3`. Moving Pantry under Garage changed the Stock item's visible path to `Garage › Pantry › Shelf 3` without moving its stock count. The large-list failure is finding 1. The picker and water findings from [batch 4 item 1](2026-11-17-picking-water-ux.md) remain relevant until fixed.
- **J3, power out:** Home, Needs attention, emergency sheet and supplies sheet rendered in every temporary household from local data. Counted drinking water was 34.4 litres for Smith, 24.7 for Garcia and 12 for Taylor, with Taylor's 1 litre of appliance water excluded. This did not test a physical power cut.
- **J4, handing it on:** Settings rendered for all three; copying a folder to another computer or restoring from a backup was outside this screen check. The data-safety merge changed backup and restore internals; a household restore flow belongs to roadmap item 11.
- **J5, expiry:** Needs attention rendered for all three. Date order is still the earlier ISO presentation in some lists and reminders; Lane A has local dates scheduled after nested Places, so this is carried forward from the [earlier UX report](2026-11-16-ux-check.md), not counted as a new nested-place defect. Lots have not landed yet.

The findings and results above come from local program behaviour and synthetic screenshots checked on 2026-11-17. No outside preparedness claim is made.
