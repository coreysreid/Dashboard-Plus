# 0017. Only ask plausible questions

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
The program only wonders aloud about things that could reasonably be linked, so tyre wear is never connected to the garden hose.

## What we chose
Add a plausibility gate to the question loop: measures and events carry declared topics, a watch lists which topics may explain it, and a candidate must pass both plausibility and time closeness. Add a "That doesn't make sense" answer that stops that pairing for good, a weekly question budget, and a clearly labelled Explore mode for deliberate any-to-any comparison.

## Why we chose it
- Corey asked for "ask, don't assert" without dumb questions.
- Time closeness alone produces false leads, because many unrelated things drift together.
- Asking about fewer pairs reduces the multiple-comparison penalty, so real findings are easier to detect.
- Household feedback ("doesn't make sense") teaches the program which declarations are wrong.

## What else we considered
- Ask about everything and rank by statistics: rejected, because it produces nonsense questions and false hits.
- Let an AI judge plausibility: rejected for v1, because it needs a model or outside service and results are not reproducible.

## What this costs us (the downsides)
- Module authors must declare topics well; poor declarations either hide good questions or allow dumb ones.
- Some real, surprising links are never asked about (Explore mode covers this).

## How hard it is to undo
Low. The gate is one filter in the Analysis module and the topic tags are plain data.

## We should revisit this if
- Households report too few useful questions.
- Dismissal counts show a topic pairing is frequently rejected.
