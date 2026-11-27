# Working in this repository

Dashboard Plus is a public, local-first "CRM for a home". Start with
[INDEX.md](INDEX.md) and follow the `INDEX.md` in each folder downward; open
a file only when its index row says you need it. Do not read the whole tree.

Two agents work in parallel: read [docs/WORKSTREAMS.md](docs/WORKSTREAMS.md) for your lane
and the files you may edit before changing anything.

## Rules that never bend
- The repository is public. Never commit real names, personal data, tokens,
  database files, a real `config.toml`, or personal paths. Use synthetic data.
- Never name the project owner or their household in files, commit messages,
  pull requests or comments. Write **User 1** for the owner and **User 2** for
  their partner, and leave out their home town, region and real belongings.
- The program never stores fraud-grade details (decision 0141): no field may ask for a password, PIN, alarm,
  door, safe or Wi-Fi code, full card or bank account number, tax, health card, passport or licence number, a
  scan or copy of ID, or a security answer. Ask who to call, where it is kept (`guard = "where_kept"`) or only
  the last 4 digits (`guard = "last_digits"`); a module that declares such a field does not load. Example data
  models the safe forms.
- Every technical decision needs a record in `docs/decisions/` (copy
  `TEMPLATE.md`): what was chosen, why, the downsides, and how to undo it.
- Every folder has a short `INDEX.md` (25 lines or fewer, one row per entry).
  Every Python file starts with a one-line docstring that its index row quotes.
- Dependencies are few and pinned to exact versions. Ask before adding one.
- Explain choices in plain language. User 1 judges the product, not the code.
- Lane A merges its own pull requests once every check is green; see "Who merges" in docs/WORKSTREAMS.md for the exceptions.

## Before you finish any change
One command runs every check: `python tools/check_all.py`. The individual steps are:
```bash
python tools/check_privacy.py
python tools/check_indexes.py          # add --skeleton to see missing rows
python tools/make_project_map.py       # regenerates PROJECT_MAP.md
pip install --require-hashes -r requirements.lock
PYTHONPATH=src python -m unittest discover -s tests
```
Keep `README.md` and `PROJECT_MAP.md` current. Small commits, tests first.
