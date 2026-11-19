# 0086. The connector checks it is really Dashboard before sending the key

- **Status:** Accepted
- **Date:** 2026-11-19
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Dashboard Plus picks a new address each time it opens. If it is closed, another
program on this computer could take the old address and wait for the key. Now
the AI-assistant connector first asks the program at that address to prove it
is the Dashboard Plus that made the key, without sending the key. Only the real
Dashboard can answer correctly. If the answer is wrong or missing, the key is
not sent and the assistant is told to copy the address again from Settings,
Helpers.

## What we chose
- **A new route that needs no key: `POST /api/v1/hello`.** Before every
  request, the connector opens a connection and sends two values: a fresh
  random nonce (32 bytes) and the key's public name.
- **The key's public name** is `SHA-256("dph-id:" + fingerprint)`, where the
  fingerprint is the SHA-256 of the key that Dashboard already keeps in
  `data/secrets/helper_keys.json` (decision 0066). A key (`dph_` plus 32
  random bytes) carries no identifier of its own, and Dashboard does not keep
  the key, so the name has to come from the fingerprint: both sides can work
  it out, and nobody can work back from it to the fingerprint or the key. The
  fingerprint itself is never sent.
- **Dashboard's answer** is `HMAC-SHA256(secret, "dashboard-plus-hello-v1|" +
  nonce + "|" + host:port)`, where the secret is `SHA-256("dph-hello:" +
  fingerprint)` and host:port is the exact Host the request was sent to (which
  must already be `127.0.0.1:<port>` or `localhost:<port>`). Only the key's
  holder and the Dashboard that made the key can work out the secret.
- **The connector compares** its own result with `hmac.compare_digest`. On a
  match it sends the real request, with the key, **down the same connection**,
  and it will not open another one for it (`auto_open = 0`). If Dashboard
  closed that connection, the connector checks again on a new one (once more
  at most) instead of sending the key unchecked.
- **On a wrong or missing answer** the tool fails with: "This address is not
  Dashboard Plus, or it is an old address. Open Dashboard Plus and copy the
  address again from Settings → Helpers. If the address is right, this
  helper's key may have been turned off: make a new one there. The key was not
  sent." The other program's own words are never passed to the assistant.
- **The answer tells a stranger nothing.** A name that is not a working key
  (unknown, or turned off) gets an answer of exactly the same shape and size,
  signed with a secret made fresh each time Dashboard starts. Every kept
  fingerprint is compared, so timing says nothing either.
- **The usual door rules still apply:** an `Origin` header is refused
  (`from_a_web_page`), the Host must be exact (`forbidden`), JSON only, body at
  most 1 KB, no cookies, `Cache-Control: no-store`. Because the hello has no
  helper to count against, it has its **own limit of 600 a minute, shared by
  everyone** (`app.config["HELLOS_PER_MINUTE"]`, 429 `too_many_requests` with
  `Retry-After`); it never uses up a helper's 120 a minute.
- **A check before every request, not once per connector run.** A remembered
  "yes" would outlive Dashboard: if Dashboard closed and another program took
  the port while the assistant's app kept the connector running, the next
  request would carry the key there. A check costs one extra request on this
  computer, a few milliseconds.
- The connector now uses Python's `http.client` instead of `urllib`: it never
  uses a proxy and never follows a redirect, and it lets one connection carry
  both the check and the request. The shared formulas live in
  `src/dashboard/core/hello.py`, used by both sides.

## Why we chose it
- It closes the gap left open by decision 0083 without anything for the
  household to do: no new setting, no new file, nothing to copy.
- It needs nothing new stored: the fingerprint Dashboard already keeps is
  enough. No new library either.
- Sending the request down the checked connection leaves no moment between
  the check and the key when another program could step in.
- Putting host:port into the signed text stops an old-port program from simply
  asking the real Dashboard (at its new address) and repeating the answer.

## What else we considered
- **Check once per connector run and remember it** (suggested first): fewer
  requests, but the remembered answer is exactly what the attack needs once
  Dashboard closes.
- **Send nothing identifying and have Dashboard answer for every key it
  knows:** no public name, but the answer's size would tell anyone how many
  helpers exist, and the work grows with every helper.
- **Use the fingerprint as the public name:** simpler, but the fingerprint is
  what the proof is built from, so sending it would let anyone forge the proof.
- **A fixed port, or a connection file Dashboard writes:** helps people with
  the changing address, but a file can go stale, and a fixed port can still be
  taken while Dashboard is closed. Still possible later; this check would stay.
- **HTTPS with a certificate:** strong, but heavy for a program that only ever
  talks to this computer, and a household cannot be asked to manage one.

## What this costs us (the downsides)
- **Anyone who can read `data/secrets/helper_keys.json` can pretend to be
  Dashboard** to the connector, because the proof is made from the
  fingerprints. They still would not learn any key from it, and such a program
  can already read the household's database in the same folder.
- **Every tool call is now two requests.** It is on this computer and takes a
  few milliseconds, but each one counts against the shared 600-a-minute limit.
- **A turned-off key now gets "not Dashboard Plus, or an old address"** (with
  a line saying the key may have been turned off) instead of Dashboard's own
  "no longer works" message, because Dashboard can no longer prove it made a
  key it has forgotten. The 401 still appears if a key is turned off between
  the check and the request.
- **A new connector needs a Dashboard that knows the hello.** Both ship
  together, so this only matters if someone mixes versions.
- **The key's public name is the same every time.** A program on the old port
  learns it, and could later ask the real Dashboard about it; it only ever gets
  an answer of the same shape whether the key works or not.
- More code to keep right on both sides; the formulas are pinned by tests in
  `tests/test_helper_keys.py`, `tests/test_helper_api.py`,
  `tests/test_api_contract.py` and `tests/test_mcp_connector.py`.

## How hard it is to undo
Easy: remove the `/hello` route and `_hello_gate` from `web/api.py`, its entry
in `openapi-v1.json`, `core/hello.py`, and `_check` from `connector/client.py`
(going back to sending the request directly). No stored data changes.

## We should revisit this if
- Tool calls feel slow, or the shared limit is reached in normal use.
- People are confused by the "not Dashboard Plus" message after turning a key
  off; then consider a separate, still uninformative, hint.
- A fixed port or connection file is added (plan section 8): keep this check,
  and decide whether the file should carry anything more.
