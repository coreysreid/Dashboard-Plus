# Contributing to Dashboard Plus

Thanks for helping make this local household dashboard useful. Start with [the project vision](docs/VISION.md) and [the working rules](AGENTS.md). Describe the household benefit in plain language so Corey can judge the result.

This is a public repository. Use made-up people, addresses, dates and records in every example and test. Never commit a real database, a real `config.toml`, personal paths, tokens or other private household information. If you discover a way household data could be exposed, follow [the private reporting route](SECURITY.md).

Keep each change small. Add a decision record in `docs/decisions/` for a technical choice: what you chose, why, its downsides, how to undo it and when to reconsider. Copy `docs/decisions/TEMPLATE.md` and update its index. Every folder needs a short `INDEX.md` with one row per entry; each Python file begins with a one-line docstring that the index quotes. Keep `README.md` and `PROJECT_MAP.md` current when your change affects them. Dependencies must be few and pinned exactly; ask before adding one.

From the repository root, with Python 3.12 and the pinned dependencies installed, run:

```bash
python tools/check_privacy.py
python tools/check_indexes.py
python tools/make_project_map.py
python -m pip install --require-hashes -r requirements.lock
PYTHONPATH=src python -m unittest discover -s tests
```

The first three commands catch accidental private files, missing index rows and an out-of-date project map. The install checks package hashes. The tests use synthetic data and temporary folders. Explain in your pull request what a person can now do, the checks you ran and any known limit. If you work in one of the [parallel lanes](docs/WORKSTREAMS.md), follow its file ownership and branch rules.
