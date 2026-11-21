# First phone-member screens, in words

Designed **21 November 2026** for batch 19 item 87. These are proposed screens, not a shipped phone app. The phone is a **member** under decision 0089: it reads the last accepted copy from main, saves its own work offline, and sends each change to main's Review. Only main can accept a change. Stage 1 (decision 0100) supplies stable IDs and a local change log; pairing and transfer have yet to be built.

The invented Smith household below uses kidney beans at **Kitchen › Pantry › Lower shelf**. Its last accepted copy has **13 tins** across two batches. Times, counts and people in this document are example data.

## Shared frame and language

One column at 320 px, with the household name, a **Sync status** button, a page heading, then content in reading order. Bottom navigation: **Needs attention**, **Stock**, **Changes**, **More**. Show status in words, never only a dot or color. Keep a persistent, nonblocking banner when offline: **Offline · Changes saved on this phone.** Under the heading, show **Main's records as of 20 Nov, 9:00 am** (using the household's local date and time preference); when a pull is old, add **May have changed on main.** A phone clock never makes a pending change look accepted. A pending badge says **2 changes saved on this phone**, separately from the accepted count. Sync status offers **Try syncing now**, the last successful pull, the main computer's name, and a plain error. It does not expose credentials or household facts in OS notifications.

Each form preserves entries during offline use, app suspension and a failed send. **Save on this phone** writes one durable operation; a double tap must leave one operation. A transfer acknowledgement changes its state to **Waiting for main**, not **Accepted**. A later accepted pull updates both the accepted record and the operation status. A rejected operation remains visible with the explanation and can be edited into a *new* operation only after the person chooses **Change and resend**. No retry quietly changes a record.

## 1. Needs attention

Top: **Needs attention**; below, **From main's last accepted records** and the as-of line. Show cards grouped by area as on the computer, but collapsed to one sentence each: for example **Kitchen · Drinking water is below the amount you chose** and **Kitchen · Kidney beans are below “Keep at least”**. Each opens the accepted item or the relevant phone action. If medical details occur here, show the neutral card **Medical item needs attention**; a deliberate **Show details** action reveals safety detail in the app. Keep that detail out of previews, notifications, recent-app snapshots where the platform permits, and ordinary status text.

Below a divider, **On this phone** shows **2 changes saved here** or **2 changes waiting for main** with a **See changes** link. These are work states, not resolved warning counts. If the last pull is stale, place **This list may have changed on main** above the cards. Empty accepted state: **Nothing needs attention in the last records received from main.** Offline empty state adds **Connect to check for newer records.** Never say **All ready** while out of date or because a phone action might fix a warning.

Computer features omitted here: the whole household dashboard, editing all modules, main-only approvals, and any new readiness calculation based on unsent work. A member's Needs attention list is a snapshot with its age attached.

## 2. Stock in and out

Entry from **Stock** or an item: **Stock in and out**. Show **Find an item** search over existing accepted items, then a selected item heading and **Choose a batch** list. Each batch row includes its distinguishing date, amount and full place path; for example **Kidney beans · Use by 20/05/27 · 8 tins · Kitchen › Pantry › Lower shelf**. Where two batches have the same date, also show their saved batch name or stable short identifier so the choice is unambiguous. If there is no eligible batch, say **No batch to choose. Add or correct batches on the main computer.** Do not silently pick the oldest or invent a date.

After selection: **What happened?** with **Stock in** and **Stock out** choices; **Amount** numeric field with the item's fixed unit displayed beside it; **When** prefilled with today's household date but editable; **Reason (optional)**. Show **Accepted on main: 8 tins in this batch · received 20 Nov, 9:00 am**. Button: **Save on this phone**. On save: **Saved on this phone. It will wait for main to review.** Link: **See change**. If online, transfer may start, but success copy still says **Sent to main for review**, not **Added to Stock**. For a locally known shortfall: **This batch only has 8 tins in the last records from main. Enter 8 or fewer, or check main for newer changes.** Main validates against its current count again; if it differs, its Review must offer a human resolution, not apply a negative balance.

Computer features omitted: creating a new Stock item or batch, editing its place or use-by date, direct live Stock movement, receipt/import flows, and approval of another member's movement. Those require separate designed phone flows before becoming available. Item search is over the last accepted pull, so a newly created main item may require a pull first.

