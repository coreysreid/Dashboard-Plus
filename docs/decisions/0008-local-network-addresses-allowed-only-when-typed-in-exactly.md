# 0008. Local-network addresses allowed only when typed in exactly

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The API connector can talk to something like a smart-home hub, but only at an address the person entered.

## What we chose
Private and loopback addresses are blocked unless the person adds that exact address to the allow-list, with an explanation.

## Why we chose it
- Needed for the smart-home example in the brief.
- Exact addresses limit the risk of a source being pointed at other devices on the home network.

## What else we considered
- Block all private addresses: safest, but removes the smart-home use.

## What this costs us (the downsides)
- A person could type in a wrong or risky address.
- Slightly more setup for that one use.

## How hard it is to undo
Low. It is a rule in one place.

## We should revisit this if
- We see misuse.
- Home Assistant integration needs a different approach.
