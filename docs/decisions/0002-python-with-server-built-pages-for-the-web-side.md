# 0002. Python with server-built pages for the web side

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The screens are built by the program itself and sent to the browser, rather than being a separate JavaScript application.

## What we chose
Python with a small, well-established web framework, pages produced on the server, and only light browser scripting where needed (for example the lazy-loading grid).

## Why we chose it
- Fewest moving parts: no separate JavaScript build step to maintain for years.
- Matches the Python modules, so one language covers the core and the modules.
- Easy to bundle into a portable folder and easy for a newcomer to read.
- Fits the goal that the project outlives its maintainer.

## What else we considered
- A single-page JavaScript app: slicker, but needs a JavaScript toolchain forever.
- Python standard library only, no framework: smallest, but we would re-implement routing, forms and security protections that a mature framework already does safely.

## What this costs us (the downsides)
- Highly interactive screens (drag-and-drop, live updating) take more effort than in a JavaScript app.
- We depend on one framework, pinned to an exact version.

## How hard it is to undo
Medium. The data layer, modules and API are independent of how pages are drawn, so only the web layer would be rewritten.

## We should revisit this if
- Screens we need feel slow or clumsy because of this approach.
- The framework is no longer maintained.
