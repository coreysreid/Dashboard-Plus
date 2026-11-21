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
| smoke_test_portable.py | Start the built portable folder or Mac app, check it answers, and close it safely. | the Windows or Mac build check fails |
| build_macos.py | Build the unsigned Mac app and zip (Dashboard Plus.app) for this Mac's processor: bundled Python, libraries, launcher. | changing what ships in the Mac app |
| macos.toml | Pinned Mac Python version, downloads and checksums for the Mac build | updating the Mac app's Python |
| make_migration.py | Write a module's next numbered migration from its tables.toml. | a module's tables changed |
| load_example.py | Load a made-up example household into an empty data folder, for demos, screenshots and testing. | demonstrating or testing with realistic data |
| make_screenshots.py | Make the example screenshots: run each example household through every stage of using the dashboard. | the screens changed and the gallery needs remaking |
| screenshots.js | Browser steps for make_screenshots.py (Node and Playwright) | changing how screenshots are taken |
| browser_check.py | Click through the real dashboard in Chromium (setup, Set up my home, dates, stock in, stocktake, Mark returned, Mark done, Things to do, spreadsheet import, Review keys and buttons, readiness questions, Think it through drills, charts, pet feeding at 320px, private details, closing) and fail loudly. | a screen or its browser code changed |
| browser_check.js | Browser steps for browser_check.py (Node and Playwright): what is clicked and checked | changing what the browser check clicks |
| make_project_map.py | Build PROJECT_MAP.md from every INDEX.md in the repository. | changing the map format |
