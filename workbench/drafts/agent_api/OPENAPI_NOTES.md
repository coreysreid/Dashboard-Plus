# Helper API v1 contract notes

The [OpenAPI 3.1 description](openapi-v1.json) was drafted **18 November 2026** from [Lane A's v1 plan](../../../docs/plans/agent-api-v1.md). It describes eight `/api/v1/` operations with bearer auth, every planned error status, a made-up request/response for each route, and the current limits. The helper's local port changes by launch; the example `5199` in the server variable is not a fixed port. This is a **draft contract**, not proof that `api.py` ships on main. The old `workbench/drafts/helpers/API_EXAMPLES.md` describes an earlier route and review design and must not be copied into v1.

The JSON form is an OpenAPI 3.1 document; JSON Schema type unions express nullable `next_after`, `record_id` and `reason`. Dynamic module values deliberately use an open `values` map, but the runtime `/tables` response supplies the allowed field names, types, choice keys and link targets. The plan forbids private, system and derived fields in proposals; the spec describes this in the request schema and errors. A response example uses the fictional Pet diary helper and Miso's invented weight. `request_key` and `why` are test strings, not credentials.

## Keep these in step with the implementation

1. **Routes and verbs:** compare all eight path operations with `src/dashboard/web/api.py` after the skeleton merges. Keep the page-only `/review` and Settings actions out of the bearer API description.
2. **Exact envelopes:** the plan names `/attention` sections but not its final JSON member names; it also does not settle all `/batches` summary/detail fields or whether a single record GET has a wrapper. The examples and `Attention`/`BatchSummary` schemas are **provisional**. Confirm them against live JSON before using this file to generate a client.
3. **Errors:** match 400/401/403/404/409/413/415/422/429 and the safe 500 body to code. The 403 examples distinguish `not_allowed`, `look_only`, `private_detail` and `from_a_web_page`. The 422 example must retain entry/table/field without echoing submitted values. Add any code-specific refusal before calling the spec final.
4. **Limits and paging:** sync body 65,536 bytes, 50 entries per POST, 200 suggested rows per helper per UTC day, 1–300 `why`, 1–100 request key, record and batch limits, keyset `after`, and identical-request 200 versus first-submit 201.
5. **Privacy and scope:** a granted module must not disclose a hidden module through linked IDs, target schema, formatted names, gap text or guessed-ID validation. [Item 48](ABUSE_CASES.md) flags this as a critical gap to check. The spec must narrow link fields when the implementation decides its grant-aware policy.
6. **Value formats:** ISO dates, decimal money in major units, stable choice keys and link IDs. Check `Cache-Control: no-store`, JSON content type and that cookies, query-string keys and Origin-bearing requests never authenticate.
7. **Versioning:** the document is `0.1.0-draft`; when the skeleton is approved and merged, set a matching release version, record incompatible changes, and check that every example passes against the running app with invented data. Never publish this as a stable SDK contract before that check.

No new external household guidance is claimed. The source is the repository plan and shipped schema conventions, checked 18 November 2026.
