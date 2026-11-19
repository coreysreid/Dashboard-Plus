# 0087. An Add a helper form makes one key, even if it is sent twice

- **Status:** Accepted
- **Date:** 2026-11-19
- **Decided by:** Claude (technical decision delegated by Corey), from Lane B's UX check of the helper feature

## In plain words
If you press **Make a key** and the form is sent again, for example by
refreshing the key page and agreeing to resend, Dashboard Plus no longer makes
a second working key. It says: "A key was already made from this form. It
cannot be shown again. Return to Helpers if you want to make another."

## What we chose
- Each Add a helper form Dashboard shows carries its own one-use token
  (`form_token`, random, kept in memory only), alongside the page's usual
  security token.
- The first successful key spends it. Sending the same form again is refused
  with 409 and the words above; no key is shown, because the first key page was
  the only time it could be.
- A form Dashboard did not show (or one from before it was last opened) is
  refused with "This form is out of date, so no key was made. Please fill it in
  again.", keeping what was typed.
- A form refused for a fixable reason (no name, no part ticked) stays usable,
  so the person can correct it and send it.
- The latest 50 open forms are remembered; older ones must be filled in again.

## Why we chose it
- A second active key that nobody meant to make is a second password to lose.
- The key can be shown only once, so the repeat must explain itself rather
  than silently do nothing.

## What else we considered
- Refusing a second helper with the same name: a household may want two keys
  with one name on purpose (one per assistant app), and it would not stop a
  resent form with a new name.
- Redirecting after making the key (post/redirect/get): the key would have to
  be stored or put in an address to show it after the redirect, which
  decision 0066 rules out.

## What this costs us (the downsides)
- A form left open across a Dashboard restart must be filled in again.
- Remembered forms live in memory per running Dashboard; this is fine because
  Dashboard runs as one process on one computer.

## How hard it is to undo
Easy: drop the `form_token` field and its check in `helper_settings.py`.

## We should revisit this if
- People report "out of date" more than rarely, for example after a long
  break with the page open.
