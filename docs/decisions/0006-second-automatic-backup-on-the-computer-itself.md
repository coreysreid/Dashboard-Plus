# 0006. Second automatic backup on the computer itself

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
A copy of backups is kept on the computer, not only on the USB stick.

## What we chose
Write the daily backup beside the data and also to a folder in the person's local application data (location shown and changeable in Settings).

## Why we chose it
- A USB stick can be lost, broken or corrupted; a second copy elsewhere is the real safety net.
- It costs a little disk space and no effort from the person.

## What else we considered
- Backup only next to the data: simpler, but loses the point of a second copy.

## What this costs us (the downsides)
- Uses extra disk space.
- Copies of personal data now exist in a second place, which the README must state plainly.

## How hard it is to undo
Low. It is a setting.

## We should revisit this if
- People are surprised by the second copy.
- Disk space is a problem.
