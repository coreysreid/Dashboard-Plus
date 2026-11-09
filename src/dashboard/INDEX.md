# src/dashboard/  (summary: the program package)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Dashboard Plus: a local-first home dashboard (package root). | checking the version |
| __main__.py | Command-line entry point: open the dashboard, or close a running one safely. | changing how it starts |
| server.py | Start and stop the local web server, and remember how to reach it. | changing startup, closing or ports |
| core/ | Core services: records, links, review, audit, backups | changing anything topic-neutral |
| web/ | Web layer: pages, forms, Agent API | changing screens or the API |
