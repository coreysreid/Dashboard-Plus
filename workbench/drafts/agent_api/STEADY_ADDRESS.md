# A helper connection that survives an ordinary restart

**Design only, checked 20 November 2026** against `src/dashboard/server.py`, `src/dashboard/connector/{config,client,mcp_server}.py`, `src/dashboard/web/{helper_settings.py,templates/helper_connect.html}`, the portable launcher in `tools/build_portable.py` and decisions 0066, 0083 and 0086. No address discovery change is shipped. The aim is that a household pastes its assistant settings **once per installation** and does not edit them every time Dashboard opens.

## Choice

Give the connector a **steady file location**, while Dashboard continues to choose a free loopback port on each start. After its listener is ready, Dashboard writes a separate `data/run/helper-address.json` with only a version, current `http://127.0.0.1:<port>/api/v1` address and random nonsecret run ID. It writes a temporary file then replaces the old one as one operation. It removes the file on safe close only if the run ID still matches; a crash may leave a stale file. The connector reads and validates this file **before every tool call**, because the assistant may keep the same MCP process open through several Dashboard restarts. It then performs the existing decision 0086 `/hello` identity proof on that same connection before sending the key. It never trusts the file as proof of identity.

Use a new locator file. **Do not read `data/run/dashboard.json` in the connector:** that existing file also contains the browser launch session and shutdown token. The locator contains **no key, cookie, token, person name or record data**. Keep it inside the selected data folder so two Dashboard installations on one computer do not mix. The Settings block would pass its exact file path as `DASHBOARD_PLUS_ADDRESS_FILE`; it would still put `YOUR-KEY-HERE` only in `DASHBOARD_PLUS_KEY`. The key stays in the assistant app's settings, not the locator. A client that stays running re-reads the locator for each call; it must not cache a successful identity proof or a port.

The current connector loads `DASHBOARD_PLUS_URL` and its key once at process start. Core must change the transport so `DASHBOARD_PLUS_ADDRESS_FILE` is resolved on each call, while the key remains the one given to that process. When a file path is supplied, do not let a stale `DASHBOARD_PLUS_URL` environment value override it. The generated path is inside the selected data folder. Bound the file's size and validate its schema, canonical loopback host, numeric port and exact API path using the same URL rules as today. A replaced file or symlink must not bypass the `/hello` proof; a platform-specific symlink refusal is optional defense, not the key boundary. This is a local locator, not a way to connect to another computer.

## Options and risks

| Approach | Household effect | Risk and decision |
|---|---|---|
| **Chosen port** saved per data folder | The assistant can keep one URL after restarts. | A different program or another Dashboard may take the port. The app must never bind a public interface or silently switch to a new port while promising the old URL. If the port is busy, show a clear problem or use a discoverable fallback. `/hello` still protects the key, but the helper cannot connect until the collision is resolved. More port choice and conflict UI for little benefit. Not recommended first. |
| **Separate current-address file (recommended)** | Copy the MCP settings once; Dashboard can still use any free port. | A crash may leave a stale address; a bad local process could edit the file; a USB drive letter or folder move can invalidate the saved absolute path. Validate it and keep `/hello` before the key. Show a specific missing/stale-file hint, and re-copy settings after moving the portable folder. |
| **Explicit URL, as today** | The person copies the new address into assistant settings after each start. | Simple and already shipped, but easy to forget. Retain it as a **manual compatibility path** for clients unable to pass a file setting. Never silently fall back to an old URL when a configured locator is missing or invalid. The person can choose “Use current address instead” and copy it, with `/hello` still required. |

The file is not a secret store. File permissions should still limit casual edits where the filesystem supports them; the portable USB may use a filesystem without useful per-user permissions. A program that can alter this file could cause a connection failure or redirect a check to its own listener, but cannot get the key without proving it is the Dashboard that made the key (0086). A program that can read Dashboard's key-fingerprint file has a stronger local foothold already; the locator does not change that boundary. No port scan, network discovery, proxy, redirect or public address is allowed.

## Exact Settings words

