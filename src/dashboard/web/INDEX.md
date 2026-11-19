# src/dashboard/web/  (summary: the screens: pages, forms and their protections)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Web layer: pages, forms, the Review screen and the helper API. | adding a screen or route |
| app.py | Build the Flask web application and its local-only protections. | changing sign-in, protections or reports |
| pages.py | Pages built from module declarations: the record grid, add and edit forms, and history. | changing the grid or forms |
| setup.py | The first-run wizard and the settings page: who lives here, the home, modules and backups. | changing setup questions or settings |
| count.py | Count this batch: a stocktake of one batch, reviewed and then saved as one stocktake correction. | changing the stocktake screens |
| home.py | Group the home page by area: each module's main lists shown large, its other lists as one line of links. | changing how the home page is grouped or ordered |
| sheets.py | One-page printable sheets declared by modules, such as the emergency sheet. | changing printable sheets |
| display.py | Turn declared tables and stored values into friendly labels, form fields and text. | changing how values look |
| templates/ | The HTML pages | changing what a page looks like |
| api.py | The helper API (/api/v1): programs the household gave a key to can look at records and suggest new ones. | changing what helpers can read or send |
| review.py | The Review screen: helpers' suggested new records and imported rows, waiting for a person to accept or reject each one. | changing the Review page |
| csv_import.py | Settings, Import from a spreadsheet: choose a table, upload a CSV, match its columns, check the rows, send to Review. | changing the import screens |
| helper_settings.py | Settings, Helpers: give an assistant a key, choose what it may do, and turn its access off. | changing the Helpers settings page |
| export_page.py | Settings, Export my records: a page and a button that downloads a zip of spreadsheet files. | changing the Export page |
| restore.py | Settings, Backups: the list of backups, a preview of one, putting it back, and Undo restore. | changing the restore pages |
| openapi-v1.json | The published OpenAPI 3.1 description of the helper API, served at GET /api/v1/openapi.json. | changing a helper route, reply or error code (edit it too) |
