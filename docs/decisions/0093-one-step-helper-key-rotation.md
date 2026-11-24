# 0093. One-step "Make a new key" for a helper

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by User 1), from Lane B's design `workbench/drafts/agent_api/ROTATE_KEY.md`

## In plain words
If a helper's key was lost or may have been seen, press **Make a new key** on
that helper in Settings, Helpers. You get one new key, shown once; the old key
stops at once. The helper keeps its name, what it may do, its suggestions
waiting on Review and its history, so you no longer have to turn it off and
make a separate new helper.

## What we chose
- **One button per working helper**, next to Turn off access, with Lane B's
  words under it. No second confirmation page. The form carries the page's
  CSRF token and a **one-use `new_key_token` bound to that helper** (kept in
  memory, latest 200), like decision 0087. A resend, refresh or double click
  makes nothing and says "A new key was already made from this button...";
  an unknown token, or one for another helper, says "This page is out of
  date, so no key was changed...". A helper whose access is off has no button,
  and an old form for it says "This helper's access is off. No key was made."
- **The new key is shown once,** in one box with **Copy key**, on a page that
  also has **Copy connection settings** (with `YOUR-KEY-HERE`, never the real
  key) and **Done**. Done returns to Helpers with "<name>'s key was changed on
  <date>. Its access and history are unchanged." The card keeps its Made date
  and adds "Key changed <date>".
- **What stays:** the helper's row id, `key_id`, slug (so the history's
  `agent:<slug>` stays readable), name, grant, Made date, batches and
  suggestions, and request keys (a retry with an old request key returns its
  first batch). `last_used_at` stays the last use by either key.
- **Three new columns** on `core__helpers` (migration `0005`): `rotated_at`,
  `key_pending_at` and `key_generation`.
- **A safe order,** under the same lock as making and turning off keys:
  1. one transaction sets `key_pending_at` and raises `key_generation`. From
     here no key of the helper works: `verify` refuses a pending helper;
  2. `data/secrets/helper_keys.json` is replaced whole: every fingerprint of
     that `key_id` out, the new one in, so the file never holds both;
  3. a second transaction clears the mark, sets `rotated_at` and adds one
     `helper_rotate` audit row with no values.
  Only after step 3 is the key put in the page.
- **If a step fails** the helper stays paused, no key is shown, and the page
  says "The key could not be changed. This helper's access is paused so the
  old key cannot be used. Check the data folder, then make a new key from
  Helpers." At start-up, any helper still marked has every fingerprint
  removed, and its card says "Key change did not finish. Make a new key to
  reconnect." The old key is never put back.
- **In-flight writes are checked again.** Inside the write transaction,
  `proposals.submit` reads the helper's revoked, pending and generation state
  again; a request checked with the old key (or a key turned off meanwhile) is
  refused with 401 `no_key` and nothing is stored. A read already under way may
  finish.
- **Restore and Undo:** keys are not in backups (0066). Restoring a copy from
  before the change keeps the same `key_id`, so the new key works and the old
  fingerprint stays gone; a copy from before the helper existed has no row for
  the new key. Restore's existing step still turns off any helper with no
  fingerprint.

## Why we chose it
- Turning off and making a new helper split its history and its waiting
  suggestions across two names, which is confusing on Review.
- The pause before the file swap means no moment exists when the old key
  still works after the person asked for it to stop, even if something fails.
- Keeping `key_id` lets a restored database recognise the new key without the
  old one ever coming back.

## What else we considered
- **A confirmation page first:** one more step for something easy to redo; a
  second new key simply replaces the first.
- **Keep the old key working for a while:** gentler for a running assistant,
  but a key that may have been seen should stop now.
- **Write the file first, then the database (like Turn off):** a failure
  between the two could leave the new key working with no record, or the old
  one working after the person was told it stopped.

## What this costs us (the downsides)
- An assistant still using the old key fails at its next call until its
  settings get the new key; nothing copies the key into the assistant's app.
- A crash after the last step but before the page is shown leaves a working
  key the person never saw. They must make another new key.
- A failure leaves the helper paused with no key until the person presses
  Make a new key again.
- Open buttons live in memory: after a restart an old page says "out of date".
- One more migration and three columns on `core__helpers`.

## How hard it is to undo
Medium: remove the route, button and `rotate`; the three columns can stay
unused (SQLite keeps them harmlessly), or a new migration can drop them.

## We should revisit this if
- People report pausing after storage failures, or ask to keep an old key
  working during a change-over.
