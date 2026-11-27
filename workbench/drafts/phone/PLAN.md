# A first phone app for a household

Batch 24 item 127. Planned **27 November 2026**. This is a plan for iPhone and Android, not a phone app that can be installed today. The main computer still has only local sync preparation: permanent record IDs, revisions, a filtered change log, and **What your other computers get**. Pairing, transfer and phone storage have not shipped.

## What a household would see first

1. **Add this phone** on the main computer shows the chosen lists and details **before** the first copy. A second person checks the same choices on the phone, compares the main computer's identity, and approves the pairing on main. The first copy includes older records allowed by those choices, so the screen says that plainly. A helper key cannot pair a phone. The household must set up a supported private device network; the app must not instruct them to open a router port.
2. **Needs attention** opens from the last accepted copy, read only. It shows when that copy arrived and says **May have changed on main** when old. Pending phone entries sit in a separate **Changes waiting on main** count; they do not clear a warning or make a readiness claim. A warning derived from a list kept on main must not reveal that list's records on the phone. Private detail stays behind **Show** and out of notifications and ordinary previews.
3. **Quick entry** has six named actions: **Food put out for a pet**, **Record a dose given**, **Weigh a pet**, **Stock in**, **Stock out**, and **Mark done** for an existing Garden or Home care job. The person chooses an existing subject or Stock batch and sees the unit, household date/time and place where relevant. **Save on this phone** writes one durable local operation. **Sent to main for review** means only that transfer succeeded. Main's Review accepts or refuses each operation; the phone shows the later outcome after a pull. A planned dose is never silently turned into a given dose, and no blank day is called missed.
4. **Changes** separates Saved here, Sending, Waiting for main, Accepted, Rejected and Needs rework. It gives the reason without exposing another member's private entry. A double tap, retry or reconnect never creates a second feeding, dose, movement or Mark done.
5. **Sync status** shows main's name, last successful pull, unsent count and a plain paused reason. **Turn off this phone** stops future exchange and explains that already copied records may remain on it. On a lost phone, main can revoke the member key; revocation cannot remotely erase an offline phone.

The existing [first-screen copy](FIRST_SCREENS.md) covers Needs attention, Stock in/out, count and Changes. It needs the four new quick-entry forms above and the sharing-choice gate before it can be used as a complete phone specification. Count this batch is useful later, after main can review an observed amount against intervening movements; it is not a launch shortcut for Stock in/out.

## First build, in order

| Step | Household result | Gate before moving on |
|---|---|---|
| 0. Prove the exchange boundary | Nothing new on the phone yet. | Independent remote-boundary review from decision 0089; stable IDs and restore epochs from 0100; one protocol for computers and phones; protected member credentials distinct from helper keys. |
| 1. Pair and read | A phone sees only a dated accepted copy and a read-only Needs attention. | Short-lived one-use invitation, mutual identity check, private-network-only connection, exact module versions, consent preview and choice-aware first snapshot. Test revocation, interrupted copy and a restored main. |
| 2. Save offline | The six quick actions save locally and show a pending count, even in airplane mode. | Protected accepted store plus durable outbox, operation IDs, date/unit validation, crash and storage-full recovery, no secret or record text in logs or OS notifications. |
| 3. Send to Review | Main can accept or refuse each row; the phone learns the result. | Idempotent pushes, base revisions, link checks, Review staging, outcome pull, conflict and Undo behavior. No action may update main merely because it was sent. |
| 4. Widen and release | Both platforms can be installed and supported by a household. | Real-device VoiceOver/TalkBack, large text, lost-phone, backup/restore, two network adapters, store privacy, signing, distribution and update checks. |

Foreground **Try syncing now** is enough for the first version. Background delivery and notifications are separate work after the two operating systems prove they are reliable. Main has to be reachable for exchange; offline saving never implies an immediate household-wide update.

## Which information reaches a phone

Decision 0140 supersedes the older fixed travel list in [PHONE.md](PHONE.md). Main's **What your other computers get** choices govern every list and detail; defaults come from each module's travel rules. Medical details, doses, prices, money back, registration and other allowed private facts can travel when the household chooses. A private choice that starts sharing needs the existing explicit confirmation. Decision 0141 removes boxes for codes, full card and bank numbers, ID copies and similar fraud-grade detail; a phone must use the same guards and never offer such a box. The old Home layout codes field is retired in favour of a guarded **Who to ask, or where the code is kept** hint. Account and policy references use last four digits only.

The pairing preview must say both what is shared now and what the first full copy will contain from earlier records. A later choice to share more must send an explicitly reviewed full copy of that list or detail; a future-only change log cannot reconstruct older records kept here. A tighter choice immediately stops future lines, but the screen must say that a copy already on another phone cannot be recalled. If a shared record points to a record kept on main, the phone shows **Linked detail is kept on the main computer** rather than guessing a name or exposing an ID. Changing a phone's sharing permission is a main-computer choice, not a hidden side effect of Quick entry.

Before offering an action, the phone checks that its subject and fields are available under the current sharing choice. For example, it cannot record a dose against a medication detail it has not received, or send a Stock movement for an unknown batch. It says **This list is kept on the main computer. Choose to share it there before recording it on this phone.** It never silently drops a required private field to make a request fit. Optional local-only detail typed on the phone stays only there and is not smuggled through Review, a change log, an error or a backup sent to main. The core needs an explicit contract for such fields before this flow ships.

## Quick-entry boundaries

