# Household sync: decisions, core work and sources

Checked **19 November 2026**. This is item 69 for Lane A's decision 0089. Corey's newer main/member push–pull brief in `docs/WORKSTREAMS.md` supersedes the build order and automatic merge assumptions of `docs/plans/household-sharing.md` option C and decision 0081; its warnings about local SQLite files and optional sharing still apply. No code, network listener or key scheme is shipped by this draft.

**20 November item 68 follow-up:** Corey accepted main/member sync in decision 0089; shared-folder option A is unselected. The [option A ready-check](../../reports/2026-11-20-sharing-option-a-ready-check.md) lists blockers if it is ever reconsidered: a whole copied database carries fields 0089 keeps local, cloud-file leases cannot provide an atomic cross-device lock, and current Review cannot reconcile two changed databases. That route needs a new product/privacy decision, a safe exchange and recovery design, and a full read-only write gate before it can be built. Do not use a shared SQLite file as a shortcut around the chosen record-level sync stages.

## What Corey needs to choose

1. Is the first supported pair two Windows computers, with main expected to be on whenever they sync? A phone needs another client design.
2. Are modules chosen for each member, or does membership always mean a full copy? If modules are chosen, should a member be allowed to push edits to modules it cannot pull? Proposed: no.
3. May a member receive private fields? Proposed: Off by default with a separate confirmation and clear warning that its local database and backups then hold them. If Off, should private fields in mixed records remain main-only forever? Proposed: yes, and absence never clears them.
4. Must main approve **every** incoming row, or may a household later permit automatic acceptance of conflict-free rows? Item 69 assumes every row reaches Review. Start there.
5. When main restores an older backup, should members be re-paired, or can a controlled rebase after comparing epochs keep their keys? Proposed: pause and require an explicit rebase; never make the restored snapshot an automatic delete wave.
6. Is a private network the only online transport for v1, with encrypted USB bundles as a later milestone? Proposed: yes. Which supported setup is acceptable for Corey's household: Tailscale or a self-managed alternative?
7. How long should main retain accepted changes and tombstones for a member that never returns? Proposed: warn before retiring a device; a returning member starts with a new snapshot and reconciles its outbox.
8. Should a headless home server be a supported v1 main or a later milestone? It needs a separate admin and recovery path.

## Transport choice and limits

| Option | Household cost | Network and trust consequence |
|---|---|---|
| Tailscale (pilot recommendation) | Install and join a private tailnet on both computers; hosted control service | WireGuard-based private device network, with relay fallback. Main must still authenticate the exact Dashboard process and member. Tailscale HTTPS certificates may publish tailnet/device names to public Certificate Transparency; prefer app-owned pinned certificate and a neutral device label. |
| Headscale with Tailscale clients | Someone runs and maintains a separate control server | Self-hosts coordination but not Dashboard main; the home main must still be awake and reachable through the private network. More setup and recovery work. |
| Manual WireGuard | Someone distributes peer keys, addresses and routes | Encrypted private IP path, but no household pairing/configuration interface supplied by WireGuard itself. Highest setup burden. |
| ZeroTier | Join and authorize both devices on a virtual network; commonly hosted controller | Encrypted virtual LAN, possibly via relay; still needs Dashboard's own authentication and pinned main identity. |

No public router forwarding, public reverse tunnel or Tailscale Funnel in the proposed product. Tailscale Serve is tailnet-only but its HTTPS naming/privacy trade-off should be checked before choosing it. A private device network can still include a compromised device. The sync door needs its own authenticated protocol and an app-owned TLS certificate bound to the selected private IP. The precise Windows firewall, certificate generation, interface-change and process-supervision behavior remains **unverified** and needs real-device tests before a promise to a household. No design should make the present local helper API remotely reachable by accident.

## Core work, in household terms

