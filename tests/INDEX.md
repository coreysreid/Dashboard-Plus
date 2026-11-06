# tests/  (summary: automatic tests; synthetic data only)
Run: PYTHONPATH=src python -m unittest discover -s tests

| Entry | What it is | Open it when |
|---|---|---|
| test_check_privacy.py | Tests for the privacy check. | changing privacy rules |
| test_check_indexes.py | Tests for the index check. | changing index rules |
| test_project_map.py | Tests for the project map generator. | changing the map |
| test_repository.py | Tests that this repository passes its own checks. | CI fails on the repo itself |
