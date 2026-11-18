# Optional data-folder passphrase: portable Windows research

Checked **18 November 2026** for a Windows 10/11 app that may run from a USB stick. This is research for batch 12 item 46, not an encryption feature or a recommendation that a household's current data folder is protected. Dashboard Plus currently uses an unencrypted SQLite database and makes a second backup on the computer when enabled. Its setup screen says the data folder is not encrypted.

## Options and tradeoffs

| Option | What it covers and how it travels | Forgotten passphrase and limits |
|---|---|---|
| **BitLocker To Go on the USB drive** | Windows protects the removable drive, so the program and data folder travel together after unlock. Microsoft says removable drives can unlock on another computer with a password or smart card; enabling BitLocker is listed for Windows Pro, Enterprise and Education. This is an **external drive setup**, not a Dashboard Plus passphrase screen. | Keep the BitLocker recovery key away from the stick. Microsoft says losing access to the recovery key can leave a drive unrecoverable. The app's computer-side second backup is **outside the USB encryption** and needs its own protection and a tested restore path. |
| **App-owned passphrase using SQLCipher** | SQLCipher is an encrypted SQLite implementation with per-page AES-256 and a passphrase-derived key. Its community edition has a BSD-style licence with attribution requirements. It could protect `dashboard.db` while preserving a portable app, but requires a pinned, packaged native dependency and a reviewed migration from the current SQLite file. | SQLCipher does not itself give Dashboard Plus an account reset. If no usable passphrase, recovery key designed by the app, or older readable backup remains, the records cannot be opened. SQLCipher alone does **not** protect `config.toml`, secrets, attachments, exports, temporary files or backups; a whole-folder promise needs an explicit plan for each. |
| **Cryptomator vault** | An external encrypted file vault can cover a folder and offers a recovery key. Its desktop workflow adds a vault mount/unmount step before opening the portable app. | Its own docs warn that plaintext copies made by programs while the vault is unlocked can sit outside it. The computer-side second backup and accidental exports still need attention. The app cannot silently assume a mounted vault exists. |
| **VeraCrypt portable mode** | An external encrypted container can move with a USB drive. | VeraCrypt's portable-mode documentation says it requires administrator rights. That conflicts with an expectation that the app opens on an arbitrary Windows computer without an administrator. |
| **Windows DPAPI as the sole key** | Windows can protect a key for one account. | Microsoft's `CryptProtectData` documentation says decryption normally needs the same user credentials and computer. Alone, it would strand a portable folder on another computer; it can at most be an optional convenience unlock, not the recovery plan. |

**Recommendation for Lane A:** For a household that already has a suitable Windows edition and knows how to manage its recovery key, document BitLocker To Go as an external way to protect a USB stick now, with an explicit warning that the separate computer-side backup is not covered by that stick. For M3, assess an app-owned encrypted-data design using SQLCipher only after deciding how **all** data-folder outputs, two backup locations, exports, attachments and restore will be protected. Do not add a passphrase toggle that encrypts only the primary DB while still creating readable backups. Cryptomator and VeraCrypt can remain household-managed alternatives; they should not be presented as one-click app features.

## Proposed household words

> **Protect this data folder with a passphrase (optional).** You will need it to open these records, including on another computer. Keep the recovery key somewhere separate from the USB drive. If you lose both, Dashboard Plus cannot open these records. Backups on this computer also need protection; check that you can open a backup before relying on it.

That wording applies only **after** a tested app recovery-key and encrypted-backup design exists. Before that, the shipped setup should continue to say **“The data folder is not encrypted.”** Do not promise a password hint, remote reset, or support-team recovery. A passphrase should never be written to `config.toml`, command-line logs or an ordinary export.

## Core questions before implementation

1. Generate a random data key and wrap it separately with a household passphrase and an offline recovery key, or choose another documented key hierarchy. Define key changes, recovery-key replacement, memory handling and what happens when both are lost. SQLCipher's passphrase mode alone does not supply the app recovery key in the proposed words.
2. Inventory every on-disk location: live DB plus WAL/journal and temp files, attachments, configuration/secrets, reports/exports, `data/backups`, optional computer-side backups, and restore staging. State which are encrypted and which contain no private values. Do not call it whole-folder protection until this is true.
3. Make daily, safe-close and before-update backup copies readable only with the expected key or an independently protected recovery key. A failed second copy must remain visible. Test restore on another Windows computer before relying on the plan.
4. Define launch/close order on a removable drive: unlock before opening the database, keep backups from writing plaintext outside the protected area, close and verify writes before removal, then lock the key/vault. Avoid a partially encrypted migration; make a verified backup and all-or-nothing switch.
5. Decide how the optional setting interacts with a lost or stolen stick, an older unencrypted backup, a forgotten passphrase and the private-detail erase ledger. Encryption does not erase copies already made.

## Sources and reuse notes

All URLs were reachable and read **18 November 2026**. These are vendor documentation, not a claim of independent security certification.

- [Microsoft BitLocker overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/) — BitLocker To Go coverage and Windows edition availability. Microsoft Learn content; link and summarize, do not copy its text into product screens.
- [Microsoft BitLocker FAQ](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/faq) and [finding a recovery key](https://support.microsoft.com/en-us/windows/find-your-bitlocker-recovery-key-6b71ad27-0b89-ea08-f143-056f5ab347d6) — removable drive unlock and loss/recovery behavior. Microsoft documentation, linked rather than reproduced.
- [SQLCipher design](https://www.zetetic.net/sqlcipher/design/) and [community edition/licence](https://www.zetetic.net/sqlcipher/community/) — database encryption design and BSD-style community licensing/notice requirement. Use exact licence text and dependency review before bundling.
- [Cryptomator security target](https://docs.cryptomator.org/security/security-target/) and [password/recovery key](https://docs.cryptomator.org/desktop/password-and-recovery-key/) — vault scope, plaintext outside an unlocked vault and recovery key. Linked summaries only.
- [VeraCrypt portable mode](https://veracrypt.io/en/Portable%20Mode.html) — administrator requirement. Linked summary only.
- [Microsoft DPAPI CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata) — user/computer-bound decryption. Microsoft documentation, linked rather than reproduced.
- Current app backup behavior: `src/dashboard/core/backups.py` and `src/dashboard/core/db.py`, checked 18 November 2026. No external licence is needed to restate our own code behavior.
