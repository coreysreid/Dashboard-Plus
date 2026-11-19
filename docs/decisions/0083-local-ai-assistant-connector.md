# 0083. A local connector for AI assistants (MCP)

- **Status:** Accepted
- **Date:** 2026-11-19
- **Decided by:** Claude (technical decision delegated by Corey), from Lane B's design in `workbench/drafts/agent_api/MCP_CONNECTOR.md`

## In plain words
Many AI assistant apps can use "tools" through a standard called MCP. Dashboard
Plus now comes with a small connector the assistant's app starts on this
computer. It lets the assistant do exactly what a helper key allows (look at
the parts you ticked and suggest new records) and nothing more. Suggestions
still wait for you on the Review page. Settings, Helpers shows the settings to
paste into the assistant's app, with `YOUR-KEY-HERE` where the key goes.

## What we chose
- **A stdio MCP server in `src/dashboard/connector/`**, started with
  `python -m dashboard.connector`. It reads one JSON-RPC 2.0 message per line
  on stdin and writes one per line on stdout; nothing else goes to stdout.
  It speaks MCP protocol `2025-06-18` (and accepts `2025-03-26` and
  `2024-11-05` if the app asks for them), and answers only `initialize`,
  `ping`, `tools/list` and `tools/call`. Anything else gets the standard
  JSON-RPC error (-32700 unreadable, -32600 not a valid request, -32601 no
  such method, -32602 no such tool). It opens no network port of its own.
- **No new library.** The protocol is small enough to write with Python's
  standard library (`json`, `urllib`), so nothing is added to
  `requirements.txt`.
- **Eight tools, one per helper API route**, with the names from Lane B's
  manifest (`dashboard_me`, `dashboard_tables`, `dashboard_list_records`,
  `dashboard_get_record`, `dashboard_attention`,
  `dashboard_suggest_new_records`, `dashboard_list_suggestion_batches`,
  `dashboard_get_suggestion_batch`). Each has a closed JSON Schema; arguments
  are checked before any request, and a path is only ever built from a fixed
  route plus a checked table name or id. There is no tool to accept, reject,
  edit, delete, reach settings, or call any other address.
- **Every result is labelled as household data, not instructions** (Lane B's
  abuse case 14): the text starts with a sentence saying so, the data follows
  as JSON, and `structuredContent` carries the same label beside the data.
  The `initialize` instructions say the same. A suggestion's result repeats
  the API's own words that it is waiting for review.
- **The address and key come only from the person**: the environment values
  `DASHBOARD_PLUS_URL` and `DASHBOARD_PLUS_KEY`, or a small TOML file named
  with `--config` (the environment wins). Never from a tool's arguments. Only
  `http://127.0.0.1:<port>` or `http://localhost:<port>` (optionally ending in
  `/api/v1`) is accepted; anything else is refused and never contacted.
- **The key never leaves except in its header.** Requests use `urllib` with a
  15-second timeout, an empty proxy list (so `HTTP_PROXY` is ignored), and
  redirects refused. Every line written to stdout or stderr has the key, and
  anything shaped like a helper key, replaced by `[key hidden]`. Messages on
  stderr are one line each, never a stack trace.
- **API refusals become plain tool errors** (`isError: true`): "Dashboard Plus
  said: <the API's message>", with its status, code and problems as data. A
  refused request is never retried with another key or wider access; a
  timed-out suggestion tells the assistant to retry with the same
  `request_key`, which cannot add it twice.
- **Settings, Helpers and the new-key page** show "Connect an AI assistant":
  a JSON block for the assistant app's MCP settings (`command` is the Python
  running Dashboard, `args` are `-m dashboard.connector`, `env` holds the
  current address and `YOUR-KEY-HERE`), plus the words "The key is a
  password" and, as in decision 0082, that an online assistant "will see what
  the helper reads". The real key appears only in the one box on the new-key
  page, as before.
- **The portable Windows folder needs no new file.** Its bundled Python
  already finds our code (its `._pth` file lists `..\src`), so the command
  shown is `...\Dashboard Plus\app\python\python.exe` with
  `-m dashboard.connector`. No `.exe` or `.bat` was added: recent versions of
  Node, which many assistant apps run on, refuse to start a `.bat` file
  directly, and a separate `.exe` would need a new build tool.

## Why we chose it
- It keeps the one safety boundary in the app: the connector holds no rights
  of its own and can only make the eight requests a helper key already allows.
  Review stays the only way anything is added.
- Standard input and output mean no extra port, nothing listening, and the
  assistant's app controls when it runs.
- With no new library there is nothing new to keep pinned and checked.
- Labelling results as data is the cheapest defence against a record that
  says "ignore your instructions"; the key cannot leak through the
  connector's own output even if a model tries to echo it.

## What else we considered
- **An MCP library (the official Python SDK):** less code, but a large new
  dependency tree for a few hundred lines of protocol.
- **MCP over HTTP inside Dashboard itself:** no extra program, but another
  door into the app that browsers could knock on, and harder to keep separate
  from the pages' protections.
- **Putting the real key into the settings block on the new-key page:**
  easier to copy once, but the key would then sit in two places on the page
  and in anything that copies the page; the placeholder keeps it in one box.

## What this costs us (the downsides)
- **An online assistant sees what it reads.** Every non-private field in the
  parts a helper may use can be sent to the assistant's provider. Private
  details stay out because the API never returns them, but a private matter
  typed into an ordinary note is not protected. The Helpers page says this.
- **The key is kept by the assistant's app, often in a readable settings
  file.** An environment value is not a secret store. The page tells the
  person the key is a password and how to remove it; the connector warns on
  stderr if its own `--config` file can be read by others.
- **The address changes each time Dashboard opens** (port chosen at start),
  so the person must update the assistant's settings after reopening. A fixed
  port or a connection file is still to come (plan section 8).
- **A program now on the old port would receive the key.** If Dashboard is
  closed and another local program takes its port, the connector sends the
  key there. Only programs already running on this computer could do this.
- **Labels are a request, not a guarantee.** A model may still be swayed by
  text inside a record; the real protection is that the connector can do
  nothing beyond the key's grant and that suggestions wait for a person.
- We write and maintain the protocol code ourselves; new MCP versions may
  need small updates.

## How hard it is to undo
Easy: delete `src/dashboard/connector/`, `tests/test_mcp_connector.py` and
`templates/helper_connect.html`, remove the two `include` lines and
`assistant_settings` from the Helpers pages. The helper API is unchanged, so
nothing else depends on it; people would remove the "dashboard-plus" entry from
their assistant's settings.

## We should revisit this if
- People struggle with the changing address: add a fixed port or a
  connection file the connector can read.
- A common assistant app cannot start the command shown (for example it needs
  a single `.exe`), or stores keys somewhere we should warn about by name.
- MCP changes in a way the hand-written protocol cannot follow cheaply; then
  weigh the official library again.
