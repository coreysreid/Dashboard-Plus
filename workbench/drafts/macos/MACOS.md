# Dashboard Plus on macOS: build and household plan

Researched **20 November 2026** for batch 17 item 72. Decision 0096 has since produced an unsigned Apple silicon `.app` preview, separate from the Windows-only portable folder built by `tools/build_portable.py`. This document preserves the earlier release proposal; [RELEASE_PLAN.md](RELEASE_PLAN.md), updated **27 November 2026**, starts from the actual preview and covers the signed-release path, real-Mac test, Dock/menu choice and update gates. This is still a plan, not a signed Mac release.

## Recommendation

Ship a signed and notarized **Dashboard Plus.app** outside the Mac App Store first, in a signed/notarized disk image or zip, with household data in the user's Application Support folder. It keeps the program replaceable while leaving the database and backups in a predictable, private location. The app starts a loopback-only local server and opens the default browser, as the Windows build does today. Add a clear **Save and exit** path that stops the server and completes backups before quitting. A headless main for sync is a later, separately reviewed product milestone; ordinary Mac use is local until sync ships.

A USB-style Mac folder can be explored for households that need it, but making the `.app` read and write inside its signed bundle would break replacement and signing assumptions. A removable-data mode would instead use an explicit external data folder, validate its permissions and filesystem behavior, and warn before removal. Do not promise this mode in the first Mac release. Keep the normal data folder outside the app bundle.

## Build and release steps for Lane A

1. **Build on macOS.** Use a pinned, supported CPython and the repository's exact-hash `requirements.lock`; do not reuse the Windows embeddable zip. Freeze or bundle the interpreter, libraries, `src/dashboard`, templates and shipped modules into a Mac `.app`. Add a launcher that starts `python -m dashboard` with an explicit data path, checks for an existing instance, opens the browser and has an unambiguous quit/backup action. Keep the loopback address and per-launch browser token model. Pin the packaging tool and each native binary before release; adding a dependency needs a decision under `AGENTS.md`.
2. **Choose architecture deliberately.** Produce a universal app with `arm64` and `x86_64` slices only if the interpreter and every compiled dependency contain both slices and both paths are tested. Otherwise publish separate Apple silicon and Intel builds with unmistakable names. Do not silently rely on Rosetta. The current Windows `win_amd64` wheel selection cannot supply either Mac slice.
3. **Sign all executable code.** Use a Developer ID Application identity for distribution outside the Mac App Store. Enable the hardened runtime and sign the app's nested executable code and libraries in an order that preserves the final app signature. Check entitlements against actual needs: loopback listening and browser launch do not justify broad file or device access. Verify the final signature before packaging. The household should never be instructed to disable Gatekeeper to make a release work.
4. **Notarize and staple.** Submit the signed distribution artifact with Apple's current `notarytool` workflow, wait for an accepted result, staple the ticket where supported, then validate the final artifact with Apple tools and test a fresh download on a clean Mac. Apple's older `altool` notarization route is retired. If signing/notarization fails, block that release and fix the packaging; do not tell households to bypass the warning.
5. **Publish and update.** Publish versioned artifacts, checksums and plain release notes. On update, stop Dashboard, make and verify a backup, replace the app, then reopen the **same** Application Support data. Rollback must not blindly open a database already migrated by a newer app. Test Mac's quarantine/Gatekeeper path from the downloaded artifact, not only a developer build.

These steps are a design, not a claim that a bundled Mac app, signing identity or Apple build runner exists today. A first build should be produced on a Mac runner and smoke-tested there before writing household download instructions.

## Data and what differs from Windows

| Concern | Current Windows folder | Proposed macOS app |
|---|---|---|
| Program | `Dashboard Plus/app/` contains Windows embeddable Python and modules; `.bat` starts it | Signed `.app` contains Mac interpreter, code and read-only resources; user can replace it without moving records |
| Household records | `Dashboard Plus/data/` beside the launcher | `~/Library/Application Support/Dashboard Plus/` for the current user, with private permissions and separate `data`, `backups`, `run`, `reports` areas as needed |
| Start and stop | Open and Save-and-exit `.bat`, browser page | Open `.app`, browser page, visible Save and exit/Quit; no hidden second server; launch token stays local |
| Backups and moving computers | Data folder travels with the portable folder | Backups live under Application Support plus any chosen second copy; use Dashboard's checked backup/restore flow to move data, not a live SQLite copy |
| Updates | Replace program files, keep `data` | Replace `.app`, keep Application Support data; check schema and backup before migration |
| OS trust | Unsigned batch launch may trigger SmartScreen | Developer ID signing, notarization and Gatekeeper validation for downloaded app |