| What the household would see | What core must build |
|---|---|
| “Pair a computer” with a one-use invitation, main identity check and a named device that can be turned off | Separate member-key namespace, one-time display/fingerprint/revocation outside backups as in 0066, independent TLS identity, mutual nonce proof, exact Host and private-interface binding, replay/size/rate limits. Member keys must never authorize helper routes. |
| “Syncing with …”; records stay available offline | Global row and link IDs, durable per-device outbox, accepted-main revision/cursor/epoch and an atomic change log beside `core__audit`; first-pull snapshot and later delta apply with checked backup. No direct SQLite-file sync. |
| “Changes from Sam's laptop” on Review with side-by-side rows | Separate sync request staging for create/update/delete and private fields, dependency graph, per-row Accept/Reject, under-lock revalidation, idempotent operation/decision storage, accepted-change fan-out. Helper proposal tables (0068) are add-only and grant-filtered; they are not enough. |
| “Counted 8; main now says 6” | Stock movement global IDs, exactly-once normal-path application, no replicated cached total, and an observation-based stocktake action that computes its correction at acceptance after showing intervening events (0070). |
| “This part needs updating before it can sync” | Module and exchange-schema versions, migration of queued operations, per-module stop/retry, link safety and no cross-module bypass (0055, 0069, 0074). |
| “Sync paused after restore” | Restore/Undo gate (0079) integrated with sync pause, new epoch, rebase flow and key revocation that survives restoring an old database. |
| “Save an offline bundle” | Versioned authenticated-encrypted format, a dedicated pairing/bundle secret, safe key rotation/recovery, tamper/replay checks and no plaintext temp copy. Python's standard library has no suitable AEAD; dependency requires its own approval and decision under AGENTS.md. |
| “Move main to a home server” | One-authority handover protocol, portable headless launcher, supervised start/stop, local admin and backup/restore path, private-interface binding and secure certificate re-pinning. |

The current audit has local integer IDs and changed-row JSON, not global identities, a durable cursor or a versioned portable protocol (`src/dashboard/core/migrations/0002_audit_history.sql`). Stock movements update batch/item quantities (`modules/stock/tables.toml`), and the shipped count action checks and writes a correction together (`src/dashboard/core/records.py`). Restore swaps a checked SQLite copy with an Undo path and keys outside backups (`src/dashboard/core/restore.py`). These are useful foundations but cannot by themselves provide safe sync. Preserve the current module migration boundary (0055) when applying remote changes.

## Staged build and rough size

These are **relative sizes, not delivery estimates**. Stop after each stage for its acceptance and security gate.

| Stage | Size | Reviewable result and gate |
|---|---|---|
| 0. Rules and threat model | Small | Corey answers the questions above; decision 0089 records privacy, transport and Review authority. Independent security review of remote boundary. |
| 1. Local identities and exchange log | Large | Global IDs/backfill, schema versions, main revisions and outbox; two local copies exchange synthetic changes offline with no listener; migration and restore tests. |
| 2. Review and merge engine | Very large | One request per push, field conflict/dependency UI, Stock events/counts, delete/edit, exactly-once decisions; no network yet. Two-device and skewed-clock fixtures pass. |
| 3. Private-network pairing and pull/push | Large | Separate member keys, pinned HTTPS, listener auto-off, checked snapshot/deltas, mode badge and recovery messages. Independent security review plus two clean Windows devices. |
| 4. Offline encrypted bundles | Medium | Same protocol through authenticated files; tamper/replay/lost-key tests and vetted crypto dependency. |
| 5. Headless main handover | Large | Home-server runbook, one-authority handover, backups, local admin and failover drills. |

## Threats to test before release

- **Stolen laptop:** revoke its member key, but copied records and backups remain on its disk; recommend device storage encryption and say exactly what was copied. Never promise remote erasure.
- **Lost or copied key:** a member key is scoped to one device/household and can be revoked without restoring a database; rate limits and TLS pinning reduce misuse, but an attacker with both key and device access may act as that member until revocation.
- **Someone else on the private network:** cannot use the listener without a member grant and main identity check; malformed requests, wrong Host, replay and flooding must fail without leaking private field names or values.
- **Member mistakes or hostile record text:** everything pushed waits for a person, is displayed as data, and is validated again at acceptance. A member cannot call Restore/Export/Settings or helper Accept through sync.
- **Confused main/restore:** old main and new server cannot both accept pushes; epoch mismatch pauses exchange rather than replaying prior operations or resurrecting deleted rows.

## Sources and scope

Official sources checked **19 November 2026**: [Tailscale concepts](https://tailscale.com/docs/concepts/what-is-tailscale), [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve), [Tailscale HTTPS certificate privacy](https://tailscale.com/docs/how-to/set-up-https-certificates), [Headscale](https://headscale.net/stable/), [WireGuard](https://www.wireguard.com/), [ZeroTier setup](https://docs.zerotier.com/start/) and [protocol](https://docs.zerotier.com/protocol/), [SQLite network filesystem warning](https://www.sqlite.org/useovernet.html), and [SQLite backup API](https://www.sqlite.org/backup.html). Network-product behavior is cited from these pages; Dashboard-specific rules above are proposals, not vendor claims. The earlier household-sharing plan's `Sources (from memory)` section is not relied on for protocol claims. Verify certificate and Windows firewall behavior on the exact portable build before publishing a setup guide.
