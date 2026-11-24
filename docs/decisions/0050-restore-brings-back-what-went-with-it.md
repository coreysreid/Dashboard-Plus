# 0050. Restoring brings back what went with it; backups and counts made safer

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by User 1), from an independent review

## In plain words
An independent review (a second AI model, reading the code and trying to break
it with made-up households) found ways records could quietly go missing or be
counted wrong. These are fixed:
- Restoring a person brings back their "Who to call" roles and important
  details, and puts them back as a pet's vet or carer.
- Restoring a stock item no longer counts its stock in and out twice.
- Amounts like 0.1 and 0.2 now add up exactly.
- A "bought" entry can be corrected upwards after some was used.
- Two copies of the program on one computer no longer overwrite each
  other's second backups.
- A backup that fails its check never leaves a file that looks like a good
  backup, and a failed second copy is tried again the same day.

## What we chose
- Every record deleted or link cleared along with a delete is tagged with the
  record the person deleted. Restoring that record restores the tagged ones
  and puts cleared links back (only if still empty). A stock movement deleted
  with its item is marked as still counted, so restoring doesn't count it
  again.
- A record can't be restored while what it links to is still deleted; the
  message says which to restore first.
- Stock counts are changed with exact decimals, rounded to 6 places;
  correcting an entry applies the difference in one step.
- Numbers of a trillion or more are refused.
- Each data folder gets a random id and keeps its second copies in a
  sub-folder with that name.
- Backups are written under a temporary name, checked, then renamed.
- Nesting counts the levels below a record when it moves.

## Why we chose it
The household is told "it can be restored later" and trusts its numbers and
backups; each of these broke that promise in a way they would not notice.

## What else we considered
- Restoring by matching delete times: fragile when several things are deleted
  in the same second.
- Storing amounts as text decimals: a bigger change to every table.

## What this costs us (the downsides)
- History rows for deletes carry a little more detail.
- Second copies made before this change stay in the old shared folder.

## How hard it is to undo
Medium. The behaviour can be reverted; the extra history detail is harmless.

## We should revisit this if
- Households want a "recently deleted" list to restore from (planned).
