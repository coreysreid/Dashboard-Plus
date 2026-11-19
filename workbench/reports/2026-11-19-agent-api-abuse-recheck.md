# Agent API abuse cases: recheck of the shipped boundary

Checked **19 November 2026** against `main` at `94f398f`, decisions [0074](../../docs/decisions/0074-agent-api-hardening.md), [0085](../../docs/decisions/0085-review-queue-cap.md) and [0086](../../docs/decisions/0086-connector-checks-it-is-really-dashboard.md). This is batch 14 item 56. I compared all 22 numbered cases in the [original catalogue](../drafts/agent_api/ABUSE_CASES.md) with `src/dashboard/core/{helpers,proposals}.py`, `src/dashboard/web/{api,app,review}.py` and the `test_helper_*` tests. The concurrent probes used separate SQLite connections to an invented temporary Stock household; no shipped code or household data was changed.

## Findings, worst first

### Important — case 11 is partly held: simultaneous requests can pass both suggestion caps

**Steps:** Fill a helper's daily count to 199 with four valid batches (50, 50, 50, 49). Start two distinct one-row `proposals.submit` calls on separate SQLite connections. Synchronize them immediately after each has read `used_today = 199`, then let both continue. Both return a batch ID; the final count is **201**, past the 200/day cap. For the Review queue, fill 499 pending suggestions, raise the daily cap only in the temporary probe to isolate this limit, and synchronize two one-row calls after both read `waiting_for = 499`. Both succeed; **501** wait against the 500 cap. These are deterministic concurrent reproductions; ordinary sequential 201st and 501st requests are correctly refused with 429.

**Cause:** `proposals.submit` reads both counts before its `db.transaction`/`BEGIN IMMEDIATE` insertion. Different request keys avoid the unique-key protection. **Expected:** At most 200 suggestions in a UTC day and 500 from a helper waiting on Review, including simultaneous requests. **Suggested core change:** Recheck the daily and waiting counts under the same write transaction that inserts the batch and proposals, and refuse the whole request with the existing 429 error before any insert. Keep same-key retries returning their original batch. Add two-connection tests for both caps. This protects Review from a runaway local helper while preserving the current plain messages.

### Minor — case 21 is partly held: an unsupported API version answers as a page

**Steps:** Send a bearer-only GET to `/api/v1/nope`: it returns JSON 404. Send the same request to `/api/v2/me`: it returns **302 HTML** to `/start`, because only `/api/v1/` enters the API guard. There is no grant or write bypass. The original catalogue expected JSON 404 for an unsupported version. **Exact suggested reply:** HTTP 404 JSON `{"error":"not_found","message":"This API version is not available. Use /api/v1/."}` for `/api/v2/…` and other `/api/vN/…` paths. This is a client clarity issue, not a security breach.

### Deferred — case 14 needs the MCP connector to exist

The v1 API returns household record text as data, but no MCP wrapper is shipped yet. Its ability to label malicious record content as untrusted and refuse tool actions cannot be runtime checked. Before a connector ships, use the twelve checks in [`MCP_ACCEPTANCE.md`](../drafts/agent_api/MCP_ACCEPTANCE.md), including a made-up record that says to send the key to `example.com`.

## All 22 cases

“Held” means the shipped code and focused tests support the boundary described in the catalogue; it is not a formal penetration-test claim. “Partly held” identifies the reproduced gap above. The catalogue's old 403 expectation for an ungranted table was intentionally changed by decision 0074 to an indistinguishable 404.

| Case | Result | Evidence or limit |
|---|---|---|
| 1. Leaked key and revocation | Held | Key shown once; fingerprint outside the DB; Turn off makes it fail. A copied key remains usable until revoked. |
| 2. Web page, Origin and Host | Held | Any Origin and wrong Host refused; cookie and bearer permissions stay separate. |
| 3. Local key holder | Held within grant | A program with the key may use its scope. Private fields, other modules, page actions and revoked keys are refused. |
| 4. Side effects before Review | Held | Proposals stay in core staging; Accept creates one live row; Reject creates none. |
| 5. Crafted controls and ungranted table | Held, revised | System, worked-out and private fields refused. Unknown and ungranted tables now share 404, per 0074. |
| 6. Backup and restored keys | Held | Fingerprint file outside DB prevents old backup from reviving or remapping a key; absent file fails closed. |
| 7. Guessing and comparison | Held within test limits | Long random key, bounded header, generic 401 and `hmac.compare_digest` across stored fingerprints. No formal timing proof. |
| 8. Hidden linked modules | Held | Schema, records and Attention omit ungranted links; guessed link IDs get the same refusal; Accept rechecks. |
| 9. Other helper's batches | Held | Batch list and detail filter by helper ID; foreign IDs answer 404. |
| 10. Request-key retries and races | Held | Same body returns first batch; changed body gets 409. Parallel same-key probe made one batch and proposal. |
| 11. Flooding and caps | **Partly held** | Body, entry, page and rate limits work; daily and waiting caps have the concurrent race above. |
| 12. Malformed or SQL-like input | Held | Registry field checks and dry-run rollback refuse bad rows without a partial batch; 500 response is generic. |
| 13. Helper text on Review | Held | Markup escaped, provenance stated, hidden/bidi text screened, and a person must press Accept. |
| 14. Malicious instructions in records | Deferred | No MCP wrapper yet; API data must remain untrusted in the future connector. |
| 15. Stale proposed links | Held for add-only v1 | Accept revalidates; deleted links and switched-off modules do not add a row. Semantic edits to a still-valid link are outside v1's add-only contract. |
| 16. Double decision | Held | One pending-to-decided update and transaction; concurrent Accept/Reject tests add at most one row. |
| 17. Credential separation | Held | A page cookie does not open the API; a bearer key does not open pages or bypass page CSRF. |
| 18. Secrets in text and responses | Held for key-shaped text | `dph_`-shaped text is refused before storage; API responses are no-store, errors do not echo values, audits omit proposal text. |
| 19. Turned-off helper's proposals | Held | Old key gets 401; pending suggestions remain on Review with access-off wording. |
| 20. Unknown versus ungranted | Held | Both return the same 404 code and body; `/tables` lists only the grant. |
| 21. Unsupported version and body | **Partly held** | V1 unknown route JSON 404, non-JSON proposal 415, malformed JSON 400; `/api/v2/me` returns HTML redirect. |
| 22. Misleading reason and name | Held | Reason length bounded and attributed to the named helper; a person chooses the helper name in Settings. |

**Scope:** This recheck focused on the 22 cases and the merged API. It did not run malware, an online assistant, or a future MCP connector. The original catalogue is a design artifact from before the API merged; this report records the shipped result. Sources and tests named above were checked on 19 November 2026.
