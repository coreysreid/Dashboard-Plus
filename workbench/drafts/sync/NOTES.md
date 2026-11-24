# Household sync: decision 0089 delta, core work and sources

**Stage 1 shipped, checked 21 November 2026:** Decision 0100 now supplies permanent IDs, revisions, a filtered local change log and offline snapshot/check readers for 36 record tables, including Utilities. [STAGE1_ACCEPTANCE.md](STAGE1_ACCEPTANCE.md) refines the earlier design's twelve checks into exact fixtures and assertions, and names gaps in the 19 current automated tests. The deliberate People-detail replacement action, pairing, member keys, network boundary, receiving withheld-value behavior and conflicts remain stage 2 work; no household records travel yet. Utilities account number/notes stay local, and User 1 confirmed Pets microchip travels under decision 0089.

Updated **20 November 2026** against accepted `docs/decisions/0089-household-sync-main-and-members.md`, `docs/WORKSTREAMS.md` batch 17 item 70 and the shipped People, Home layout and Vehicles tables. This remains a design; no sync listener, key scheme or network exchange has shipped. The earlier item 69 draft assumed optional module grants and a private-details switch. Decision 0089 settles those product choices.

**20 November item 68 follow-up:** User 1 accepted main/member sync in decision 0089; shared-folder option A is unselected. The [option A ready-check](../../reports/2026-11-20-sharing-option-a-ready-check.md) lists blockers if it is ever reconsidered: a whole copied database carries fields 0089 keeps local, cloud-file leases cannot provide an atomic cross-device lock, and current Review cannot reconcile two changed databases. That route needs a new product/privacy decision, a safe exchange and recovery design, and a full read-only write gate before it can be built. Do not use a shared SQLite file as a shortcut around the chosen record-level sync stages.

## What changed from item 69

| Earlier draft | Decision 0089 rule and work needed |
|---|---|
| A member could choose modules and turn private details on | A member receives the full copy of parts switched on. There is no v1 private-details grant. A per-column travel classification filters both directions, including bundled exchange and logs. |
| All `sensitive` fields treated alike | Medical safety details in `people.important_info.detail` for allergy, condition, medication, care_need and dietary travel, remain behind Show and print on the emergency sheet. Access instructions, Home layout access_details and vehicle registration do not. `kind=other` defaults local until classified. This is a conditional field rule, so a simple `sensitive` Boolean cannot implement it. |
| Tailscale recommended, with Headscale/ZeroTier comparison | Tailscale and self-run WireGuard are initial network adapters. A third adapter can be added later. Exchange and member authorization do not depend on provider. Headscale and ZeroTier are research context, not v1 commitments. |
| Review engine before network pairing | Stage order now follows 0089: 0 security review, 1 IDs/revisions/log, 2 pairing and pull, 3 push to Review, 4 conflicts, 5 encrypted USB, 6 home server. |
| Windows desktop first, headless main a later step | Two computers first, with macOS support designed next. Android and iOS join as members in a later phone milestone; shared protocol and data rules must work without a desktop browser or Windows paths. Home server remains stage 6. |

The [option A ready-check](../../reports/2026-11-20-sharing-option-a-ready-check.md) still applies if shared-folder sync is reconsidered: a copied SQLite file would carry local-only fields, cloud-file leases cannot make a cross-device atomic lock, and Review cannot reconcile diverged databases. It is unselected.

## Exact field policy needed in core

The only shipped `sensitive = true` columns checked on 20 November are `people.important_info.detail`, `home_layout.{exits,shutoffs,equipment,meters}.access_details`, and `vehicles.vehicles.registration`. The People detail rule depends on its `kind`, so the exchange schema needs an explicit *travels to members* rule per private column, with a discriminator and fail-closed default. Module authors must classify new private columns before they are eligible for sync. Ordinary columns that could contain secrets in free text (for example People notes) need product wording and a content decision; schema flags alone cannot prevent someone typing a password into an ordinary field. Decision 0089 deliberately does not promise a vault.

The filter belongs before portable audit/change-log entries, outbox serialization, Review staging, snapshot/delta response and USB encryption, on **both** main and member. No raw value, derived hash, length, search token or diagnostic sample of a local-only field crosses. A missing or local-only marker does not overwrite the receiving copy's field. Main should avoid a record name or error that reveals the value. Core must define transition behavior when a `people.important_info` row changes kind between medical and access, including an already-synced medical value: ordinary sync cannot retract copies already made. Require explicit user wording and a migration/reconciliation rule before shipping. Distinguish the placeholder from true blank/null and from a not-yet-pulled row. The member's own local-only value must remain available on that member after a snapshot or restore. A member backup/export may include its own data and needs its separate existing privacy warning; sync must never treat it as a data exchange bundle.

