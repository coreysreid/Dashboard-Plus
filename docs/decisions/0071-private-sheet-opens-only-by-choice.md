# 0071. A private sheet opens only by choosing "Show private sheet", never from a link

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey), from Lane B's current-build UX check and sensitive-detail recheck

## In plain words
The private medical sheet asks "Show it only when you mean to print or share
it" first. But anyone with the address ending `?show=1` (a bookmark, a copied
link, a browser's history) skipped that question. Now the sheet can only be
opened by pressing the **Show private sheet** button on the question page. The
address alone always lands on the question. Printing the sheet still works.

## What we chose
- The button is a small form that sends a POST (with the page's own security
  token) to the sheet's address. Only that POST shows a sheet with private
  details. A plain visit, including `?show=1`, shows the question page.
- The sheet it shows is the normal printable page, so **Print** works. The
  address stays the plain sheet address, with nothing in it that unlocks it.
- Sheets with no private details are unchanged: a plain link opens them.

## Why we chose it
- It closes the bypass the review found with no new storage and no new moving
  parts: nothing to expire, clean up or leak between browser tabs.
- A POST result cannot be bookmarked, linked to or re-opened from history, which
  is what "only by choice" means.

## What else we considered
- A short-lived reveal remembered by the server for this browser session: more
  code, a timer to get wrong, and a link would work again for as long as it lasts.
- Keeping the link and writing down why it is fine: the warning is about a
  mistaken click or a shared screen, and a bookmarked link defeats that.

## What this costs us (the downsides)
- Reloading the revealed sheet makes the browser ask "resend form?"; going back
  to the sheet from another page shows the question again. That is the point,
  but it is one extra click.
- This is protection against accidents on a shared screen or link, not against
  someone already using this computer's session.

## How hard it is to undo
Easy: turn the form back into a link and read the query again in `sheets.py`.

## We should revisit this if
- Households find the resend prompt on reload confusing, or the Agent API needs
  a way to fetch a private sheet (that would be its own explicit grant).
