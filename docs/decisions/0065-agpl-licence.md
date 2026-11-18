# 0065. The licence is the GNU AGPL, version 3 or later

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Corey Reid
- **Replaces:** decision 0014 (MIT)

## In plain words
Dashboard Plus is now licensed under the GNU Affero General Public License,
version 3 or (at your choice) any later version. Households can use it freely
at home with nothing extra to do. Anyone who shares a changed copy, or runs a
changed copy for other people over a network, must share their changes under
the same licence, so nobody can turn it into a closed product. A donation link
will be added once Corey has one.

## What we chose
- `LICENSE` holds the official AGPL v3 text (from the SPDX licence list, which
  reproduces the Free Software Foundation's text). The README carries the
  copyright line, "Copyright (C) 2026 Corey Reid", and the plain-words summary.
- "Or later": if the Free Software Foundation publishes a version 4, people may
  choose it; this avoids needing every contributor's agreement to move.
- Contributions, and modules (including files-only modules), are shared under
  the same licence (CONTRIBUTING.md).
- The bundled libraries (Flask, Werkzeug, Jinja, MarkupSafe, ItsDangerous,
  Click, Blinker, Colorama, Waitress) use permissive licences that can be
  included in an AGPL program.

## Why we chose it
- Corey wants the project to stay free: improvements made by others come back
  to everyone rather than into a closed product.
- Every commit so far is by Corey or by agents working for him, so the change
  needs no one else's permission.

## What else we considered
- Keeping MIT: anyone could make a closed, paid version without sharing back.
- GPL v3: similar, but doesn't cover changed copies run as an online service.
- AGPL v3 only: a later move to version 4 would need every contributor's say.

## What this costs us (the downsides)
- Some companies avoid AGPL software, so fewer businesses may build on it.
- Copies of the project taken before today remain available under MIT.

## How hard it is to undo
Moving to a more permissive licence later would need every contributor's
agreement once others contribute; today only Corey's.

## We should revisit this if
- Corey wants to offer a separate commercial licence, or a donation or
  sponsorship arrangement needs specific wording.
