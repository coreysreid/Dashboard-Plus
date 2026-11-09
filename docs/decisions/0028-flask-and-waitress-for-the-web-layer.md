# 0028. Flask and Waitress for the web layer

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The screens are built with Flask, the most widely used small Python web
toolkit, and served by Waitress, a simple, well-tested server that works the
same on Windows as everywhere else.

## What we chose
Flask 3.1.1 (with its own small libraries: Werkzeug, Jinja2, MarkupSafe,
itsdangerous, click, blinker, and colorama on Windows) and Waitress 3.0.2, all
pinned exactly in `requirements.txt` and locked with checksums in
`requirements.lock`. This follows decision 0002 (server-built pages).

## Why we chose it
- Flask is mature, documented everywhere, and easy for a newcomer to read, which
  matters for a project meant to outlive its maintainer.
- Flask's page templates escape text automatically, which prevents a common
  class of security mistakes.
- Waitress is pure Python, needs no compiler, and runs well on Windows; Flask's
  own server is only meant for development.
- Every library except MarkupSafe is pure Python, and MarkupSafe ships ready-made
  Windows files, so the portable folder needs no build tools.

## What else we considered
- Bottle: a single file with no dependencies, but less actively maintained and
  less familiar to new contributors.
- Starlette or FastAPI with Uvicorn: modern and fast, but asynchronous code is
  harder for newcomers and the dependency tree is larger.
- Django: complete, but far larger than a local household app needs.

## What this costs us (the downsides)
- Nine pinned libraries instead of none, all of which need occasional security
  updates (`tools/lock_requirements.py` makes this a one-line change plus a
  re-lock).
- Flask brings click, a command-line library we do not use directly.

## How hard it is to undo
Medium. Pages and routes are in `src/dashboard/web/`; the database, modules and
rules do not depend on Flask.

## We should revisit this if
- A pinned library stops receiving security fixes.
- Pages need live updating that server-built pages handle poorly.
