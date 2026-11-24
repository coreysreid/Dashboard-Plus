# 0085. A helper may have only so many suggestions waiting on Review

- **Status:** Accepted
- **Date:** 2026-11-19
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
A helper can send at most 200 suggested records a day, but nothing stopped them piling up on the Review page over
many days until a person could not get through them. Now one helper may have at most 500 suggestions waiting. If a new
batch would go over, the whole batch is turned away with a plain message asking the household to look at the waiting
ones first. Accepting or rejecting suggestions makes room again.

## What we chose
- The limit is 500 per helper, counted as suggested rows still waiting (not accepted, not rejected). It can be
  changed in the app settings, like the requests-per-minute limit (`HELPER_REVIEW_QUEUE_LIMIT`).
- A request is refused whole if the rows already waiting plus the rows in it come to more than the limit. Exactly
  reaching the limit is allowed. Nothing from a refused request is kept.
- The reply is **429** with the code `review_queue_full` and the message "<n> suggestions from this helper are already
  waiting on Review. Ask the household to look at them first." There is no `Retry-After`, because only a person
  deciding on Review frees room, not time passing.
- Imported spreadsheet batches (decision 0080) are not a helper's, so they neither count against any helper nor
  fill its room.
- A retry of an earlier request (same key and body) still gets its first answer even when the queue is full, because
  it adds nothing.
- `GET /api/v1/me` shows `review_queue_limit` and `suggestions_waiting` so a helper can stop before it is refused.
- The check comes right after the daily limit and before the entries are examined, so it is cheap and does not
  depend on anything in the records.

## Why we chose it
- The abuse review (case 11) found that the per-day cap and the request-rate limit still let a helper, or a mistaken
  loop, bury the household's Review page over a few days.
- Refusing whole matches how every other refusal works: all or nothing, so a helper never has half a batch to untangle.
- Helpers get a clear signal and a reason that points at a person, which is the right place for the problem.

## Why 429 and not 409
- 429 already means "too much from this sender, stop for now" to helper programs and the people who write them, and the
  daily limit uses it too, so all three limits behave alike.
- 409 means the request clashes with the stored state of what it names. We already use it for a reused request key,
  where retrying with a new key is the fix; here no change to the request helps.
- Cost: a program that retries every 429 after a pause will retry this one too. Each retry is cheap, is counted by
  the requests-per-minute limit, and the message tells a person-facing helper to stop.

## What else we considered
- **Drop the oldest waiting suggestions to make room.** Rejected: it would silently throw away something the
  household has not seen.
- **Count per household instead of per helper.** Rejected: one noisy helper could then shut out the others.
- **Just rely on the daily limit.** Rejected: 200 a day for a week is 1,400 unread suggestions.
- **A smaller number, such as 100.** Possible; 500 leaves room for several honest days of work while stopping a flood.
  It is a setting, so a household or a later release can change it.

## What this costs us (the downsides)
- A legitimate helper is stopped if the household is away for a while, and stays stopped until someone reviews. That
  is the point, but it can look like a fault.
- One count query on every suggestion. It is on an indexed column and cheap at this size.
- A helper can take only its own room. It cannot see how many another helper has, and a household with many helpers
  could still see many waiting in total.
- The limit is a setting in the app, not yet something the household can change on a page.

## How hard it is to undo
Easy. Remove the check in `proposals.submit` and the two `/me` fields. Nothing is stored for it.

## We should revisit this if
- Households meet `review_queue_full` often in normal use (the number is too small, or Review needs a bulk "accept
  all from this helper" action).
- A total cap across helpers is wanted.
