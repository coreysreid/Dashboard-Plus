# Dashboard Plus

**Look after what your household has.**
Know what you have, where it is, and when it's running out.

A free, portable, local-first "CRM for a home". Track the pantry and when to
reorder, the weekly shopping, emergency water, the tools and screws you have
stacked away, your pets, and anything else you care about: an art project, an electronics
hobby, Lego sets you flip, a wine collection. See it in charts, and
get gentle questions that help you understand *why* numbers change. The habit
of looking after what you have is what makes a home resilient.

**Status: planning, with the repository skeleton in place.** There is nothing to
open yet. Start with the documents in `docs/`:

- [`docs/VISION.md`](docs/VISION.md): what this is, who it is for, what it will never be
- [`docs/CORE.md`](docs/CORE.md): the one-page v1 promise
- [`docs/DESIGN.md`](docs/DESIGN.md): how it will be built
- [`docs/INFLUENCES.md`](docs/INFLUENCES.md): the ideas we build on, and their authors

Everything stays on your own computer. Nothing is sent anywhere unless you
switch on an optional outside source.

## Licence

MIT. Copyright (c) 2026 Corey Reid. See [`LICENSE`](LICENSE).

## For contributors

Everything needed to check a change is the Python standard library, so there is
nothing to install. From the project folder:

```bash
python tools/check_privacy.py        # nothing personal may be committed
python tools/check_indexes.py        # every folder has a current INDEX.md
python tools/make_project_map.py     # regenerate PROJECT_MAP.md
PYTHONPATH=src python -m unittest discover -s tests
```

GitHub runs the same checks on Windows and Linux for every change. Start at
[`INDEX.md`](INDEX.md) and follow the index in each folder. See
[`AGENTS.md`](AGENTS.md) for the working rules.