## 3. Count this batch

Enter from one selected existing batch, never from a whole item total. Heading **Count this batch**. Read-only context: **Kidney beans**, **Use by 20/05/27**, **Kitchen › Pantry › Lower shelf**, **Last accepted count: 8 tins**, **Received from main: 20 Nov, 9:00 am**. Field **I counted** with **tins** beside it; optional **When I counted** and **Note**. Under the field: **Main will compare this count with any newer movements before it is accepted.** Button **Save count on this phone**. Confirmation **Count saved on this phone · waiting for main to review.** The payload is observed quantity, batch ID, observation time and accepted base revision, not a precomputed `+/-` correction. Main must handle intervening movements and may ask for a recount; the phone never silently adjusts the accepted quantity.

When a count is pending, show **Your count: 6 tins · waiting for main** next to **Accepted on main: 8 tins**. Do not replace the latter or clear a low-stock warning until main accepts and the phone pulls that result. If the batch disappeared or changed while offline, show **This batch changed on main. Your count was saved; ask the person at main to review it.** Do not retarget the observation to another batch.

Computer features omitted: the computer's immediate correction preview and write, editing batch metadata, resolving an intervening movement, and accepting the resulting correction. The phone is an observation collector here.

## 4. Changes waiting on main (member Review)

Bottom label **Changes** opens heading **Changes waiting on main**. A summary uses distinct counts: **2 saved here · 1 waiting for main · 1 needs your attention**. Rows identify action, item/batch, time and status, e.g. **Stock out · Kidney beans · 2 tins · Saved on this phone**. Group statuses: **Saved on this phone**, **Sending**, **Waiting for main**, **Accepted on main**, **Rejected on main**, **Needs rework**. Accepted rows show the main acceptance time only after an accepted pull. Rejected and needs-rework rows show main's reason in plain words and **Change and resend** where editing is possible; **Discard this change** requires confirmation and affects only an unsent or rejected local operation. A staged request already on main cannot be withdrawn by deleting the phone row; say **Ask the person at main to reject this change**.

Empty state: **No changes from this phone are waiting.** Offline state: **Changes are saved here. They will be sent when this phone can reach main.** A failed send shows **Could not send · Your change is still saved here** and **Try again**. If main has accepted the change but this phone has not pulled the result, continue showing **Waiting for main · Last checked [time]** rather than guessing. A row can show a nonprivate reference to a dependent group, but must not expose another member's staged details or medical safety text in the list. No **Accept**, **Reject**, **Accept all**, helper key, or incoming-approval controls appear on a phone member.

Computer features omitted: main's full Review queue (helpers, imports, receipts, members), group approval/rejection, audit detail and household-wide change management. The phone shows this member's outgoing work and outcomes only.

## Cross-screen checks for the first prototype

1. At 320 px and large text, every heading, full place path, unit, primary button and state word is readable without horizontal scrolling; focus and screen-reader order follow the visual order.
2. With the phone offline, save an in, out and count, force quit, reopen: each form has one durable operation and accepted counts remain unchanged. Repeated taps and send retries create no extra operation on main.
3. With a pull six days old, Needs attention says when records were received and may have changed; a pending Stock in does not clear its warning or claim the household is ready.
4. Accept one operation, reject another and leave a third staged on main. After a pull, the phone shows three distinct outcomes and keeps the rejected content available for a deliberate edit.
5. Change a batch on main before an offline count arrives. Review on main sees observed amount and base revision; phone neither computes a correction nor silently switches batches.
6. Turn on a medical warning and local-only fields. Reveal safety detail only through Show; search UI, list preview, notification, status, logs and outgoing payload contain no local-only value. Vehicle registration and access instructions remain on their origin device.
7. A phone member cannot open main's Review approval, helper key, import, backup/restore or server settings through navigation, deep link or offline cache. Test Android TalkBack and iOS VoiceOver on real devices before release.

## Basis

Checked **21 November 2026**: decisions [0089](../../../docs/decisions/0089-household-sync-main-and-members.md) and [0100](../../../docs/decisions/0100-sync-stage-1-stable-ids-and-change-log.md), the existing [phone proposal](PHONE.md), shipped Stock labels and computer Count/Review/Needs attention templates. Those are product and implementation references, not evidence of a running mobile app. See [NOTES.md](NOTES.md) for the missing core work.
