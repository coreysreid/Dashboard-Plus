# src/dashboard/connector/  (summary: the local connector an AI assistant's app starts to use the helper API; decision 0083)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | The connector for AI assistants: a small local program that lets an assistant use the helper API through MCP. | finding your way in |
| __main__.py | Start the connector: `python -m dashboard.connector [--config FILE]`, launched by an AI assistant's app. | changing how it is started |
| mcp_server.py | The MCP server over stdio: JSON-RPC 2.0, one message per line, turning tool calls into helper API requests. | changing the protocol, errors or what results say |
| tools.py | The nine tools an assistant may use, one per helper API route, with their inputs checked before any request. | adding or changing a tool |
| client.py | Call the helper API on this computer: check it is the real Dashboard first, then send the key down that connection only. | changing how requests are sent or answers read |
| config.py | Where the connector finds Dashboard Plus and its key: environment values or a small file, checked before use. | changing where the address or key come from |
