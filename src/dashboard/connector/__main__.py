"""Start the connector: `python -m dashboard.connector [--config FILE]`, launched by an AI assistant's app."""
from __future__ import annotations

import sys

from dashboard.connector.mcp_server import main

if __name__ == "__main__":
    sys.exit(main())
