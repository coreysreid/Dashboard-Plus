# 0024. Prompt engine in the core, content in modules

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
The program can ask "have you thought about…?" questions suited to your home, and the questions themselves live in modules, not the core.

## What we chose
Add a small prompt engine to the core: it reads `prompts.toml` files, matches prompts to a household profile, hides prompts whose answer is already in the data, records dated answers (Yes, Not relevant, Not yet, Tell me more) and schedules reviews. A coverage view reports how many applicable prompts were looked at per area. All wording and subject matter live in modules.

## Why we chose it
- Helping people think is one of the product's pillars, and every module can use it (stock, pets, garden), so the machinery belongs in the core once.
- Keeping content in modules keeps the core free of any topic, which is a core promise.
- It reuses the plausibility idea from the question loop: ask only what fits.

## What else we considered
- Put prompts only inside the Readiness module: other modules could not contribute their own.
- A free-text checklist feature: cannot match prompts to a household or detect what is already recorded.

## What this costs us (the downsides)
- The core grows by one feature, with a small condition language (profile matches and missing data) that must stay simple.
- Poorly written prompts could nag; the budget and the Not relevant answer limit that.
- Coverage numbers could be misread as a safety score; the wording is fixed to say looked at, never safe.

## How hard it is to undo
Medium. Prompts are plain data; removing the engine would remove the panel but not stored answers.

## We should revisit this if
- Households ignore the panel or mark most prompts Not relevant.
- The condition language needs to become more complicated than files can express.
