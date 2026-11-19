# Household sync acceptance checks (design only)

Checked **19 November 2026** against the item 69 brief, [SYNC.md](SYNC.md), and the shipped behaviors named in [NOTES.md](NOTES.md). Each check uses two or three invented devices and synthetic records. Nothing in this file asserts that sync is built.

| # | Set up and action | Expected result |
|---|---|---|
| 1 | Fresh install; open every page before pairing. | Badge says “On this computer only”; no sync listener or network request. |
| 2 | Pair Sam's laptop over a private network, with no modules ticked; compare main's fingerprint on both screens. | No records move until a module is chosen and the identity is verified; invitation expires and cannot pair a second device. |
| 3 | Present a helper key to the sync door, then a member key to `/api/v1`. | Both are refused without revealing whether a household or table exists. Turning one key off does not affect the other. |
| 4 | Swap main's TLS identity or route the address to another program after pairing. | No member key or records sent; a plain identity warning requires a new, independently verified pairing. |
| 5 | Move main off its chosen private address, sleep it, restart it, or switch Allow sync off. | Network listener closes; member retains its copy and unsent outbox. No public or wildcard bind. Restart remains off until chosen on main. |
| 6 | First pull of Stock and People; interrupt halfway, then retry. | Checked backup exists before apply; incomplete snapshot changes nothing. Completed pull has links, global IDs and one saved cursor. A second pull adds nothing twice. |
| 7 | Member edits Rice's minimum offline and pushes twice with the same operation ID. | Main gets one Review request and one row, marked waiting; live Rice stays as it was. The member sees “Waiting for main to review.” |
| 8 | While member is offline, main edits Rice's minimum and member edits its name; push. | Review shows both fields and bases; accepting the name preserves main's minimum. No whole-row overwrite. |
| 9 | Both edit Rice's minimum, then member pushes. | Side-by-side current/main and member values; explicit person choice. Recheck under lock before save; no clock-based winner. |
| 10 | Member adds one Stock in and one Stock out while main has added another movement; retry push. | Each distinct movement is shown and, if accepted, applied once through normal Stock rules; totals equal the resulting movements, with no copied cached total. An impossible Stock out remains pending with a reason. |
| 11 | Member counts a batch at 8 while main records Stock out before Review. | Review shows counted 8, observed amount/base and main's new amount and intervening movement. Stale count cannot auto-apply its old delta; fresh confirmation computes correction under a write lock. |
| 12 | Main deletes a linked person while member edits that person and adds a linked vehicle. | Review shows delete/edit conflict; dependent link cannot be accepted until the target is retained or repaired. Tombstone is not silently undone. |
| 13 | Member has an older or switched-off module; push a row and a cross-module link. | Affected row waits with “Waiting for compatible module”; unrelated valid rows can proceed only when dependency graph allows. Raw values stay out of unauthorized views. |
| 14 | Push a record with private fields while its grant says Private details Off; then switch the grant on deliberately. | Off: no private value leaves main or enters the member's copy, proposal or error. On: confirmation names local and backup exposure; only newly authorized sync material is sent, with an auditable grant change. |
| 15 | Main restores a backup and then presses Undo restore while member has an offline edit. | Sync pauses and epoch changes at each operation; stale cursor/push does not replay. The offline edit is kept for an explicit rebase decision. Revoked keys remain dead. |
| 16 | Member is away long enough for log pruning. | Main requests a fresh checked snapshot, not an incomplete delta; member's unsent edits remain separately reviewable. |
| 17 | Export a USB bundle; tamper with it, import it twice, try it on another household, then lose its USB drive. | Tamper/wrong household/replay refused before Review; first valid import creates one waiting request. File contains authenticated ciphertext and no raw key or plaintext database. |
| 18 | Revoke a lost member, then attempt old-network and USB sync. | Both paths refuse future exchange; main says earlier copies may remain on lost device. Existing accepted history remains. |
| 19 | Move main to a headless home server; start old main again. | Exactly one main identity accepts pushes. Members must verify and pin the new identity; old main cannot silently resume as authority. Backups and admin path work without a desktop browser. |
| 20 | An incoming row contains HTML, a fake instruction, an unknown global link, an oversized payload, or duplicate operation ID. | Text is displayed as data, not run; link and size are refused plainly, no partial write or secret in response; duplicate returns prior decision. |

Run these on two clean Windows computers and one offline USB exchange as well as automated two-device fixtures before enabling sync. Include a forced clock skew and an old module version. A security review must try a stranger on the private network, stolen member key and lost laptop.