Apple's Application Support location is user-specific. The `~/Library/...` form is an example path for household explanation; the program should ask macOS for `applicationSupportDirectory`, not build the path from a username. Follow decision 0055's owner-only data permissions and refuse accidental data-folder symlinks or wrong ownership after checking platform behavior. Do not write a database, key or report inside the signed `.app` or public Downloads folder. A household moving from Windows can export a checked backup and restore it on Mac if the formats are compatible; test that exact migration with invented data. The Windows help text and screenshots cannot simply be copied because Mac's install, warnings, paths and quit flow differ.

## Plain household steps once a build is verified

1. Download the Mac build for your Mac's processor from the project's release page, or the verified universal build. Open the downloaded disk image or zip and move **Dashboard Plus.app** to Applications.
2. Open the app from Applications. macOS checks the signed and notarized app. The browser opens Dashboard on this Mac. If macOS says it cannot verify or open it, stop and use the project's help link with the exact release version; do not change Mac security settings.
3. Answer the normal household setup questions. Your records stay in this Mac account's Application Support folder. Use **Save and exit** before shutting down or moving any external backup drive.
4. To update, use Save and exit, keep a checked backup, replace the app in Applications and reopen it. The data folder stays put. To move to another computer, use Dashboard's backup and restore screens.

These are proposed words; publish them only after an actual signed/notarized build passes clean Mac installation. For the first sync release, this Mac app would be a computer member under decision 0089, using the same member identity and filtered exchange as Windows; the Mac build alone does not enable sync.

## Acceptance before a Mac release

1. Build both architecture targets (or one verified universal app), launch on clean current macOS on Apple silicon and Intel, and run `tools/check_all.py` plus a packaged-app smoke test. Confirm bundled modules, templates, native wheels, locale dates and the browser token work without a developer Python installation.
2. Download the final artifact on a clean Mac; Gatekeeper accepts its Developer ID signature and notarization, stapled ticket validates, and no security-bypass step is needed. Repeat after an update.
3. Open, close, reopen and recover from a crash. One server owns a data folder; Save and exit completes a backup. No `0.0.0.0` listener or public network route appears. Helper route remains loopback-only.
4. Check Application Support directory and database permissions with two local Mac accounts, a symlink, a removable filesystem and an interrupted backup. Neither account can see the other's ordinary records by default. Report filesystem limits honestly.
5. Replace the app while keeping data; restore an invented Windows backup into a clean Mac account; reject a too-new database or wrong-format backup without damage. Test a clean uninstall instruction that distinguishes removing the app from deleting household records.
6. If sync is later enabled, re-run the remote-boundary review on macOS, including private-interface binding and member key storage. Mac packaging must not broaden the local server's exposure.

## Sources and limits

Official sources opened and checked **20 November 2026**:

- [Apple Developer: Signing Mac Software with Developer ID](https://developer.apple.com/developer-id/) — Developer ID is the outside-App-Store distribution identity.
- [Apple Developer: Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) and [TN3147: migrating to the latest notarization tool](https://developer.apple.com/documentation/technotes/tn3147-migrating-to-the-latest-notarization-tool) — notarization and the supported tool path.
- [Apple Platform Security: Gatekeeper and runtime protection](https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web) — downloaded-app checks and runtime protections.
- [Apple Developer: Building a universal macOS binary](https://developer.apple.com/documentation/apple-silicon/building-a-universal-macos-binary) — Apple silicon and Intel slices.
- [Apple Developer: `applicationSupportDirectory`](https://developer.apple.com/documentation/foundation/filemanager/searchpathdirectory/applicationsupportdirectory) — user Application Support data location.
- Repository `tools/build_portable.py`, `tools/portable.toml`, `src/dashboard/__main__.py`, `README.md`, and decision 0055, read **20 November 2026** — current Windows-only build and data behavior. Exact Mac packaging tool, entitlements, signing commands, firewall behavior, supported OS versions and installer format need a real Mac build and review before the household steps are published.
