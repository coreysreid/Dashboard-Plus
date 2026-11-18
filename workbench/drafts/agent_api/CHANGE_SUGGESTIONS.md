# Suggest a change to a record: later API design

Draft checked **18 November 2026** against [the v1 plan](../../../docs/plans/agent-api-v1.md), current `Records.update` and the earlier [Review words](../helpers/REVIEW_WORDS.md). V1 deliberately allows **new-record suggestions only**. None of the routes below ships or changes that boundary. A helper can never directly edit or delete a household record or accept its own suggestion.

## One worked example

In the invented Smith household, **Kidney beans** has **Keep at least 4 tins**. A Stock-scoped helper reads the current record and suggests **6 tins**. Stage only this patch:

```json
{"target":{"table":"stock__items","id":6,"revision":17},"before":{"minimum":4},"set":{"minimum":6},"why":"The household's invented paper note says to keep six tins."}
```

The exact `revision` is illustrative. The helper must first read the record through its grant; it may propose only known ordinary, editable fields. `set` lists changed fields, so omission means “leave it alone” and an explicit `null` means “clear this optional field.” Private, system, worked-out, file and ungranted link fields are refused. Quantity is worked out from batches and cannot be patched. The proposal remains in a separate queue; Stock and Needs attention do not change while it waits.

**Review card:**

> **Stock note helper suggests changing Kidney beans**  
> **Why:** The household's invented paper note says to keep six tins.  
> **Keep at least:** 4 tins now → 6 tins suggested  
> Nothing changes until you choose.  
> [Accept change] [Change then accept] [Reject]

The helper name is a verified label, while `why` is untrusted text displayed as text, never as a command or link. **Change then accept** opens only the proposed ordinary fields. If the person chooses **5 tins**, the second review reads **“Keep at least: 4 tins now → 6 tins suggested → 5 tins you chose.”** Primary button: **Save changes and accept**. On success: **“Changed Kidney beans. Keep at least is now 5 tins. Your change to the helper's suggestion is kept in history.”** The original 6, chosen 5, verified helper and deciding person remain distinguishable in proposal/audit history. The live row is attributed to the person's decision, not silently to the helper.

If a person changes Kidney beans to **5 tins** in another window before acceptance, disable the stale action and say **“This record changed since the helper looked at it. Keep at least is now 5 tins. Review the current values before accepting.”** Button **Review again** shows current 5 and helper's original 6; the person may accept/rewrite/reject. A second change between review and Save gets the same conflict, with no partial write. Do not say “Updated” until the transaction succeeds.

## Pending amendment and withdrawal

A helper may amend **its own still-pending proposal** with a new request key and the expected proposal revision. The replacement must pass the same grants and dry-run checks. Keep the previous version in proposal history; show **“Stock note helper changed this suggestion before you reviewed it. Check the new value.”** with old and new values/time. A Review tab opened before the amendment cannot accept its stale version. A helper may withdraw its own unreviewed proposal; show **“Withdrawn by Stock note helper before review. No record changed.”** Once a person starts or completes a changed acceptance, or a proposal is accepted/rejected, the helper cannot amend or withdraw that decision. Revoking a helper blocks amendment but keeps history and pending proposals for the person.

These require future endpoints such as `POST /api/v1/proposals/{id}/amend` and `/withdraw`, with the same bearer, module, Origin and Host guards as v1. Endpoint names are **proposed**, not additions to [the v1 OpenAPI file](openapi-v1.json). Same-key retries must return the first result; a changed body with the same key conflicts.

## Undo is a household decision

**Undo accepted change** is a person-only action on Review/history. Preview the accepted before/after fields, current values, later edits and linked side effects. If the record still matches the accepted after-state and no later dependent action would be harmed, apply the inverse through the normal core record service, audit it and show **“Your earlier change was undone. The helper's original suggestion remains in history.”** If a person later edited any affected field, or a stock movement/batch would go negative, refuse automatic undo: **“This record changed after the suggestion was accepted. Nothing was undone. Review the later changes and edit the record yourself.”** Never force an old full snapshot over newer household work. For an accepted **new** row, Undo previews a normal soft delete and its cascade/restore effects; it does not erase audit or private history. A helper may request no Undo of an accepted row.

A batch with several accepted suggestions needs a conflict preview for **every** affected row and side effect before a group Undo. Default to all-or-nothing, then let the person choose individual safe rows if one conflicts; do not undo some silently. A rejected or withdrawn proposal has nothing live to undo.
