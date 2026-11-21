# Mac preview: current gaps after decision 0096

Checked **21 November 2026**. The unsigned Apple silicon preview now ships from GitHub Actions; [MACOS.md](MACOS.md) is the earlier release proposal, not the state of the preview. [The household read-through](../../reports/2026-11-21-mac-preview-readthrough.md) gives exact README and bundled read-me replacement words.

A real Mac test is still needed for the quarantined download, first-open warning, Finder replacement update, browser reopening, Application Support records and second backup location. GitHub CI starts the app from its build folder and cannot prove those household steps. The preview has no Intel artifact, Developer ID signature or notarization. The launcher has no Dock/menu Quit control and a slow start can outlast its 20-second alert window. Those are product/release gaps, not something this workbench draft can fix. No household should be promised a signed release or told to turn off Mac security checks.

Before a public Mac release, Lane A needs the signed/notarized build and real-device acceptance in decision 0096. Keep the preview's data separate from the `.app`; do not move or erase the Application Support folder during an update. Source: decision 0096 and the shipped Mac build/README, checked 21 November 2026.
