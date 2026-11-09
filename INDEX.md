# ./  (summary: Dashboard Plus, a local-first home dashboard; start here)
Follow the INDEX.md in a folder before opening its files. Hidden files are not listed.

| Entry | What it is | Open it when |
|---|---|---|
| README.md | Friendly introduction, status and how to run the checks | first meeting the project |
| AGENTS.md | How an AI agent should work here | before changing anything |
| CONTRIBUTING.md | Public contribution rules and checks | before contributing |
| SECURITY.md | How to report a problem that could expose household data | reporting security concerns |
| CLAUDE.md | One line pointing to AGENTS.md | never; tools read it for you |
| LICENSE | MIT licence, Copyright (c) 2026 Corey Reid | checking reuse terms |
| PROJECT_MAP.md | Generated one-page map of every INDEX.md | you want the whole picture |
| config.example.toml | Example settings (the real file lives in the data folder) | adding a setting |
| pyproject.toml | Project name, version and Python version | changing project metadata |
| requirements.txt | The few runtime libraries, pinned to exact versions | adding or updating a library |
| requirements.lock | Generated: those libraries with checksums | never by hand; regenerate it |
| .github/ | CI workflow and pull request checklist | changing the automatic checks |
| docs/ | Vision, core promise, design, decision records | understanding why or how |
| examples/ | Optional worked module examples, not installed by default | learning to write a module |
| modules/ | Optional features, one folder each | adding or changing a topic |
| src/ | The program itself | changing how the app works |
| tests/ | Automatic tests | adding or fixing a test |
| workbench/ | The second agent's own space: drafts, reports, research (not part of the program) | reviewing Lane B's work |
| tools/ | Repository checks and generators | changing CI checks |
