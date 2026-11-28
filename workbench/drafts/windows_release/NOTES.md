# Core gaps for an installed Windows version

Checked **27 November 2026**. [PLAN.md](PLAN.md) is the batch 24 item 129 release plan. The current program ships an unsigned portable zip, batch launchers and data beside the program; CI smoke-tests that route. It does not ship an MSI, EXE installer, MSIX, Store listing, installed-data migration, sign-in startup or automatic update.

Lane A needs a separate installed-app launch and data path outside read-only package files, checked backup/restore from a portable copy without overwriting it, a second backup destination that remains separate, one instance per account/data folder, startup opt-in, package-specific helper/loopback checks, versioned migrations and clear uninstall/rollback words. Store MSIX should be prototyped first; if its app model breaks any local or helper behavior, choose an installer with recorded evidence. A Store MSI/EXE listing still needs publisher signing and publisher-owned updates. Direct signing alone does not promise no SmartScreen warning.

User 1's portable zip remains a useful USB mode with an honest source-and-checksum check before any local Unblock instruction. The current README's **Unblock** step removes Windows's internet-source mark; it is not signature verification. No installer, Store or real-machine warning check was run here. Nothing in this workbench plan changes the shipped app.
