# src/dashboard/web/  (summary: the screens: pages, forms and their protections)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Web layer: pages, forms, the Review screen and the helper API. | adding a screen or route |
| app.py | Build the Flask web application and its local-only protections. | changing sign-in, protections or reports |
| pages.py | Pages built from module declarations: the record grid, add and edit forms, and history. | changing the grid or forms, or what a private list or record shows before Show (0121) |
| setup.py | The first-run wizard and the settings page: who lives here, the home, modules and backups. | changing setup questions or settings |
| home_setup.py | Set up my home: rooms and areas, the storage spots inside them, and which rooms connect, on one page. | changing the Set up my home page |
| action_form.py | An action's small form, such as Mark done: open it, save it once as one operation, and Undo it (decision 0091). | changing Mark done or Undo screens |
| checklist.py | Things to do: the Today, This week, This month, This year and No date yet pages, each row with its record's own action. | changing the Things to do pages or the Home card |
| moves_pages.py | One reminder per policy (decision 0117): the household's choice screen, Review and move row by row, Transfer back, and the notices on each record's page. | changing the Vehicle insurance choice or move screens |
| count.py | Count this batch: a stocktake of one batch, reviewed and then saved as one stocktake correction. | changing the stocktake screens |
| home.py | Group the home page by area: each module's main lists shown large, its other lists as one line of links. | changing how the home page is grouped or ordered |
| questions.py | The "Have you thought about…?" screens: the questions by group, one question with its four answers, and Not now. | changing the question screens |
| drills.py | The "Think it through" screens: the drills that fit, one drill's sources and steps, each step with its records, and saving a practice. | changing the drill screens |
| exit_sketch.py | Our way-out sketch: the drawing with its text version, the few facts it asks for, and the printable sheet and text. | changing the way-out sketch pages or their forms |
| exit_drawing.py | Draw the way-out sketch as SVG on the server: room boxes by floor, labelled lines, doors out and the meeting place, split into pages. | changing how the sketch is laid out, drawn or split into pages |
| sheets.py | One-page printable sheets declared by modules, such as the emergency sheet. | changing printable sheets |
| display.py | Turn declared tables and stored values into friendly labels, form fields and text. | changing how values look |
| templates/ | The HTML pages | changing what a page looks like |
| api.py | The helper API (/api/v1): programs the household gave a key to can look at records and suggest new ones. | changing what helpers can read or send |
| review.py | The Review screen: helpers' suggested new records and imported rows, waiting for a person to accept or reject each one. | changing the Review page |
| receipt_line.py | Review, a receipt line the helper could not match: choose its Stock item or make a new one, then confirm amount and date. | changing Choose item for a receipt line |
| csv_import.py | Settings, Import from a spreadsheet: choose a table, upload a CSV, match its columns, check the rows, send to Review. | changing the import screens |
| bring_in.py | Bring in earlier entries: a list's own page to read a person's CSV, match it, preview every row, add them and Undo. | changing the Bring in earlier entries pages, their Show step or Undo (decision 0137) |
| helper_guide.py | The starting message for a helper's assistant: what it may use, how to send, and its limits, from list and field names only. | changing the starting message or GET /api/v1/guide |
| helper_settings.py | Settings, Helpers: give an assistant a key, choose what it may do, give it a new key, and turn its access off. | changing the Helpers settings page |
| export_page.py | Settings, Export my records: a page and a button that downloads a zip of spreadsheet files. | changing the Export page |
| chart*.py | Charts drawn on the server as SVG, labelled bars, dated dots and bars over time (charts, decision 0124), and the pages showing today's drinking water and one pet's recorded weights (chart_pages, decision 0109) | changing a chart or its empty words |
| daily_pages.py | Daily totals pages (decision 0110): one subject's day, a dated sheet, the Home lines, the record panel and Review's repeat note. | changing the feeding log pages, its sheet or its Home card |
| calendar_pages.py | Month calendars (decision 0119): a colour-coded grid with a symbol for every state, a legend and the same days in words. | changing a calendar page, its words, the Things to do Calendar tab (every list together, 0122), the record panel or a private calendar's Show (0121) |
| bar_pages.py | Bars over time (decision 0124): how often, or how much in one unit, per day, week or month, drawn on the server with the same values in a table and in words. | changing a bars chart page, its words, the record panel, a private table's Show, or a whole list's chart with private amounts (0128) |
| timeline_pages.py | One record's timeline (decision 0126): "What happened, newest first", by month, a symbol and words per kind, Earlier by server links, and private entries only as counts until a pressed Show. | changing the timeline's words, its record panel, paging or a private timeline's Show |
| private_daily.py | Private daily history (decision 0120), such as medicine doses: counts and times until Show, per-medicine totals after it. | changing the dose panel, Record a dose or Show details on Dose history |
| restore.py | Settings, Backups: the list of backups, a preview of one, putting it back, and Undo restore. | changing the restore pages |
| openapi-v1.json | The published OpenAPI 3.1 description of the helper API, served at GET /api/v1/openapi.json. | changing a helper route, reply or error code (edit it too) |
