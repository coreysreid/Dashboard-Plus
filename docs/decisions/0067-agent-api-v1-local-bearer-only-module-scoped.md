# 0067. The Agent API v1: local, bearer-only, module-scoped, and never private details

- **Status:** Proposed — awaiting Corey's OK
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey); needs Corey's plain-words OK because it changes a security rule
- **Refines:** DESIGN sections 9 and 12; decision 0055

## In plain words
Helpers talk to Dashboard through a small door at `/api/v1`, only from this computer. The door has its own lock: a
helper's key. This is the first place where a request is allowed in without the "launch link" cookie and page token that
every screen needs, because a helper is a program, not a person with a browser. **That is the change that needs Corey's
OK.** Everything else (every screen) is exactly as strict as before. Helpers can look at the parts the household chose and
suggest new records for a person to accept. They can never see private details, change or delete anything, or accept
their own suggestions.

## What we chose
- Only paths that start with exactly `/api/v1/` use the key. The Host check still applies first. Every other path keeps the
  cookie, the Origin check and the page token, unchanged. Pages never read the `Authorization` header.
- A request to `/api/v1/` must carry `Authorization: Bearer <key>`. A request that carries an `Origin` header (which every
  web page adds) is refused, so a web page can never use the API even if it learns a key. Cookies, the address line and
  form fields are never read for a key. Writes must be `application/json`; bodies over 64 KB are refused.
- A key is limited to the parts (modules) the household ticked, at the level chosen: look only, or look and suggest.
- Private (`sensitive`) columns are never returned and never accepted. There is no way to grant them in v1.
- Suggestions are new records only, at most 50 per call and 200 per helper per day, each call needs a `request_key` (a
  retry never adds twice) and a reason, and is all-or-nothing.
- There are no routes to decide, change, delete, read history, see other helpers, or touch settings, backups, files or keys.
- Replies are JSON in one error shape with plain sentences; they never repeat what was sent.

## Why we chose it
- A cookie belongs to a browser; a key belongs to a program. Letting the key in at one narrow door, and nowhere else,
  keeps the screens as safe as they were.
- Refusing any request with an `Origin` header closes the one way a malicious web page could ride a helper's key.
- Module scope is something a household can understand ("Pets, yes; Medical, no").
- No private details at all is the safest rule for v1; a grant can come later with its own decision.

## What else we considered
- Reusing the cookie for helpers: they have no browser, and it would put the session secret in more places.
- Per-table permissions: more precise, harder to explain, not needed for the skeleton.
- Letting helpers read private details when granted: deferred.

## What this costs us (the downsides)
- One more door to keep correct. Tests prove that a key opens no page and a cookie opens no API route.
- A key given to an online service lets that service see what the helper reads. The key page says so.
- The address changes each time Dashboard opens (the port is chosen fresh), so helpers need it again after a restart.
- A "Look" helper still sees names and values in the parts it was given (for example a People list), so only tick the
  parts you are happy to share.

## How hard it is to undo
Easy. Removing the `/api/v1/` branch in one place switches the API off; screens do not depend on it.

## We should revisit this if
- Helpers need to change or delete records, read private details, or run when Dashboard is not open.
