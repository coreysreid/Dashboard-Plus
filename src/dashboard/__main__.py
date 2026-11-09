"""Command-line entry point: open the dashboard, or close a running one safely."""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

from dashboard import __version__


def write_report(data_dir: Path, error: BaseException) -> Path | None:
    """Save technical details of a failure to a file the person can choose to share."""
    try:
        reports = data_dir / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / f"report-{datetime.now():%Y%m%d-%H%M%S}.txt"
        details = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        path.write_text(f"Dashboard Plus {__version__}\n\n{details}", encoding="utf-8")
        return path
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run; failures are explained in plain words."""
    parser = argparse.ArgumentParser(prog="dashboard", description="Dashboard Plus")
    parser.add_argument("--data", default="data", help="the data folder (default: ./data)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    parser.add_argument("--close", action="store_true", help="close a running dashboard safely")
    parser.add_argument("--modules", help="the modules folder (default: the one shipped with the program)")
    parser.add_argument("--version", action="store_true", help="print the version and stop")
    args = parser.parse_args(argv)

    if args.version:
        print(f"Dashboard Plus {__version__}")
        return 0

    data_dir = Path(args.data).resolve()
    try:
        from dashboard import server

        if args.close:
            if server.close_running(data_dir):
                print("Dashboard closed safely. You can unplug the drive now.")
            else:
                print("Dashboard is not running, so there is nothing to close.")
            return 0
        modules_dir = Path(args.modules).resolve() if args.modules else None
        server.serve(data_dir, open_browser=not args.no_browser, modules_dir=modules_dir)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as error:  # noqa: BLE001 - every failure gets a plain message
        from dashboard.errors import PlainError

        report = write_report(data_dir, error)
        print("Sorry, Dashboard Plus could not start or stop properly.")
        if isinstance(error, PlainError):
            print(str(error))
        print("Your data has not been changed.")
        if report:
            print(f"A report with the details was saved to: {report}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
