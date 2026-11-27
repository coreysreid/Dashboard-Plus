# Batch 23 item 124: the read-me files, against today's app

Checked 27 November 2026 against Lane A's branch at `eeb6eac`:
- the Windows portable folder's `READ ME FIRST.txt` (`README_TXT` in `tools/build_portable.py`);
- the Mac preview's `READ ME FIRST.txt` (`README_TXT` in `tools/build_macos.py`);
- `README.md`'s opening, "What it does today", "Using it on Windows" and "On a Mac" sections;
- Lane B's `workbench/drafts/guide/GETTING_STARTED.md`.

Each sentence was compared with what the app does now (helpers and the connector, 0138; Bring in, 0137; batches;
restore; sharing choices, 0140 on Lane A's branch). Worst first. The suggested replacements are exact.

## Windows `READ ME FIRST.txt`

| # | Now | Problem | Replace with |
|---|---|---|---|
| W1 | "Your records are kept in the "data" folder next to these files. Nothing is sent anywhere." | Overpromises since the connector (0138): an online assistant sees what a helper reads. The Mac read-me was already fixed (batch 19 item 84). | "Your records are kept in the "data" folder next to these files. Dashboard Plus does not send them to an online service by itself. If you connect an online helper, what you allow it to read may be sent by that helper: check Settings, Helpers first." |
| W2 | (nothing about unblocking) | User 1 hit the "unblock the zip" problem. The fix is only in README.md. | Add before the "Windows protected your PC" paragraph: "Before unzipping, right-click the zip, choose Properties, tick Unblock and click OK. Only for a zip from this project's GitHub page." |
| W3 | "To update the program, replace everything except the "data" folder." | Right, but it does not say that a backup is made, or where backups are. | "To update, click Save and exit, then replace everything except the "data" folder. The next start backs up your records first. Backups are in data\backups and in %LOCALAPPDATA%\Dashboard Plus\backups." |
| W4 | "This is an early test version." | Still true; keep it. Add a line on moving computers. | "Moving to a new computer? Copy the whole Dashboard Plus folder, data included, or see Restore from a backup in Settings." |

## Mac `READ ME FIRST.txt`

| # | Now | Problem | Replace with |
|---|---|---|---|
| M1 | "Your records are kept in your own Mac account, in Library/Application Support/Dashboard Plus …" | The second backup copy is somewhere else (`~/.local/share/dashboard-plus`), which README.md admits but this file does not (also item 123). | Add: "A second backup copy is kept in .local/share/dashboard-plus in your home folder (a hidden folder: in Finder press Command-Shift-. to see it)." Better: fix the folder (item 123). |
| M2 | "To update: Save and exit, then drag the new app into Applications and choose Replace." | It does not say an update backs up first, or how to check. | "…choose Replace. The next start backs up your records before changing anything; check your records are there." |
| M3 | "If you connect an online helper, information you allow it to read may be sent by that helper." | Good. Keep it. | — |

## README.md

| # | Where | Now | Problem | Replace with |
|---|---|---|---|---|
| R1 | Opening | "Everything stays on your own computer. Nothing is sent anywhere unless you switch on an optional outside source." | A connected online helper is not "an outside source" in a household's words, and other computers (0140) are coming. | "Everything stays on your own computer. Nothing is sent anywhere unless you choose to: connect a helper (an AI assistant you give a key) or, later, pair another computer of your own." |
| R2 | Status | "Status: an early test version of the first release (M1)." | The app now has M2 and M3 features (helpers, sync stage 1, Bring in). | "Status: an early test version. It works, but it is new: keep a copy of anything important somewhere else too." |
| R3 | What you paid | "Prices stay on this computer and are never on lists, sheets, the export or a helper's screen." | With 0140, prices can be shared with the household's own other computers, by choice. | "Prices are never on lists, sheets, the export or a helper's screen. They stay on this computer unless you choose to share them with your other computers." |
| R4 | The first charts | "**The first charts:** …" | There are now many charts; "first" reads as dated. | "**Charts:** …" |
| R5 | Calendars and trends | "**Things to do** has a **Calendar** tab for Routines: …", then later "The **Calendar** tab now shows every dated list together" | Two stages of the feature, one after the other; a reader cannot tell which is true. | Start with: "**Things to do → Calendar** shows every dated list together: …" and remove "for Routines" and "now". |
| R6 | Bars over time | "until then the chart says "this person" and its chooser lists people by number" | True today, but a household reads "by number" as a fault (item 106 suggests "Person 1 of 2"). | Keep until the words change, then "…and its chooser lists Person 1, Person 2 …". |
| R7 | Helpers (early) | "Private details are never shared with helpers." | True for sensitive fields, but a medicine or code typed into an ordinary note is not caught (item 114). | "Private details (the fields marked private) are never shared with helpers. Do not type codes or medicines into ordinary notes." |
| R8 | Using it on Windows | "Nothing is installed, no administrator rights are needed, and no settings on the computer are changed." | The second backup copy writes to `%LOCALAPPDATA%`. That is not a setting, but it is outside the folder. | "…and no settings on the computer are changed. A second backup copy is kept in your account's local app data folder." |
| R9 | Where your data is | "To **start a fresh copy** for someone else, copy the folder without its `data` folder" | Right. Add the opposite case: moving. | Add: "To **move to a new computer**, copy the whole folder with its `data` folder." |

## Getting started (Lane B's draft, `workbench/drafts/guide/GETTING_STARTED.md`)

Item 117 rewrites the guide, so these are listed for it, not fixed here:

| # | Now | Problem | Replace with |
|---|---|---|---|
| G1 | "If you already have that item, open it and correct its **Amount on hand**." | Amounts now come from batches ("Amount on hand: 20 litres, in 1 batch"); a stocktake uses **Count this batch**. | "If you already have that item, open it and use **Count this batch** to record what you counted." |
| G2 | "Today, an item has one Use by date; separate dates for different batches are planned" | Batches shipped. | "Each batch has its own Use by date: add a batch for each date." |
| G3 | "It runs on **Windows 10 or 11**" | There is also a Mac preview. | "It runs on Windows 10 or 11, and there is an early Mac preview (see the README)." |
| G4 | "You can see backup status under **Settings**." | Restore exists. | "Settings shows how the last backup went, and **Restore from a backup** can put one back, with Undo." |
| G5 | Nothing about pets, calendars, bars, timelines, Bring in or helpers | The first ten minutes are still right; the later pages are item 117's. | — |

## Limits

The built zips were not downloaded; the read-me text was read from the build scripts that write it. Windows and
macOS were not used.
