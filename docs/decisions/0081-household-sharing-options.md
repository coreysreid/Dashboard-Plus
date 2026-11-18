# 0081. Sharing the records with your household: three options, Corey to choose

- **Status:** Proposed — Corey to choose an option
- **Date:** 2026-11-18
- **Decided by:** Corey (needs his OK: any option changes the privacy and security rules); designed by Claude
- **Would refine:** decisions 0011, 0055 and 0067, and DESIGN section 12; the full design is in
  [docs/plans/household-sharing.md](../plans/household-sharing.md)

## In plain words
Corey asked how a partner could see the same records, as an option, with the
program always showing whether it is "on this computer only" or sharing. There
are three ways to do it. **A:** keep the records in a folder OneDrive, Dropbox
or Syncthing copies between your computers, and take turns: one computer has
them open at a time. **B:** one computer at home is the "home base", and
others (including phones) open it in a browser over home Wi-Fi with their own
password. **C:** every computer keeps its own copy and they swap changes, with
clashes shown on Review. Nothing is built yet. The suggestion is A first (or B
first if the partner mainly uses a phone), and C only later if needed.

## What we chose
Nothing yet. Proposed, for Corey to choose:
- **Stage 1: option A**, through a shared folder, Syncthing recommended. The
  records are never opened inside the shared folder: each computer checks out a
  checked copy, works on it locally, and checks it back in as a finished file.
  A lease file names who has them open; a generation number stops one computer
  overwriting another's newer copy (its copy is set aside instead); half-arrived
  files and cloud "conflicted copies" are detected and never opened for writing.
- **Instead B first** if the partner mainly uses a phone: listening on the home
  network only while switched on, accounts with scrypt-hashed passwords,
  paired devices, HTTPS with a self-signed certificate, strict Host and Origin
  rules, rate limits, and automatic switch-off.
- **Later, only if taking turns is a nuisance: option C1**, sync through the
  same folder, each device writing only its own change files.
- **In every case:** the default is "On this computer only"; a label at the top
  of every page says the mode in plain words ("Sharing on home Wi-Fi with 2
  devices", "Syncing with Sam's laptop, last synced 2 minutes ago", "Sharing
  paused"), with colours that pass WCAG contrast; and switching off returns to
  isolation without losing anything.

## Why we chose it
- A keeps the rule that the program listens on this computer only (0011) and
  needs no new dependency, while respecting SQLite's warning that two computers
  must never write one database file over a shared or synced folder.
- B is the only option that reaches a phone, but it opens a door on the home
  network and needs HTTPS, accounts and probably a new dependency.
- C is the most convenient and by far the largest change: world-wide ids for
  every record, merge rules, worked-out stock counts, and a lasting cost on
  every future database change.

## What else we considered
- Putting `dashboard.db` itself in OneDrive or a network share and opening it
  from two computers: refused; it can corrupt the file.
- Plain HTTP on home Wi-Fi for option B: refused; anyone on the network could
  read pages and take over a session.
- A company-run sync server: against the local-first promise.
- Remote access from outside the home (a VPN or tunnel): out of scope here.

## What this costs us (the downsides)
- **Any option changes the privacy and security rules:** A sends the whole
  records file, private details included, to a shared folder (and, with
  OneDrive or Dropbox, to a company that can read it, since the copy is not
  encrypted); B reverses 0011's "this computer only" for the home network and
  adds a second way in besides 0067's helper door; C does one or both. The
  footer promise "Nothing is sent anywhere" stops being true while sharing is
  on, so it must change.
- A: one at a time; a stale or clashing session leaves a set-aside copy to look
  through by hand. B: nobody else can use the records while the home base is
  off; first-visit certificate warnings. C: very large, with clash reviews.
- A new security review before any option ships.

## How hard it is to undo
Easy while it is only a design. Once built: A and B are Medium (remove the
Sharing page and its core piece; each computer's local records stay as they
are); C is High (world-wide ids and the change log reach every table).

## We should revisit this if
- Corey answers the questions in the plan (who, which devices, phone or not),
  or a household asks for sharing outside the home.
