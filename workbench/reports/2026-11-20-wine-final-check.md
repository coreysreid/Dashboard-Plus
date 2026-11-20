# Wine final check against shipped core — 20 November 2026

Checked `origin/main` at `1b303b4` (decision 0095). All names and data below are invented. This is a read-only review of shipped Wine; no module or core files were edited.

## Result, worst first

1. **Minor — update check 14's example expectation.** The old `workbench/drafts/wine/ACCEPTANCE.md` (retained in git history at `35cc315`) says Smith, Garcia and Taylor each have one Wine, Bottle and Tasting row. Decision 0095 deliberately leaves Garcia's Wine switched off and has no Garcia Wine rows. In a disposable Garcia household, all four Wine routes return 404 as expected; Smith and Taylor each show one linked row in the three lists. Lane A should keep decision 0095's behavior and amend any surviving promotion checklist or test plan that still promises Garcia Wine rows. No shipped change is needed.
2. **No other promotion blocker found.** The Wine module has the intended manual counts, free-text places, ordinary price and tasting notes, date validation, linked-delete refusal and snapshot sheet. The shipped tests cover each of the original 15 check areas. The scope limits in decision 0095 still apply: entering a tasting never changes a count; price and notes enter a general export and a Wine-granted helper read.

## The 15 checks rerun

| Old check | Current-main evidence | Result |
|---|---|---|
| 1. Load alone, no host, four routes | `test_1`; Smith and Taylor browser routes opened | Pass |
| 2. Empty lists, required fields, 320px | `test_2`; phone-width Wine routes had zero horizontal overflow | Pass |
| 3. Add and edit invented wine | `test_3` | Pass |
| 4. Two separate Bottle rows | `test_4` | Pass |
| 5. Manual count, tasting does not subtract | `test_5` | Pass |
| 6. Missing-place question and free-text place | `test_6` | Pass |
| 7. Invalid numbers refused; zero allowed | `test_7` | Pass |
| 8. Household date order, impossible/wrong-order dates | `test_8` and `test_8b` | Pass |
| 9. Tasting text rendered as text and exported | `test_9` | Pass |
| 10. Price/export/helper grant and sheet omission | `test_10` and `test_10b` | Pass |
| 11. Sheet contents and print | `test_11`; Smith/Taylor sheet rendered in Chromium to nonempty A4 and Letter PDFs | Pass for checked fixtures |
| 12. Linked deletion refused, restore | `test_12` | Pass |
| 13. Wine off/on retains rows | `test_13` | Pass |
| 14. Three example households | `test_14` and `test_14b`; browser checked Smith/Taylor on and Garcia off | Pass under decision 0095; old draft wording stale |
| 15. Backup, restore, Undo | `test_15` | Pass |

Additional shipped tests check the home card, migration table ownership and absence of drinking, buying or value advice. The 21 Wine tests passed with `PYTHONPATH=src /tmp/dashboard-plus-venv/bin/python -m unittest discover -s tests -p test_module_wine.py -v` (21 tests, 2.022 seconds). Browser ran on disposable example data in Chromium at 320px and 1280px: Wine lists and sheet were HTTP 200 for Smith/Taylor, 404 for Garcia, with zero page overflow in all 24 route checks. Smith/Taylor sheets each generated A4 and Letter PDF bytes; this did not inspect a long-place paper print visually, so the print claim is bounded by the shipped `test_11` content check and the checked example PDFs.

Source: `docs/decisions/0095-wine-promoted.md`, shipped `modules/wine/` and `tests/test_module_wine.py`, and the historical Wine acceptance file. Checked 20 November 2026.
