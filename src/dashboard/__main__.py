"""Command-line entry point: prints the version while the program is still being built."""
from __future__ import annotations

import sys

from dashboard import __version__


def main() -> int:
    """Say plainly that there is nothing to open yet."""
    print(f"Dashboard Plus {__version__}")
    print("This version is the project skeleton. There is nothing to open yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
