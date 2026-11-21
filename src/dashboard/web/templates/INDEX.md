# src/dashboard/web/templates/  (summary: HTML pages; base.html holds the shared look)
| Entry | What it is | Open it when |
|---|---|---|
| base.html | Shared layout, colours (light and dark), header and footer | changing the overall look |
| home.html | Home page: days of cover, needs attention, tables with counts, backup and data file status | changing the home screen |
| attention.html | Running low, expiring soon, days of cover with the working shown, and gaps worth filling in | changing the attention page |
| count.html | Count this batch: the count, its review and what was saved | changing the stocktake wording |
| import.html | Import from a spreadsheet: choose a list and file, match columns, see which rows are ready, send to Review | changing the import wording |
| grid.html | A table's records, a page at a time, sortable | changing the list of records |
| rows.html | One page of grid rows (also loaded as you scroll) | changing a row |
| form.html | Add and edit forms, delete and restore, and history | changing the form |
| action_form.html | An action's small form, such as Mark done: what it asks, the next-date choice, Save once | changing the Mark done wording |
| _*.html | Pieces shared by both forms: one field (_field), and the forms' styles and browser code (_form_script) | changing every form at once |
| home_setup.html | Set up my home: add rooms and storage spots, rename, move or delete them, and connect rooms; no scripts needed | changing the Set up my home wording |
| setup.html | First-run wizard and Settings (one form, two modes) | changing setup questions |
| *sheet.html | A printable sheet styled to fit one page (sheet), and the step before one with private details (private_sheet) | changing how sheets print |
| start.html | Shown to a browser that was not opened by the shortcut | changing that message |
| report.html | Shown after saving a report | changing that message |
| close*.html | The "Save and exit" page, and the page shown after a safe close | changing how closing works |
| error.html | Plain-language error page with "Save a report" | changing error wording |
| helpers.html | Settings, Helpers: the helper list, the address, and the form that makes a key | changing the Helpers settings page |
| helper_key.html | The one page that shows a new helper key, with a Copy button and a warning to keep it private | changing the new-key page |
| helper_connect.html | "Connect an AI assistant": settings to paste into an assistant's app, with a placeholder for the key | changing the assistant set-up words |
| review.html | Review: each helper's waiting suggestions with Accept and Reject | changing the Review page |
| helpers.html | Settings, Helpers: the helper list with Make a new key and Turn off access, and the form that makes a key | changing the Helpers settings page |
| helper*_key.html | The one page that shows a key: helper_key for a new helper, helper_new_key for a new key for one already made; each with Copy and a warning | changing the key pages |
| helper_connect.html | "Connect an AI assistant": settings to paste into an assistant's app (pointing at the address file), with a placeholder for the key, and Connection details | changing the assistant set-up words |
| helper_start_message.html | "Starting message for your assistant": the guide for one helper to paste into its chat, with a Copy button | changing the starting message box |
| review_line.html | Choose item for a receipt line the helper could not match: pick or make the item, confirm amount and date | changing the Choose item screens |
| review_batch.html | Open earlier receipt: what became of each row of a receipt, read only | changing the earlier receipt page |
| export.html | Settings, Export my records: what is in the export and the download button | changing the Export page |
| restore_*.html | Settings, Backups: the list of backups, the check-and-compare page, the result, and the shared Undo restore box | changing the restore pages |
