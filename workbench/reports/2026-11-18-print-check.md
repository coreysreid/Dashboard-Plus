# Print check after Home layout and Vehicles

Checked **18 November 2026** on main `95c8754` with invented Smith, Garcia and Taylor records loaded into temporary folders. [The 84-case matrix](2026-11-18-print-matrix.csv) covers every declared sheet in A4 and US Letter under light and dark color settings. I used Chromium's print renderer, PDF text extraction and page-boundary checks. No shipped or real household data was changed.
Checked **18 November 2026** on main `e188229` with invented Smith, Garcia and Taylor records loaded into temporary folders. [The 84-case matrix](2026-11-18-print-matrix.csv) covers every declared sheet in A4 and US Letter under light and dark color settings. I used Chromium's print renderer, PDF text extraction and page-boundary checks. No shipped or real household data was changed.

| Household | Available sheets | A4 light/dark | Letter light/dark | Paths |
|---|---:|---|---|---|
| Smith | 7: Emergency, private Emergency, supplies, **Our home**, **First aid at home**, Pets, **Vehicles** | 14 PDFs, each 1 page | 14 PDFs, each 1 page | Full nested paths retained in supplies, Our home and First aid. |
| Garcia | Same 7 | 14 PDFs, each 1 page | 14 PDFs, each 1 page | Full nested paths retained in supplies, Our home and First aid. |
| Taylor | 6: the same except Pets, which is off | 12 PDFs, each 1 page | 12 PDFs, each 1 page | Full nested paths retained in supplies and First aid; Our home uses a top-level Hall in this example. |

**Result:** All **80 available-sheet PDFs** have their correct title, fit one page, and have no extracted word outside the A4 or Letter paper bounds. The four Taylor Pets attempts are recorded as `rendered=0` and excluded because that module is off. The print stylesheet sets white paper and black text in both color schemes, hides navigation and keeps table rows together. No overflow or split row was observed. PDF text retained the `›` path delimiter wherever the example sheet had a nested place.

The three new or newly relevant sheets are included explicitly: **Our home** (`/sheet/home_layout/our_home`), **Vehicles** (`/sheet/vehicles/vehicles`) and **First aid at home** (`/sheet/medical/first_aid`). All three returned readable output for each household. Smith and Garcia vehicles are parked in top-level places, so their ordinary Vehicle sheets contain no `›`; I also moved Smith's invented car in a temporary copy to **Garage › Garage shelves** and confirmed the Vehicle sheet showed that full path. Taylor's Our home records use a top-level Hall, so no nested delimiter is expected there. People and Pets sheets have no place column.

The Vehicle sheet omitted the invented private plate `DEMO-AU-001`; this print check did not reproduce a plate leak. The private Emergency sheet remains an intentional sensitive printout, as described in the [item 31 recheck](2026-11-18-sensitive-detail-recheck.md).
The Vehicle sheet omitted the invented private plate `DEMO-AU-001`; this print check did not reproduce a plate leak. The private Emergency sheet was rendered through its explicit `?show=1` reveal route for this synthetic print check; the ordinary route displays an interstitial. Direct access to that query bypasses the warning, as described in the [item 31 recheck](2026-11-18-sensitive-detail-recheck.md).

**Limit:** PDF word-boundary and page-count checks do not prove legibility on every physical printer or catch text clipped inside a CSS box. A paper proof is still useful before a print redesign. The matrix's `outside_page_words`, `title_in_pdf` and path columns preserve the automated evidence. Sources: the shipped template and `sheets.toml` files, the three [example households](../../examples/households/INDEX.md), and `src/dashboard/web/sheets.py`, checked 18 November 2026.
