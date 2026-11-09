# 0018. Outcomes, confirmed wins and a monthly screen

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
The program shows the difference it made, in plain numbers, and only claims a win when it is computed from records or a person confirmed it.

## What we chose
Add metrics (period against previous period, with the basis shown), a wins table filled from computed facts, confirmed questions and the person's own notes, and a monthly "What your records did for you" screen. Keep usefulness answers locally and offer an opt-in, counts-only usefulness report. No automatic reporting.

## Why we chose it
- Corey's goal is that input time produces results that matter: less waste, fewer takeaways, problems caught early.
- Confirmation keeps claims honest; guessed savings would damage trust.
- Local feedback lets us learn whether the product works without breaking the local-only promise.

## What else we considered
- Show only raw charts: rejected, because it does not answer "was it worth it?".
- Automatic telemetry: rejected, because it contradicts the privacy promise and the non-goals.
- Estimate savings automatically: rejected, because estimates look authoritative when they are not.

## What this costs us (the downsides)
- Needs at least two periods of history before showing anything, so early use feels empty (the screen says it is collecting a baseline).
- Wins that need confirmation depend on people answering.
- Without telemetry we learn about usefulness slowly and only from households that share a report.

## How hard it is to undo
Low to medium. It is an additional table, screen and metric declarations.

## We should revisit this if
- Households ignore the monthly screen.
- Usefulness answers stay mostly negative.
