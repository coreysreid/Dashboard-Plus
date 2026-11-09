# tests/  (summary: automatic tests; synthetic data only)
Run: pip install --require-hashes -r requirements.lock, then
PYTHONPATH=src python -m unittest discover -s tests

| Entry | What it is | Open it when |
|---|---|---|
| test_check_privacy.py | Tests for the privacy check. | changing privacy rules |
| test_check_indexes.py | Tests for the index check. | changing index rules |
| test_project_map.py | Tests for the project map generator. | changing the map |
| test_server.py | Tests for starting, protecting and safely closing the local web server. | changing startup or closing |
| test_main.py | Tests for the command-line entry point and its plain-language messages. | changing the command line |
| test_build_portable.py | Tests for the portable Windows build, using a stand-in for the Python download. | changing the build |
| test_lock_requirements.py | Tests for the requirements lock generator. | changing how libraries are locked |
| test_repository.py | Tests that this repository passes its own checks. | CI fails on the repo itself |
