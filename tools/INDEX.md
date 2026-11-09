# tools/  (summary: scripts that check, lock and build the project; run by CI)
| Entry | What it is | Open it when |
|---|---|---|
| repofiles.py | Shared helper that lists the files belonging to the repository. | a tool needs the file list |
| check_all.py | Run every check a change must pass before it is pushed, with one command. | before every push |
| check_privacy.py | Fail the build if anything private or machine-specific is committed. | tuning what counts as private |
| check_indexes.py | Check that every folder has a short, complete and current INDEX.md. | changing the index rules |
| lock_requirements.py | Write requirements.lock: every pinned library with the checksums PyPI publishes. | updating a library |
| build_portable.py | Build the portable Windows folder and zip: bundled Python, libraries and launchers. | changing what ships in the folder |
| portable.toml | Pinned Python version, download address and checksum for the build | updating the bundled Python |
| smoke_test_portable.py | Start the built portable folder, check it answers, and close it safely. | the Windows build check fails |
| make_migration.py | Write a module's next numbered migration from its tables.toml. | a module's tables changed |
| make_project_map.py | Build PROJECT_MAP.md from every INDEX.md in the repository. | changing the map format |
