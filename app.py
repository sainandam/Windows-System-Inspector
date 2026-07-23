"""
app.py

CLI entry point for DevPilot System Inspector.

Usage
-----
Run the dashboard::

    python app.py

Export to a specific format::

    python app.py --export json
    python app.py --export csv
    python app.py --export html

Export and suppress the dashboard::

    python app.py --export json --no-dashboard

Show help::

    python app.py --help
"""

from __future__ import annotations

import argparse
import sys
import time

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from inspector import SystemInspector
from inspector.constants import PROJECT_NAME, PROJECT_VERSION, SUPPORTED_EXPORT_FORMATS
from inspector.dashboard import Dashboard
from inspector.exceptions import AnalysisError, ExportError, UnsupportedExportFormatError
from inspector.exporter import Exporter

console = Console(highlight=False)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devpilot-inspector",
        description=f"{PROJECT_NAME} v{PROJECT_VERSION} — Windows System Inspection SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python app.py                     # display Rich dashboard\n"
            "  python app.py --export json       # export JSON report\n"
            "  python app.py --export html       # export HTML report\n"
            "  python app.py --export csv --no-dashboard\n"
        ),
    )
    parser.add_argument(
        "--export",
        metavar="FORMAT",
        choices=SUPPORTED_EXPORT_FORMATS,
        help=f"Export the report. Choices: {', '.join(SUPPORTED_EXPORT_FORMATS)}",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        default=False,
        help="Skip the Rich dashboard (useful when exporting only).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROJECT_NAME} {PROJECT_VERSION}",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    # ----------------------------------------------------------------
    # Run the inspection with a live spinner
    # ----------------------------------------------------------------
    report = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Inspecting system …", total=None)
        try:
            report = SystemInspector().analyze()
        except AnalysisError as exc:
            console.print(f"[bold red]Analysis failed:[/bold red] {exc}")
            sys.exit(1)
        finally:
            progress.update(task, completed=True)

    # ----------------------------------------------------------------
    # Display Rich dashboard (default behaviour)
    # ----------------------------------------------------------------
    if not args.no_dashboard:
        Dashboard(report).render()

    # ----------------------------------------------------------------
    # Export report if requested
    # ----------------------------------------------------------------
    if args.export:
        try:
            path = Exporter(report).export(args.export)
            console.print(
                f"\nReport saved to [cyan]{path}[/cyan]"
            )
        except UnsupportedExportFormatError as exc:
            console.print(f"[bold red]Export error:[/bold red] {exc}")
            sys.exit(1)
        except ExportError as exc:
            console.print(f"[bold red]Export failed:[/bold red] {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
