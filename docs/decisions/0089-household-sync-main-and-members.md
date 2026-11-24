# 0089. Household sync: one main, members push requests to Review, over a private network

- **Status:** Accepted as the direction (User 1, 20 November 2026). Nothing ships before an independent security review of the remote boundary (stage 0 below), because this changes the local-only rule of decision 0055.
- **Date:** 2026-11-20
- **Decided by:** User 1 (product choices below); Claude (technical shape, from Lane B's design in `workbench/drafts/sync/`)
- **Refines:** decision 0081 (household sharing options); builds on 0066, 0067, 0080, 0082, 0086

## In plain words
One copy is **main** (User 1's computer to start with). Another person's
computer is a **member**. The member **pulls** what main has accepted, works
offline, and **pushes** its changes back; they arrive on main's **Review**
screen as one request, and main accepts or rejects each row, like a merge
request. Copies reach each other from anywhere through a **private device
network** (Tailscale or WireGuard to start), never through an open port on the
home router. USB bundles come later as the offline way to do the same thing.

## What User 1 chose (20 November 2026)
1. **Two computers first.** Main is a computer that is on when the member
   syncs. User 1 also wants **macOS** alongside Windows, and **phone apps for
   Android and iOS** "in the near future pipeline", integrated with the rest:
   each phone joins as a member of this same sync (pull, push to Review), so
   nothing in the sync design may assume a desktop. Their designs follow
   version 1.
2. **Private details never travel in version 1.** User 1: Dashboard Plus is
   "meant to capture the mess, and display it cleanly; it's not a Fort Knox
   vault for your passwords, ID documents and gold bars." Private (`sensitive`)
   columns stay on the copy where they were typed; a member's copy shows them
   as "kept on main"; their absence never clears them. The app should keep
   saying plainly what it is for, and not invite people to store ID numbers or
   passwords. What a person keeps on their own USB stick is up to them.
   User 1 clarified (20 November): **medical notes are safety information, not
   private secrets.** Allergies, conditions, medications, blood type, care and
   diet needs stay hidden on screen until Show and print on the emergency
   sheet, and **do travel to members**. What never travels: access
   instructions (where a spare key is), Home layout codes and vehicle
   registration numbers. For papers, the app records where a document and its
   copies are kept ("Blue USB drive", "Family cloud folder"), never the document, a scan
   or its number. This needs a "travels to members" choice per private column
   (stage 1). User 1 confirmed (20 November): a pet's **microchip number travels
   to members** like other ordinary details; it is what a vet or pound asks for.
3. **The private network is pluggable.** Tailscale or self-run WireGuard to
   start, with room for a third provider later. Dashboard Plus never depends on
   one vendor: it listens only on the private-network address the household
   chooses, only while sharing is on.
4. **A home server as main comes later**, with its own setup and recovery steps.

## Defaults taken from Lane B's design (User 1 may change them)
- A member gets a full copy of the parts switched on (minus private details).
- Main approves **every** incoming row on Review; no automatic acceptance.
- Restoring a backup on main **pauses** sync until main deliberately catches
  members up; a restored snapshot never becomes a wave of deletes.
- A member away for a long time is warned about before it is retired; if it
  returns it starts from a fresh copy and keeps its unsent changes to push.

## What we chose (technical shape)
- **Member keys:** a separate key kind made in Settings (shown once, kept as a
  fingerprint, decision 0066), never a helper key; both sides prove who they
  are before any data moves (as in decision 0086, both ways); pinned identity
  at pairing.
- **Stable IDs and revisions:** every record gets an ID that is the same on
  every copy, a revision, and deletes are kept as markers, so changes can be
  matched across copies.
- **Pull:** first a full copy (with a backup first), then only what changed.
- **Push:** the member's changes since its last pull, staged on main's Review
  as one batch (reusing the staging used by helpers and imports, decision
  0080). Field edits clash side by side; Stock in and out entries are always
  kept; stocktake counts are rechecked against the batch as in decision 0070.
- **Badge (decision 0082):** "Syncing with … · last pulled …", "Sync paused ·
  changes saved here", "Syncing · 3 changes to review".
- **Same module versions required** on both copies before they sync, with plain words.

## Why we chose it
- It matches how User 1 wants to work ("like git": pull, work anywhere, push a
  request, main merges) and reuses Review, which households already know.
- A private device network gives "from anywhere" without exposing the app to
  the whole internet.
- Leaving private details out keeps a lost or shared second computer from
  holding the household's most sensitive facts.

## What else we considered
- Opening a port or a public tunnel: anyone on the internet could try to get in.
- Automatic merging (last writer wins): silently loses one person's work.
- Syncing a whole database file through a cloud folder: SQLite files break
  when two copies write them.

## What this costs us (the downsides)
- The largest change to the program so far: stable IDs touch every table.
- The household must install and run a private-network tool on each computer.
- Main must be on for the member to sync.
- Private details typed on a member copy stay on that copy only.

## How hard it is to undo
Medium before stage 2 ships (stable IDs are harmless on their own); high once
households depend on sync.

## Stages
0. Security review of the remote boundary and this decision.
1. Stable IDs, revisions and a change log (no network). **Built** (decision 0100,
   21 November 2026): permanent IDs, revisions, the filtered change log, the
   per-column travel rule and restore epochs, all on this computer only.
2. Member keys, pairing, and pull over the private network.
3. Push as a request on Review.
4. Conflicts side by side.
5. Encrypted USB bundles.
6. Home server as main.
Lane B's acceptance checks are in `workbench/drafts/sync/ACCEPTANCE.md`.

## We should revisit this if
- Households find the private-network setup too hard: then a guided setup or
  one more provider.
- People need phones as members.
