# 0082. Every page shows the connection mode

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by User 1); User 1 asked for it: "The app should clearly display that it's in isolation mode or online."

## In plain words
The top of every page now says **On this computer only**. If any helpers can
connect, it adds how many, for example "On this computer only · 2 helpers can
look". If sharing with other devices is ever switched on (decision 0081, still
a design), this is where it will say so.

## What we chose
- A small badge beside the app's name in the header of every page, linking to
  Settings → Helpers. On a phone it sits on its own line above the links.
- Its words come from facts the app knows: the app only listens on this
  computer (decision 0055), and the number of helpers whose access is on.
  Nothing about the household is shown to someone who isn't signed in.
- The footer now reads "Dashboard Plus itself sends nothing anywhere; a helper
  you connect sees only what you tick", because with helpers (decisions 0067,
  0074) "Nothing is sent anywhere" was no longer the whole truth.

## Why we chose it
- User 1 asked for the mode to be clear at all times.
- Isolation is the default, so saying it plainly sets the pattern for when
  sharing exists: the badge will change words, never disappear.
- A helper with access is the one way records can leave the computer today
  (through that helper), so it belongs in the same place.

## What else we considered
- A notice only on the Settings page: easy to miss.
- A coloured banner: louder than a calm default deserves; it should be kept
  for a change from the default, such as sharing switched on.

## What this costs us (the downsides)
- One more database count on every page (cheap, and skipped when not signed in).
- The badge cannot know whether a helper uses an online AI service; the
  Helpers page explains that instead.

## How hard it is to undo
Easy: remove the badge from `base.html` and the count from `app.py`.

## We should revisit this if
- People don't notice it, or read "helpers can look" as something alarming.
- Sharing is built (decision 0081): the badge must then name the mode and the devices.
