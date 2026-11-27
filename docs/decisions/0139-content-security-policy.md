# 0139. A Content-Security-Policy, and no scripts inside pages

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** Claude (technical decision delegated by User 1; User 1 approved the Content-Security-Policy question left open in 0134)

## In plain words
Every page now tells the browser: "run only the program's own scripts, load nothing from anywhere else, never sit inside another site." If something hostile were ever slipped into a page, the browser would refuse to run it. You see no difference when using the program.

## What we chose
- Every response (pages, helper answers, errors, the scripts themselves) carries this header, set in one place in `web/app.py`:
  `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
- Every inline `<script>` (eleven, including the shared form code) and every inline handler (four Print buttons and the delete confirmation) moved into eight files in `src/dashboard/web/static/`, served at `/static/`. Pages load them with `<script src="/static/..." defer>`.
- A button that prints says `data-print`; a form that asks first says `data-confirm="..."`; a form that sends once says `data-once`. One listener in `common.js` handles all three. Values the old scripts took from the server (the list address on "Show more", the country lists on set-up) now sit in `data-` attributes.
- X-Content-Type-Options: nosniff, X-Frame-Options: DENY and Referrer-Policy were already sent. Referrer-Policy stays `same-origin`, not `no-referrer`: the comment in `web/app.py` records that current browsers then send "Origin: null" and every save is refused.
- `tools/browser_check.js` fails on any `securitypolicyviolation` event or "Refused to" message across the whole sweep, and checks the header on each page it opens. `tests/test_csp_0139.py` checks the header on HTML, JSON, helper, error and static answers, and scans every template for script bodies, `on...` handlers and `javascript:` links.
- The helper API, the connector and both portable builds are unaffected: the API and connector read JSON only, and both builds copy the whole `src/dashboard` folder (`copy_program`), so `static/` travels with it.

## Why we chose it
- It is a second wall: even a page bug that let text through unescaped could not run a script.
- Pages already worked without scripts for the main jobs; the scripts were conveniences, so moving them changed nothing a household uses.
- One header in one place means a new page cannot forget it.

## What else we considered
- **Nonces per request** (keep inline scripts, tag each with a random number). Works, but every new inline script would still be allowed to exist, and the pages would differ on every load. Static files are simpler to check.
- **Moving every style into a file too** (no `'unsafe-inline'` for styles). There are about 240 `style="..."` attributes and a dozen `<style>` blocks, some with values worked out per page (bar lengths, colours). Rewriting all of them would be a large, risky change for little gain: a style cannot run code, so the main risk of inline styles is page defacement or tracking pixels, and `img-src` and `default-src` already stop loading anything from another site. Left as inline styles; revisit below.
- **`Referrer-Policy: no-referrer`.** Breaks saving in current browsers (see above).

## What this costs us (the downsides)
- Inline styles stay allowed, so a style-only injection (changing how a page looks) is not blocked.
- Any future page must keep its code in `static/`; a quick inline script now silently does nothing in the browser. The test and the browser check catch it.
- Eight extra small requests to the program on the same computer; the browser keeps no copy (`no-store`), so they are fetched each time. Not noticeable locally.

## How hard it is to undo
Easy. Remove the header line in `web/app.py`; the scripts work the same from files.

## We should revisit this if
- The inline styles are rewritten into classes: then drop `'unsafe-inline'` from `style-src`.
- A page needs a picture or font from outside the program: it must be added to this list in a new decision, never by loosening `default-src`.
