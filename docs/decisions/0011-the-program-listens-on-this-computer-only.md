# 0011. The program listens on this computer only

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Nothing else on the network, and no other website, can reach the dashboard.

## What we chose
Bind to `127.0.0.1` only. Add a per-start secret, host and origin checks. No remote access option.

## Why we chose it
- A household's data is private, and the brief puts remote access out of scope.
- Removes a whole class of risk for a non-technical user.

## What else we considered
- Allow home-network access (for phones): convenient but increases exposure and was ruled out as a non-goal.

## What this costs us (the downsides)
- No phone or second-computer access.

## How hard it is to undo
Medium. It is a deliberate non-goal; reversing it needs authentication, HTTPS and a new security review.

## We should revisit this if
- Corey changes the product direction to include phones.
