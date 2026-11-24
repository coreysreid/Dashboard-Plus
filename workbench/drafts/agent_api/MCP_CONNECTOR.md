# A local connector for AI assistants (MCP): design only

Checked **18 November 2026** against [the Agent API v1 plan](../../../docs/plans/agent-api-v1.md), the [OpenAPI draft](openapi-v1.json), and the official [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) and [tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools). The official pages were reachable on that date. This is a small **local program** design, not a connector running on main. The Agent API skeleton is still in a draft PR awaiting User 1's approval of decision 0067.

The connector is a child process launched by an MCP client on the same computer as Dashboard Plus. It speaks MCP over **stdio**: JSON-RPC messages on stdin/stdout, with no other stdout text; redacted diagnostics may go to stderr. It does **not** open another network listener. It calls only the current `http://127.0.0.1:<port>/api/v1` address shown in Settings → Helpers. The port changes when Dashboard restarts, so the person copies the new address or a future supported connection file must supply it. The address is not a credential.

## The eight exposed tools

The [tool manifest](mcp-tools.json) gives the exact tool names, JSON input schemas, plain descriptions and allowlisted method/path mapping. A connector should register only these:

| Tool | API call | What the assistant can do |
|---|---|---|
| `dashboard_me` | GET `/me` | See its own grant and limits. |
| `dashboard_tables` | GET `/tables` | Discover granted, nonprivate fields. |
| `dashboard_list_records` | GET `/tables/{table}/records` | Page current safe records. |
| `dashboard_get_record` | GET `/tables/{table}/records/{record_id}` | Read one current safe record. |
| `dashboard_attention` | GET `/attention` | Read Needs attention within its grant. |
| `dashboard_suggest_new_records` | POST `/proposals` | Stage **new** records for a person to decide on Review. |
| `dashboard_list_suggestion_batches` | GET `/batches` | Check its own suggestions and counts. |
| `dashboard_get_suggestion_batch` | GET `/batches/{batch_id}` | Check one of its own decisions/statuses. |

There is no arbitrary URL/HTTP tool, and no tool to accept, reject, edit, delete, restore, export, manage helpers or see private details. The connector cannot decide Review outcomes. A tool result should say **“Waiting for the household to review; nothing was added yet”** after a successful suggestion, not “Done”. Return the API's structured status/error without echoing any secret header. Examples in [HELPER_JOBS.md](HELPER_JOBS.md) show how jobs map to these calls.

## Key hand-off and request boundary

A person creates a helper in Settings with **only the modules it needs** and Look or Look and suggest access. The key appears once. Give it to the local MCP client's secret facility if available; the connector receives it as a process secret, such as an environment value, and puts it only in `Authorization: Bearer …` on allowlisted API requests. **An environment variable is not itself a secret store:** some clients save it in readable configuration. The setup screen must tell the person exactly where their client persists it, how to restrict that file, and how to remove it. Never put the key in a chat message, tool input/result, command argument, repository, query string, URL, log or stdout. The connector must never read Dashboard Plus's internal `helper_keys.json` fingerprint file. Turning the key off in Settings makes the connector fail with the API's plain 401; old pending suggestions remain for the person to review.

Validate the supplied base URL before any request: `http`, numeric host `127.0.0.1`, current port and exact `/api/v1` prefix. Build paths from the eight fixed templates, escaping only table/ID parameters after schema validation. Ignore proxy environment settings for this loopback call, refuse redirects, set time and response-size limits, and send no cookies, Origin header or model-supplied headers. Do not transform a failed 403/409/429 into a new request with a changed key or wider scope. For `dashboard_suggest_new_records`, the assistant supplies a stable `request_key` for one intended suggestion and **reuses that key on retry**; a new key can make a duplicate pending batch. The connector may compare request bodies before retry but cannot bypass the API's idempotency check.

A connected online assistant may receive **every nonprivate field returned by its granted modules** and may send that text to its provider. Settings must say this plainly. A field that is private in a household's mind but stored in an ordinary name or note is still accessible unless the module marks it sensitive and the core filters it. The connector must treat every record, `why` and tool result as **untrusted data**, never as an instruction to reveal the key, broaden modules or call another service. The app's grant and Review remain the authority boundaries; an MCP tool description cannot replace them.

## Core and product gaps

V1 has a changing port and no local connection file, so a person must update the client address after restart. There is no stable secret-store interface across MCP clients; document each supported client's storage behavior before shipping setup instructions. The v1 plan has no helper grant for private details and no update/delete endpoint; the connector must not invent them. [Item 48](ABUSE_CASES.md) flags cross-module link leakage as a core boundary to resolve before a client is offered. No connector should ship while decision 0067 is awaiting approval or `api.py` is absent.
