# src/dashboard/web/  (summary: the screens: pages, forms and their protections)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Web layer: pages, forms and the Agent API (not built yet). | adding a screen or route |
| app.py | Build the Flask web application and its local-only protections. | changing sign-in, protections or reports |
| pages.py | Pages built from module declarations: the record grid, add and edit forms, and history. | changing the grid or forms |
| setup.py | The first-run wizard and the settings page: who lives here, the home, modules and backups. | changing setup questions or settings |
| count.py | Count this batch: a stocktake of one batch, reviewed and then saved as one stocktake correction. | changing the stocktake screens |
| home.py | Group the home page by area: each module's main lists shown large, its other lists as one line of links. | changing how the home page is grouped or ordered |
| sheets.py | One-page printable sheets declared by modules, such as the emergency sheet. | changing printable sheets |
| display.py | Turn declared tables and stored values into friendly labels, form fields and text. | changing how values look |
| templates/ | The HTML pages | changing what a page looks like |