| Action | Phone asks | What main must check on Review |
|---|---|---|
| Food put out for a pet | Pet, food, amount if known, unit, when; **Food put out is not food eaten.** | Pet and food links, local-day grouping, possible repeat and unit. Do not silently subtract Stock; that is a separate household choice. |
| Record a dose given | Person, one of that person's medicine details, when, giver and optional amount, behind Show. | Same-person medication link, repeat warning, private fields, household day; no dose can be inferred from a plan or a blank calendar day. |
| Weigh a pet | Pet, number, unit and when; allow an earlier day. | Valid unit, exact pet, same-time possible repeat and honest chart point. |
| Stock in / Stock out | Existing item and batch, amount in its fixed unit, when and reason. | Current batch, no negative accepted balance, duplicate operation, and person-chosen batch. Do not invent a purchase price or use-by date. |
| Mark done | Existing Garden or Home care job, done day and any fields that job's action asks. | Current job state, not-before rule, one press/one operation, atomic Home care work-done row and next-date change. |

The phone shows the accepted count or state beside a pending change, never overwrites it locally. On rejection or an intervening edit, keep the person's saved words and offer **Change and resend** as a new reviewed operation. No phone member gets main's Accept or Reject controls, a helper key, import, main backup/restore or a raw database share.

## Approach and ongoing cost

| Approach | What it helps | Cost and uncertainty |
|---|---|---|
| Installable web app | One web UI and no store account for direct installation. Service worker can keep an app shell and browser storage can hold data. | Safe, long-offline record storage, credential protection, private-network access, browser eviction and background behavior need proof on real iPhone and Android devices. A browser-held member key is a serious boundary to review. |
| Shared cross-platform packaged app **(first prototype choice)** | One shared client and protocol, with platform adapters for a protected local store, secure key storage and foreground sync. | Still two signed releases, store reviews, real-device tests and OS maintenance. Flutter is a candidate for a prototype, not an approved dependency or final framework choice. iOS builds need Xcode and a Mac build path. |
| Separate native apps | Direct platform storage, accessibility and networking controls. | Two implementations and release pipelines must remain protocol-identical; likely the most engineering and review time. Use if the shared prototype fails privacy, offline or accessibility gates. |

For store distribution, Apple Developer Program membership is **US$99 per year** and Google Play registration is **US$25 once**, before any regional tax or other costs; recheck the checkout in the intended country before paying. Google personal accounts can have extra testing and device-verification requirements. Both platforms need signing, policy and privacy disclosures, updates and support. A private-network provider can add a subscription or administration cost. The main computer still has to be on for exchange. A PWA avoids store accounts but does not remove the safe-sync work. No app-store account or framework should be bought or added just to approve this plan.

## Risks and release checks

1. Pair two invented households in turn; expired or reused invitation, wrong fingerprint, helper key, wrong household, changed module version, revoked phone and public-network endpoint all refuse before data transfer. Test Tailscale and self-run WireGuard paths without making either the protocol.
2. Preview a choice of **Only on this computer** before pairing, then change it to Shared after pairing. Verify the first copy, derived Needs attention lines and later deltas omit it; the later full-copy action asks about historic private records, and Undo stops future transfer without claiming to erase an earlier phone copy. Check locally kept link targets stay neutral. Repeat with medical detail and money back, and with retired codes and last-four references.
3. In airplane mode save one feeding, dose, weigh-in, Stock in, Stock out and Garden/Home care Mark done. Force quit, restart and double tap. The outbox still has exactly six distinct operations; main has no accepted changes. Reconnect twice: each appears once on Review. Accept, reject and conflict one each; verify the phone's words and accepted copy after pull.
4. Interrupt first copy, delta, send, app update and main restore. Fill phone storage nearly full. Neither accepted copy nor unsent operation disappears; a restore epoch never becomes a wave of deletes. Record clocks and time zones must not make a day or status appear accepted early.
5. Inspect the installed app's files, OS backup behavior, logs, crash reports, notifications, app-switcher image and network traffic for invented private sentinels, member keys and fraud-grade text. Use OS key protection and a deliberate at-rest/backup policy; a screen lock alone is not the policy. Test a lost phone that remains offline after revocation.
6. On real iPhone and Android devices test one-handed 320 px layout, large text, touch targets, VoiceOver/TalkBack, focus order, light/dark/high contrast and exact as-of words. Compare app-store privacy answers with what the installed build and any diagnostics actually transmit.

## Evidence and limits

Product basis checked **27 November 2026**: decisions [0089](../../../docs/decisions/0089-household-sync-main-and-members.md), [0100](../../../docs/decisions/0100-sync-stage-1-stable-ids-and-change-log.md), [0140](../../../docs/decisions/0140-sharing-permissions.md) and [0141](../../../docs/decisions/0141-no-fraud-grade-details.md); shipped Pet feeding, Medicine doses, Pets weigh-ins, Stock, Garden and Home care declarations; and the existing [phone proposal](PHONE.md). No phone, pairing or transfer was tested.

Official platform pages checked **27 November 2026**: [Apple Developer Program](https://developer.apple.com/programs/) (membership price), [Google Play developer registration](https://support.google.com/googleplay/android-developer/answer/6112435?hl=en) (registration fee and personal-account conditions), [Flutter iOS setup](https://docs.flutter.dev/platform-integration/ios/setup) (Xcode build requirement), [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/), [Google Android app signing](https://developer.android.com/studio/publish/app-signing), [Android Keystore](https://developer.android.com/privacy-and-security/keystore) and [web.dev offline data](https://web.dev/learn/pwa/offline-data). These describe platform mechanisms and distribution rules; none proves this proposed app will retain offline records, pair securely or pass store review. Those claims require the prototype and device checks above.