## Pluggable private-network boundary

A network adapter reports the selected private interface/address, peer reachability and address changes. The sync core owns the one-use invitation, member key, app-owned pinned TLS identity, mutual proof, Host allowlist, rate/size limits, cursor and revision format. Store provider choice and endpoint separately from record data; do not put Tailscale names, WireGuard peer keys or IPs into portable operations. Initial setup offers **Tailscale** or **self-run WireGuard**; the adapter contract admits a third later without a protocol migration. A provider change closes the listener and requires endpoint and identity verification before resuming at the existing cursor. It must never silently bind a public or wildcard address. The app and helper API remain loopback-only. Phone membership later needs a mobile-capable private-network client or OS integration, background-transfer limits and protected local storage; do not claim those are solved by the desktop adapter.

Tailscale's hosted coordination and WireGuard's manual peer setup have different household costs. Neither authenticates a Dashboard member by itself. No router forwarding, public tunnel or Tailscale Funnel is part of v1. The exact Windows/macOS firewall, certificate, mobile VPN and interface-change behavior needs real-device verification before publishing setup steps.

## Core work and stage gates

| Stage | Relative size | Reviewable result and gate |
|---|---|---|
| 0. Remote-boundary security review | Small | Independent reviewer tests trust boundary, private-field filter, listener binding and abuse cases before any network milestone ships. Item 71 provides the brief. |
| 1. IDs, revisions and local change log | Large | Stable global IDs, versioned exchange schema, outbox and accepted revisions; per-column travel classification and no local-only value in portable log; offline two-copy fixtures, restore and migration tests. |
| 2. Pairing and pull | Large | Separate member keys and pinned identity, Tailscale/WireGuard adapters, private bind, checked snapshot/deltas, backup before apply, same-version gate and two-device tests. Independent security gate before release. |
| 3. Push to Review | Large | Each incoming row waits for a person; idempotent staging/decisions and ordinary records untouched before acceptance. Existing helper proposal staging is add-only and insufficient for general edits. |
| 4. Conflicts | Very large | Side-by-side field edits, Stock movement/count semantics, deletes and links, revalidation under lock, skewed-clock fixtures. No automatic last-writer result. |
| 5. Encrypted USB bundles | Medium | Same filtered exchange as network, authenticated encryption, replay/epoch tests and a separately reviewed crypto dependency. |
| 6. Home server main | Large | One-authority handover, managed process, local admin, recovery, backups and re-pinning. |

The current audit uses local integer IDs (`src/dashboard/core/migrations/0002_audit_history.sql`), Stock count uses a checked correction (`src/dashboard/core/records.py`), and restore has an Undo path (`src/dashboard/core/restore.py`). They are foundations, not a portable protocol. Preserve decision 0055's module migration boundary. Restore on main pauses sync and changes epoch; a member away beyond log retention gets a fresh snapshot while its unsent edits remain separate. Each accepted incoming row reaches Review. The first release is two computers; the wire format, credentials and revision semantics must allow macOS and phone members later.

## Remaining design questions, not reversals of 0089

- How will the household classify `kind=other` and ordinary free-text fields, and what should happen when a previously travelled medical row is reclassified as access?
- Does a placeholder disclose that a local-only value exists, or should the receiving copy show only a generic local-storage hint? How will a screen reader read it without exposing content?
- What is the exact key rotation, device retirement, log retention and rebase procedure after restore? How do provider switches preserve pinning?
- Which vetted AEAD dependency, key recovery and bundle metadata policy will stage 5 use?

## Sources and scope

Decision and shipped schemas checked **20 November 2026**. Official network and SQLite sources checked **19 November 2026**: [Tailscale concepts](https://tailscale.com/docs/concepts/what-is-tailscale), [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve), [Tailscale HTTPS certificate privacy](https://tailscale.com/docs/how-to/set-up-https-certificates), [WireGuard](https://www.wireguard.com/), [Headscale](https://headscale.net/stable/), [ZeroTier setup](https://docs.zerotier.com/start/), [SQLite network filesystem warning](https://www.sqlite.org/useovernet.html), and [SQLite backup API](https://www.sqlite.org/backup.html). Vendor behavior comes from these pages. Dashboard protocol rules above are design proposals, not vendor claims. Firewall and certificate behavior remains unverified on the portable build.
