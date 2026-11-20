# 0092. A steady helper address: an address file the connector reads for every call

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by Corey), from Lane B's design `workbench/drafts/agent_api/STEADY_ADDRESS.md`

## In plain words
Dashboard Plus still picks a new address each time it opens, but it now writes
that address into a small file in its own folder. The AI-assistant settings on
Settings, Helpers point at that file, so you paste them once and an ordinary
restart needs no new copy. The connector still checks it is really talking to
your Dashboard Plus before it sends the key (decision 0086), so a wrong or old
file cannot catch the key.

## What we chose
- **A new file, `data/run/helper-address.json`,** written after the listener is
  ready: `{"version": 1, "url": "http://127.0.0.1:<port>/api/v1", "run_id":
  "<32 hex>"}`. It is written under a temporary name and then put in place in
  one step, readable by this computer account only (0600 where the system
  allows it). The run ID is random and not a secret.
- **Never a secret in it.** No key, cookie, browser session or close token.
  Those stay in `data/run/dashboard.json`, which the connector never reads.
- **A safe close removes it only if the run ID is still its own,** so a second
  copy of Dashboard cannot remove the first one's file with an old run ID. A
  crash can leave a stale file; the next start replaces it.
- **A new connector setting, `DASHBOARD_PLUS_ADDRESS_FILE`,** holding the full
  path of that file (or `address_file` in a `--config` file). Lane B's design
  names the file, not the data folder, so the connector never has to guess a
  name inside a folder. When it is set, any `DASHBOARD_PLUS_URL` is ignored so
  a stale address cannot win. The key still comes only from
  `DASHBOARD_PLUS_KEY`, and stays in the assistant app's settings.
- **The connector reads the file again for every tool call** (an assistant app
  may keep one connector running through several Dashboard restarts). It
  remembers no address and no passed check. The file must be at most 1 KB, a
  regular file and not a symbolic link, named `helper-address.json`, with
  exactly those three values and the URL in exactly that spelling (`127.0.0.1`,
  a number from 1 to 65535 without leading zeros, `/api/v1`, nothing else).
  Then the 0086 hello runs on that address, and only on a match does the key
  go, down the same connection.
- **Exact words from Lane B's design**, each ending "The key was not sent.":
  a missing file ("I cannot find Dashboard Plus's current address file..."),
  a wrong file ("Dashboard Plus's address file does not look right...", never
  quoting it), nothing answering ("Dashboard Plus is not answering at the
  address in its connection file..."). A program that answers but cannot prove
  it is Dashboard still gets decision 0086's stronger refusal.
- **Settings, Helpers** shows Lane B's new paragraph and a settings block with
  `DASHBOARD_PLUS_ADDRESS_FILE`. A collapsed **Connection details** shows the
  current address and a "Use current address instead" block with
  `DASHBOARD_PLUS_URL` for apps that cannot use the file, with the reminder
  that it must be copied again after each restart. "Connected from this
  computer" appears on a helper's card only when its key was used in the last
  ten minutes. If the file could not be written at start, the page says so.
- **The explicit `DASHBOARD_PLUS_URL` still works** exactly as before.

## Why we chose it
- Pasting the settings after every restart was the most likely reason a
  household would give up on an assistant.
- Dashboard can keep using any free port, so there is no port to collide with
  another program or a second Dashboard.
- The file is a locator, not proof. The 0086 hello is what protects the key,
  so a planted or stale file can at worst stop the connection.
- Keeping it inside the data folder keeps two installations on one computer
  apart.

## What else we considered
- **A fixed port per data folder:** one URL to paste, but another program or a
  second Dashboard may take the port, which needs conflict handling and new
  words for a problem the household cannot fix easily.
- **Reading `dashboard.json`:** it already has the port, but it also holds the
  browser session and the close token, which a connector must never see.
- **A `DASHBOARD_PLUS_DATA` folder setting:** close to this, but the connector
  would then build a path inside a folder it was told about; naming the exact
  file is simpler to check and matches Lane B's design.
- **Keeping only the copied URL:** simple, but easy to forget after every
  restart. It stays as the manual choice.

## What this costs us (the downsides)
- A crash leaves a stale file until the next start. The connector reads it,
  the hello fails, and the key is not sent, but the assistant cannot connect
  until Dashboard opens again.
- A program that can change files in the data folder can make the connection
  fail, or point a check at its own listener. It still cannot get the key
  without the fingerprints (0086), which are a stronger foothold already.
- The settings hold a full path. Moving the Dashboard Plus folder or the USB
  drive (or a new drive letter) breaks it plainly, and the settings must be
  copied again. There is no automatic relocation.
- One more file to write at start and remove at close, and one more read per
  tool call (about 110 bytes).
- On a filesystem without per-user permissions (some USB drives) the file can
  be edited by anyone who can use the drive.

## How hard it is to undo
Easy: stop writing the file in `server.py`, drop `DASHBOARD_PLUS_ADDRESS_FILE`
from `connector/config.py` and the block on Settings, Helpers. Connectors set
up with the file would then say the file is missing and need the URL form.

## We should revisit this if
- People report "cannot find the address file" after moving the folder more
  than rarely (consider a relative path or a per-user pointer).
- An assistant app turns out unable to pass environment values to a connector.
