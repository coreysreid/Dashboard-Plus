# Make a new key for this helper

**Design only, checked 20 November 2026** against `src/dashboard/core/helpers.py`, `src/dashboard/core/migrations/0003_helpers.sql`, `src/dashboard/web/helper_settings.py`, the Helpers and one-time-key templates, and decisions 0066, 0068, 0086 and 0087. No rotation button or route is shipped. The goal is one press on an existing helper, one new key shown once, the old key stopped, and the helper's name, grant, suggestions and history kept.

## Household flow and exact words

On each **active** helper card in **Settings → Helpers**, next to **Turn off access**, show **Make a new key**. Under it:

> **“Use this if the key was lost or may have been seen. Your helper keeps the same name, access and Review history. Its old key stops when the new one is made. You will need to replace the key in your assistant app.”**

There is no second confirmation page. The local person presses **Make a new key** once. The button posts the page's CSRF token plus a **one-use form token bound to that helper ID**, like decision 0087. A duplicate POST, refresh/resend or double click cannot rotate again. The response shows the new key in **one** box only, never inside the copied MCP settings block:

> **“New key for Pantry helper”**
>
> **“Copy it now. This key will not be shown again. The old key no longer works.”**
>
> **“In your assistant app's MCP settings, replace only `DASHBOARD_PLUS_KEY` with this key, then restart or reconnect that assistant's Dashboard Plus tool. Keep the key out of chats and emails. Suggestions already waiting on Review are still there.”**

Buttons: **Copy key**, **Copy connection settings** (with `YOUR-KEY-HERE`, never the real key) and **Done**. On return to Helpers show **“Pantry helper's key was changed on 20 Nov 2026. Its access and history are unchanged.”** The card continues to show its original **Made** date, scope and level; add **Key changed** when present. The household can use the same flow if it missed the one-time display. No old key is recoverable.

For a reused form token say **“A new key was already made from this button. It cannot be shown again. Return to Helpers to make another new key if you did not copy it.”** For an out-of-date form say **“This page is out of date, so no key was changed. Open Helpers and try again.”** A helper already turned off has no rotation button; a stale submission says **“This helper's access is off. No key was made.”** Turning it on again would be a separate, explicit grant decision, not an accidental result of rotation. If storage fails, say **“The key could not be changed. This helper's access is paused so the old key cannot be used. Check the data folder, then make a new key from Helpers.”** Do not claim success or display a key on that path.

## What stays the same

Keep the same `core__helpers.id`, **`key_id`**, slug, name, grant (`access` and `modules`) and `created_at`. `core__helper_batches.helper_id` and `core__proposals` still name this helper; pending decisions and previous Accept/Reject results remain. The audit actor `agent:<slug>` remains legible. `UNIQUE(helper_id, request_key)` still makes an old retried suggestion idempotent, so a newly connected assistant should use fresh request keys for new intentions. `last_used_at` remains the last time the helper was used, regardless of which key; **Key changed** is a separate field. The new key is random in the same shape as current keys. The key itself is never stored, printed in logs, placed in a URL, added to a backup or sent to an online service by Dashboard.

The key file currently maps **fingerprint → key_id**. Replace the old fingerprint with the new fingerprint **in one atomic file replacement**, both mapped to the same stable `key_id`. A file snapshot must never contain both fingerprints. Keeping `key_id` stable means an older restored database that still has this helper row can recognize the new fingerprint; the old fingerprint stays absent because `data/secrets/helper_keys.json` is outside backups (0066). A backup from before the helper existed cannot recreate it. Revocation still removes all fingerprints for that helper and remains effective after restore.

## Safe order across database and key file

The database and secrets file cannot be committed in one transaction. Core needs a small **pending rotation** state on the helper, a `rotated_at` field, and a credential generation for in-flight writes. Under the same helper lock used by issue and turn-off:

1. Validate the active helper, local page token and one-use action token. Make the new key in memory. In one DB transaction set **rotation pending** and advance the credential generation. Authentication must refuse any key for a pending helper. A proposal already authorized with the old generation must recheck it under the write lock before staging, so it cannot arrive after rotation. A read already in progress may finish; the page should not promise to retract content already read.
2. Atomically rewrite `helper_keys.json`: remove **every** fingerprint mapped to this `key_id`, then add the new fingerprint mapped to that same ID. If writing fails, keep the helper pending and show no key. The old key is already blocked by the DB state. Never leave both keys live, retry silently, or write the plaintext key to a recovery file.
3. In a second DB transaction clear pending, set `rotated_at`, and add one value-free `helper_rotate` audit event. Only after this commits may the new key be shown once in the POST response. The key page and file must not disclose the old fingerprint or the new key twice.

On start-up, if a rotation is still pending after a crash, **fail closed**: remove any fingerprint for that helper from the secrets file, mark its card **“Key change did not finish. Make a new key to reconnect.”**, and offer a fresh one-step rotation from this credentialless state. Do not restore the old fingerprint. A crash after the final DB commit but before the response can leave a valid new key the person never saw; the household can make another new key and the unseen one stops. Repeated requests using the first form token never create a second key. Coordinate recovery with restore/Undo so a restored helper row cannot revive a removed fingerprint or clear an unfinished pause automatically.

## Checks for Lane A

1. Make a helper with Look and suggest for one module; stage a suggestion. Rotate its key once. Old key fails `/hello` and API; new key has the **same** module/level, same helper ID and slug, and sees the same pending batch. Review still accepts or rejects it as a person.
2. Send the rotation POST twice, refresh/resend the key page, and double click. Exactly one new fingerprint exists; the second response has no key and uses the already-made wording.
3. Show the new key in the one-time box only. Search HTML, URL, MCP JSON block, stdout, stderr, audit and backups for that key; it appears nowhere else. After leaving the page it cannot be retrieved.
4. Pause between pending DB state, file swap and final DB commit. During each pause neither old nor new key may stage a proposal. Crash at each point; restart cleans up without reviving the old key or presenting an unseen key as available.
5. Force a key-file write failure. The page shows no key and the helper is paused; the old key cannot be used. After the folder is writable, a fresh rotation works.
6. Start a suggestion with the old key, pause it after authentication, rotate, then let it reach the write lock. It must refuse without staging. A read completed before rotation is allowed to finish, with no new read accepted after the pending state starts.
7. Restore a backup from before rotation, then one from before helper creation. The old fingerprint remains removed in both cases; the new key can work only if the restored helper row exists and is not revoked. Restore/Undo never resurrects an off key.
8. Turn the helper off, then submit an old rotation form. It makes no key, keeps history and says access is off. Rotating another helper does not affect it.
9. Rotate while an assistant process still has the old key in its environment. Its next call fails; after replacing the key and reconnecting, it works. No key is automatically copied into that app's settings.
10. Use a request key from before rotation with the same and with different bodies. A retry returns the original batch; a different body remains refused. New intended suggestions use new request keys.
11. Verify the Settings card keeps its original Made date and scope, shows Key changed separately, and still lists old pending/accepted/rejected history under one helper name at 320px and desktop.

**Core gap:** Add the rotation route and one-use helper-bound token, the fail-closed pending state and recovery, key-file swap, in-flight write check, value-free audit, one-time page and tests. Until then, the household must turn off the old helper and make a separate new one; that splits its helper history, so the screen must not imply rotation already exists.
