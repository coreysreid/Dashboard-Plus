# Let a helper read one private detail: later design

Checked **18 November 2026** against [the Agent API v1 plan](../../../docs/plans/agent-api-v1.md), [decision 0059](../../../docs/decisions/0059-private-details-only-when-asked.md) and the shipped People and Vehicles sensitive fields. This is a **future design**, not an exception to v1: v1 always reports `private_details: false` and never shares sensitive columns. The current private browser Show button authorizes only the person using that local page; it must not grant a helper anything.

## A household's choice in Settings

From **Settings → Helpers → [helper name]**, keep **Private details: never shared** as the default. A future **Let this helper read one private detail** action opens a separate review. It lists only the records and fields declared `sensitive`, without preloading their values. The person may use their own Show control to verify a selected field. It requires that the helper already has normal access to that module; a private grant cannot add a module or let the helper suggest private values.

Use this exact review text for a made-up People detail:

> **Let Pet diary helper read one private detail?**  
> **Detail:** Example Person · Important details · Detail  
> **Access:** one read within 15 minutes. Then it ends.  
> This helper can send what it reads to the service running it. If that service is online, the detail may leave this computer. Dashboard Plus cannot take it back after the helper has read it.  
> The helper cannot change this detail or see other private details. You can turn this access off in Settings at any time.  
> [Allow one read] [Cancel]

The helper name shown is the registered key owner, not text from a proposal. Possession of that shared key identifies the grant in the app; it cannot prove which person or service actually ran the helper. Do not quote the private value in the review page, URL, notification or audit. If the person has not deliberately selected a field, leave **Allow one read** disabled. The app must not ask for this grant during ordinary setup or while accepting a helper suggestion.

After confirmation: **“Pet diary helper may read this one detail once, until 3:15 p.m. today. No private detail has been sent yet. Turn off access.”** Use the household's local time/date display and show the exact expiry. Settings lists active grants by helper, module, record and field label, status **Not read / Read / Expired / Turned off**, last-read time and **Turn off access**. When revoked: **“Access to this detail is off. The helper cannot read it again. A copy it already received may still exist outside Dashboard Plus.”** Turning off the helper key ends all its grants immediately.

## API and lifetime boundary

A new, dedicated read route should take an opaque grant ID, for example `GET /api/v1/private-grants/{grant_id}/value`. That route is **proposed**, not part of [v1 OpenAPI](openapi-v1.json). It requires the normal bearer key and local Host/Origin guards, verifies the caller is the exact granted helper, its module remains allowed/enabled, the record is current, the field remains sensitive and unchanged from the approved version, the grant is unrevoked/unexpired and its one read remains. Consume the grant and log the successful read in one transaction before sending only that one value. If transmission fails after consumption, the person must issue a new grant; this is safer than a retry that may reveal it twice. Do not accept cookies, query keys or a broad `include_private=true` on ordinary records routes.

A grant is bound to **helper ID/key identity, module, table, record ID, field, record-field revision and one read**, with a hard 15-minute expiry. Editing, deleting or restoring the record invalidates it; the household reviews the new value before another grant. If the helper is revoked or its module switched off, the grant stops. Restoring an older database backup must not revive a consumed or revoked grant: keep a durable revocation/consumption marker outside the restorable DB or fail closed on mismatch, as the v1 key design does. Do not store a copy of the private value in the grant row or its audit event. A direct guessed grant ID, another helper's grant or an expired grant gets a generic refusal that does not confirm the detail exists.

Normal `/tables`, `/records`, `/attention`, `/batches`, Review, sheets and the MCP tool list still omit private values. A future connector would need a **separate opt-in tool and warning**; its eight v1 tools remain nonprivate. No helper may propose, amend, accept, export or search private fields through this read grant. The grant does not make ordinary names, free-text notes or linked IDs private; module authors and [the abuse catalogue](ABUSE_CASES.md) still need to prevent those leaks.

## What is logged, and what cannot be undone

Audit **grant made**, **read**, **expired** and **turned off** with person/helper identity, module/table, record ID, field name, grant ID and time. Record denied reads where the helper can be identified, without saving the attempted key or field value. Show the household the last read and allow it to inspect this history. Do **not** write the private value, a hash of it, or a copy to the grant, log, error, notification or proposal. API responses use `Cache-Control: no-store`, but the helper or its provider may keep a copy. Revocation prevents **future** reads only; it cannot erase what was already sent. If a household wants a detail removed from the app's own history/backups, that is the separate [erase design](../private_erase/NOTES.md), not this grant.

## Core needs

Core currently has no per-field grant store, one-read transaction, field revision, API read route, grant expiry/revocation ledger, private-read audit or Settings screen for this. Its normal record `updated_at` is second-precision, so it cannot alone bind a grant to one field version. Require a monotonic revision for the approved field and record; do not publish or log a guessable digest of the private value. The key-file and database restore behavior must be designed together so an old backup cannot reactivate a grant. Do not implement a UI-only toggle or widen v1's module grant to include all sensitive fields.
