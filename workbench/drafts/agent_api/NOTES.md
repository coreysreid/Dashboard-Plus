# Agent API draft notes

Updated **19 November 2026** after the API merged (decisions 0066–0069, 0074, 0084–0086). [ABUSE_CASES.md](ABUSE_CASES.md) remains the original design and test catalogue; the [dated live recheck](../../reports/2026-11-19-agent-api-abuse-recheck.md) says which of its 22 cases hold on current `main`. The shipped OpenAPI description at `src/dashboard/web/openapi-v1.json`, served by `GET /api/v1/openapi.json`, supersedes this draft folder's `openapi-v1.json` and `OPENAPI_NOTES.md` for client generation.

The plan already covers bearer-only auth, local Host and Origin checks, module grants, private-field exclusion, staged suggestions, idempotency, bounded bodies and a daily proposal cap. The highest-priority behavior to verify in the build is **no live side effect before a person accepts** and **no hidden module name, ID or private value in any response or proposal validation**. A local program that has a key is authorized within its grant; Origin checks cannot stop local malware or a key willingly given to an online service.

**Current core gap:** request throttling, a 200/day cap, a 500-waiting cap, hidden-link protection, helper-text screening and one 404 for unknown or ungranted tables have shipped. The two suggestion caps can still be exceeded by simultaneous requests because their counts are read before the insertion transaction. Move their final checks inside the write transaction and add concurrent tests; see the dated recheck for the exact temporary-household reproduction. An unsupported `/api/v2/` request also redirects to the page start instead of returning a JSON 404. A future MCP connector still needs an untrusted-record-text test before it can ship.

Item 51 adds [later change-suggestion screens](CHANGE_SUGGESTIONS.md) and [acceptance checks](CHANGE_ACCEPTANCE.md). V1 is still add-only; these need monotonic revisions and person-only conflict/undo services before any endpoint is exposed.

Item 52 adds a [local stdio MCP design](MCP_CONNECTOR.md), [eight-tool manifest](mcp-tools.json) and [acceptance checks](MCP_ACCEPTANCE.md). The v1 API has landed; the connector itself still needs implementation, client secret storage and setup guidance for the changing port.

Item 53 adds a [future one-field private grant](PRIVATE_GRANT.md) and [acceptance checks](PRIVATE_GRANT_ACCEPTANCE.md). V1 continues to share no sensitive fields; a grant needs a dedicated API route, durable revision, one-read consumption and restore-safe revocation before it can ship.