On **Settings → Helpers** and the one-time key page, replace the sentence that says the address changes and must be updated every time with:

> **Connect an AI assistant.** Copy these settings into your assistant desktop app's MCP server settings. Replace `YOUR-KEY-HERE` in `DASHBOARD_PLUS_KEY` with the key shown above; do not put the key in a chat. The settings point to a small address file in this Dashboard Plus folder. Dashboard updates that file when it opens, so an ordinary restart needs no new copy. Keep Dashboard Plus open while the assistant uses it. If you move the Dashboard Plus folder or USB drive, copy these settings again. The key stays in your assistant app's settings file; treat it like a password.

On the Helpers page, where the key is no longer visible, use **“with the key you copied when you made this helper”** instead of **“with the key shown above.”** Keep the existing online-assistant warning and Review explanation. Put **“Current local address: …”** under a collapsed **Connection details** section for troubleshooting; it is not the thing to paste in the preferred flow. After a healthy connection show **“Connected from this computer”** only if core has a recent successful key use; a valid locator alone must not be called connected.

For failures, use these exact words:

| Case | Assistant tool error / nearby Settings help |
|---|---|
| Locator missing or unreadable | **“I cannot find Dashboard Plus's current address file. Open Dashboard Plus on this computer. If you moved its folder or USB drive, copy the connection settings again from Settings → Helpers. The key was not sent.”** |
| Locator malformed, external or too large | **“Dashboard Plus's address file does not look right. Open Dashboard Plus and copy the connection settings again from Settings → Helpers. The key was not sent.”** Do not quote file contents or try an old URL. |
| File points at a closed or replaced listener | **“Dashboard Plus is not answering at the address in its connection file. Open it again and try once more. The key was not sent.”** If `/hello` fails, keep decision 0086's stronger **“This address is not Dashboard Plus…”** refusal. |
| Key turned off | Keep decision 0086's wording that the key may have been turned off and a new one may be needed; do not claim the locator itself is wrong. |
| Manual URL mode | **“This assistant uses the copied address. Dashboard Plus chooses a new one each time it opens; copy the current address again from Settings → Helpers.”** |

## Acceptance checks for Lane A

1. Start Dashboard twice from the same data folder; the port may change, but one unchanged MCP settings block makes `dashboard_me` work both times. Keep the MCP process alive across the restart to prove it re-reads the file for each call.
2. Run two temporary Dashboards with distinct data folders and helper keys. Each locator resolves its own app; crossing their files fails `/hello` and sends no key.
3. Crash Dashboard without cleanup, then put a fake program on the old port. The connector reads the stale file, fails `/hello` and sends no key. No scan or automatic old-URL fallback occurs.
4. Replace the locator with malformed JSON, a very large file, a non-loopback URL, a query string, another API path and a symlink to an attacker-controlled address file. Each yields a bounded plain error or fails `/hello`, without sending the key or quoting file contents.
5. Change the locator between two calls, and between lookup and connection. The connector checks the intended host/port on the **same connection** before every authenticated request; a change never puts the key on an unchecked connection.
6. Turn off a helper key, restore an old backup and retry. The locator still finds Dashboard, but the revoked key never regains access (0066, 0086).
7. Close safely: the file is removed only for that run. Reopen: a fresh file replaces a stale one atomically. A second instance cannot delete the first's file by using an old run ID.
8. Move the portable folder to a different drive letter and start it. The old assistant command/path fails plainly; a fresh Settings block works. Do not promise automatic relocation.
9. Use a custom `--data` folder, a path with spaces and a read-only or unavailable run folder. The shown path matches that installation; failure does not leave an outdated success message or send a key.
10. Select manual URL mode with a client that cannot pass the locator. Current behavior and `/hello` remain, including the reminder to update the copied URL after restart.

**Core gap:** This needs a new file lifecycle in `server.py`, per-call address resolution in the connector, Settings block changes and tests. Until Lane A ships it, the household must keep updating the address after each restart as the current page says. No changes to shipped code are proposed in this workbench item.
