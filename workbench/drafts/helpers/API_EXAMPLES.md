# Agent API: one invented household session

Draft checked against [DESIGN sections 8–9](../../../docs/DESIGN.md) on 17 November 2026. These routes do not ship yet. The JSON and status codes are proposed, not observed. All names and IDs are made up; `TOKEN_SHOWN_ONCE` is a placeholder, never a credential.

The household gives **Pet diary helper** `pets__weigh_ins` access only, without private fields. Settings says “Pet diary helper may suggest and read Weigh-ins. Private fields: off.” Every call has `Authorization: Bearer TOKEN_SHOWN_ONCE`. Fictional pet 1 is Miso.

## All six routes

1. `GET /api/tables` → `200 {"tables":{"pets__weigh_ins":{"columns":{"pet":{"type":"link","to":"pets.pets","required":true},"day":{"type":"date","required":true},"weight":{"type":"decimal","unit":"kg","min":0,"required":true},"notes":{"type":"text"}}}}}`. Only permitted columns appear; the helper reads this before proposing. Review is unchanged.
2. `GET /api/rows?table=pets__weigh_ins&limit=20` → `200 {"rows":[{"id":14,"values":{"pet":1,"day":"2026-11-10","weight":4.2,"notes":"Home scale"}}],"next":null}`. A read has no Review effect.
3. `POST /api/propose` body `{"request_key":"miso-paper-log-2026-11-17","why":"Copied Miso's paper log","entries":[{"table":"pets__weigh_ins","values":{"pet":1,"day":"2026-11-17","weight":4.3,"notes":"Home scale"}}]}` → `201 {"batch_id":"batch-31","state":"needs_review","rows":[{"id":31,"review_status":"needs_review"}]}`. Review says “Pet diary helper · 1 suggestion · Copied Miso's paper log”; confirmed weigh-ins do not change. An exact retry by the same helper returns this result, adding nothing.
4. `POST /api/amend` body `{"row_id":31,"values":{"weight":4.25},"why":"Corrected a transcription"}` → `200 {"row_id":31,"review_status":"needs_review","values":{"pet":1,"day":"2026-11-17","weight":4.25,"notes":"Home scale"}}`. Review says “Changed by Pet diary helper before your review” and shows the corrected value; history retains the first value.
5. `GET /api/batches?limit=20` → `200 {"batches":[{"id":"batch-31","request_key":"miso-paper-log-2026-11-17","state":"needs_review","total":1,"pending":1,"accepted":0,"rejected":0}]}`. Review still counts one suggestion.
6. `POST /api/undo` body `{"batch_id":"batch-31","why":"Paper log was for another day"}` → `200 {"batch_id":"batch-31","withdrawn":1}`. A single-row variant takes `row_id`. Pending count becomes zero; history says “Withdrawn by Pet diary helper before review.” No confirmed row is removed.

In another branch, the person chooses **Change then accept**, enters 4.2 kg and accepts. Review's pending count falls; history shows the 4.3 proposal, 4.25 helper correction and 4.2 person decision. `edited_by_person` locks it. **Reject** instead says “Rejected. Nothing was added to Weigh-ins.”

## Every refusal category

Responses should be `{"error":"short_code","message":"plain sentence"}` without echoing private values. “Unchanged” means no new, edited or withdrawn suggestion and no change to confirmed records.

| Attempt | Proposed message | Review afterwards |
|---|---|---|
| Missing, malformed, expired or revoked bearer key | `401` “This helper's access key is missing or no longer works. Ask the household to check Helpers in Settings.” | Unchanged; revoke keeps history. |
| Read schema/rows or propose/amend outside granted tables | `403` “Pet diary helper may use Weigh-ins only. Ask the household to change its access in Settings.” | Unchanged; no other table data exposed. |
| Read or write a sensitive field without `--sensitive` | `403` “This helper does not have access to private fields. Ask the household to change its access in Settings.” | Unchanged; do not echo attempted value. |
| Missing `request_key` | `400` “Give this request a key so a retry cannot add the same rows twice.” | Unchanged. |
| Same helper/key, different body within 30 days | `409` “This request key was already used for different suggestions. Check the earlier batch, then use a new key.” | Original batch only; identical body returns original result. |
| More than 50 entries in a call | `400` “Send 50 suggestions or fewer at a time.” | Unchanged; no partial batch. |
| More than 200 rows for this helper today | `429` “This helper has reached 200 suggestions today. Try again tomorrow.” | Unchanged; no partial batch. |
| Invalid, missing or unknown field, wrong type, link or choice | `422` “Weigh-ins: weight must be a number of kilograms at least 0.” Name the actual table, field and allowed values. | Unchanged; validate entire batch. |
| Missing table or malformed query/body | `400` “Choose a table this helper may use.” / “This request could not be read. Check the fields and try again.” | Unchanged. |
| Amend/undo another helper's or person's row | `403` “This helper can change only its own unreviewed suggestions.” | Unchanged; do not disclose another row. |
| Amend/undo accepted, rejected, withdrawn or person-edited row | `409` “This suggestion was already reviewed or edited by a person. The helper cannot change it.” | Decision and record remain. |
| Unknown row or batch | `404` “That suggestion could not be found. Refresh the helper's batches and try again.” | Unchanged. |
| Stale person decision after proposal or target changed | `409` “This suggestion changed since you opened it. Review the latest values before accepting.” | Still pending until fresh decision. |

DESIGN does not settle pagination cursors, token lifetime, exact amend/undo wire shape or error-code names. Lane A should settle them in a core decision. Proposal writes need staging: a Stock `adjusts` action must not change live amounts before review. Source: [DESIGN sections 8–9](../../../docs/DESIGN.md), checked 17 November 2026.
