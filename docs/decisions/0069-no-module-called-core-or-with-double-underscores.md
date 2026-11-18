# 0069. A module may not be called "core" or use double underscores in its name

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** decision 0055 (modules confined to their own tables)

## In plain words
The program's own tables all start with `core__`. A module named "core", or with a name that could be mistaken for part of
another module's table names, could have slipped past the guard that keeps modules inside their own tables. Such names are
now refused, and the module is left out with a plain message.

## What we chose
- Module names may not be `core`, may not contain `__`, and may not end with `_`.
- At start-up, if a module named `core` ever reached the loader anyway, it is set aside and reported; it never replaces the
  program's own database changes.
- The message says: "'core' is reserved for the program itself."

## Why we chose it
- The guard in decision 0055 decides what is "your own table" by the module's name. A module called `core` would have owned
  every `core__` table; `pets_` would have matched `pets___x`. Closing this at the name is the simplest, surest fix.
- Found while planning the Agent API, which adds more `core__` tables worth protecting.

## What else we considered
- Making the guard smarter about prefixes: more code and more ways to be wrong than refusing the names.

## What this costs us (the downsides)
- A household's own module with such a name must be renamed. None of the shipped or example modules use one.

## How hard it is to undo
Easy. Two small checks to remove; nothing else depends on them.

## We should revisit this if
- We want "core" to be a real module name for something other than the program itself (unlikely).
