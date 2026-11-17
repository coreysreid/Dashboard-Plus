# Print check: three example households

Checked 17 November 2026 on main `260e829` with **made-up** Smith, Garcia and Taylor data loaded into temporary folders. No shipped files or real household data were changed. The [60-case matrix](2026-11-17-print-matrix.csv) records each route, paper size and color setting. I used Chromium's print renderer through Playwright, PDF text extraction and page-boundary checks. Tested **A4 and US Letter**, **light and dark** for every available sheet in each household. The browser was on Linux; printer drivers and physical printers were not tested.

| Household | Available sheets tested | A4 light/dark | Letter light/dark | Place paths |
|---|---|---|---|---|
| Smith | People emergency; People private emergency; Stock supplies; Medical first aid; Pets details | 10 PDFs, each 1 page | 10 PDFs, each 1 page | Full nested paths in Stock and Medical HTML and PDFs. |
| Garcia | Same five | 10 PDFs, each 1 page | 10 PDFs, each 1 page | Full nested paths in Stock and Medical HTML and PDFs. |
| Taylor | People emergency; People private emergency; Stock supplies; Medical first aid | 8 PDFs, each 1 page | 8 PDFs, each 1 page | Full nested paths in Stock and Medical HTML and PDFs. |

**Result:** All 56 available-sheet PDFs have the correct title, fit one page, and have no extracted word outside the paper bounds. No missing full place path was observed in the Stock or Medical sheets. The print stylesheet sets white paper and black text in both color settings, hides navigation and print controls, and asks Chromium to keep table rows together. This check found no overflow or broken page. The People and Pets sheets do not have place columns, so path checks do not apply.

**Expected unavailable route:** Taylor has Pets switched off. Its `/sheet/pets/pets` returns the access/absence page rather than a Pet sheet in all four combinations. Those four attempted PDFs are recorded as `rendered=0` in the matrix and excluded from the 56 available-sheet passes. The Home page should not offer that link. This is not missing content for Taylor.

**How to reproduce:** Load each example with `tools/load_example.py` into a fresh temporary data folder, open its local dashboard, visit each `/sheet/<module>/<name>` route available from Home, and print with Chromium to A4 and Letter under light and dark color schemes. Compare PDF page count and extracted text with the HTML; check that Stock and Medical places use `Room › Storage › Spot` paths. The matrix's `outside_page_words` flags text extending beyond PDF paper bounds, `title_in_pdf` checks the title, and path flags check the visible `›` delimiter. It does not prove content is large enough to read on every physical printer or detect text clipped *inside* a CSS box. A visual paper proof remains useful before a print redesign.

Source: shipped `src/dashboard/web/templates/sheet.html`, `src/dashboard/web/sheets.py`, module `sheets.toml` files, and the three [example households](../../examples/households/INDEX.md), checked 17 November 2026. No external household advice is asserted here.
