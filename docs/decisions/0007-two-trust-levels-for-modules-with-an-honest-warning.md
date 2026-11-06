# 0007. Two trust levels for modules, with an honest warning

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Modules made of files only are safe; modules that include code are clearly labelled as powerful.

## What we chose
Declarative modules (files only) install by copying a folder. Code modules need an explicit extra confirmation, with a plain warning that they run with the user's own permissions. We do not claim a sandbox.

## Why we chose it
- Declarative modules cannot run code, so they are safe by construction and anyone can write one.
- Claiming to sandbox Python would be false comfort; honesty is better than security theatre.
- Still allows useful community modules (sources, insights).

## What else we considered
- Only declarative modules in v1: safest, but blocks outside sources and custom insights.

## What this costs us (the downsides)
- A person who ignores the warning and installs a bad code module can be harmed.
- Support burden when a community module misbehaves.

## How hard it is to undo
Medium. Tightening later (for example to declarative only) would break existing code modules.

## We should revisit this if
- A harmful module is reported.
- A real sandbox option becomes practical.
