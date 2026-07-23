"""
exporter.py

Report exporter — serialises an InspectionReport to JSON, CSV, or HTML.

All three formats are written to the reports/ directory.  The output
path is returned from each export method so callers can display it.

Design notes:
- JSON: full recursive serialisation via dataclasses.asdict().
- CSV:  one row per section; nested structures are JSON-encoded in cells.
- HTML: self-contained file with inline CSS; no external dependencies.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from inspector.constants import (
    CSV_REPORT,
    EXPORT_CSV,
    EXPORT_HTML,
    EXPORT_JSON,
    HTML_REPORT,
    JSON_REPORT,
    PROJECT_NAME,
    PROJECT_VERSION,
    REPORTS_DIR,
    SUPPORTED_EXPORT_FORMATS,
)
from inspector.exceptions import ExportError, UnsupportedExportFormatError
from inspector.logger import get_logger
from inspector.models import InspectionReport

log = get_logger(__name__)


class Exporter:
    """
    Serialises an :class:`~inspector.models.InspectionReport` to disk.

    Usage::

        path = Exporter(report).export("json")
        print(f"Report saved to {path}")

    Parameters
    ----------
    report:
        The :class:`InspectionReport` to export.
    """

    def __init__(self, report: InspectionReport) -> None:
        self._report = report
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def export(self, fmt: str) -> Path:
        """
        Export the report in the requested format.

        Parameters
        ----------
        fmt:
            One of ``"json"``, ``"csv"``, ``"html"``.

        Returns
        -------
        Path
            The path to the written file.

        Raises
        ------
        UnsupportedExportFormatError
            If *fmt* is not in SUPPORTED_EXPORT_FORMATS.
        ExportError
            If writing the file fails.
        """
        fmt = fmt.lower().strip()
        if fmt not in SUPPORTED_EXPORT_FORMATS:
            raise UnsupportedExportFormatError(fmt, SUPPORTED_EXPORT_FORMATS)

        dispatch = {
            EXPORT_JSON: self._export_json,
            EXPORT_CSV: self._export_csv,
            EXPORT_HTML: self._export_html,
        }
        return dispatch[fmt]()

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def _export_json(self) -> Path:
        path = JSON_REPORT
        log.debug("Exporting JSON report to %s", path)
        try:
            data = dataclasses.asdict(self._report)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            log.info("JSON report written: %s", path)
            return path
        except Exception as exc:
            raise ExportError(f"JSON export failed: {exc}") from exc

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def _export_csv(self) -> Path:
        path = CSV_REPORT
        log.debug("Exporting CSV report to %s", path)
        try:
            rows = self._flatten_for_csv()
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["section", "key", "value"])
                writer.writeheader()
                writer.writerows(rows)
            log.info("CSV report written: %s", path)
            return path
        except Exception as exc:
            raise ExportError(f"CSV export failed: {exc}") from exc

    def _flatten_for_csv(self) -> list[dict]:
        """
        Flatten the report into (section, key, value) triples for CSV.

        Nested dataclasses and lists are JSON-encoded into the value cell.
        """
        rows = []
        data: Dict[str, Any] = dataclasses.asdict(self._report)

        for section, content in data.items():
            if isinstance(content, dict):
                for key, val in content.items():
                    rows.append({
                        "section": section,
                        "key": key,
                        "value": json.dumps(val, default=str) if isinstance(val, (dict, list)) else str(val),
                    })
            elif isinstance(content, list):
                rows.append({
                    "section": section,
                    "key": section,
                    "value": json.dumps(content, default=str),
                })
            else:
                rows.append({"section": "meta", "key": section, "value": str(content)})

        return rows

    # ------------------------------------------------------------------
    # HTML
    # ------------------------------------------------------------------

    def _export_html(self) -> Path:
        path = HTML_REPORT
        log.debug("Exporting HTML report to %s", path)
        try:
            html = self._build_html()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            log.info("HTML report written: %s", path)
            return path
        except Exception as exc:
            raise ExportError(f"HTML export failed: {exc}") from exc

    def _build_html(self) -> str:
        r = self._report
        sections = []

        # --- System ---
        s = r.system
        sections.append(_section("System", [
            ("Hostname", s.hostname), ("Username", s.username),
            ("OS", f"{s.os_name} {s.os_release} ({s.os_architecture})"),
            ("OS Version", s.os_version), ("Python", s.python_version),
            ("Boot Time", s.boot_time), ("Uptime", s.uptime),
            ("Administrator", _yn(s.is_admin)), ("MAC Address", s.mac_address),
        ]))

        # --- CPU ---
        c = r.cpu
        freq = c.frequency
        freq_str = f"{freq.current_mhz} MHz (max {freq.max_mhz})" if freq else "N/A"
        sections.append(_section("CPU", [
            ("Name", c.name), ("Vendor", c.vendor),
            ("Architecture", c.architecture),
            ("Physical Cores", c.physical_cores), ("Logical Cores", c.logical_cores),
            ("Frequency", freq_str), ("Usage %", f"{c.usage_percent}%"),
            ("Context Switches", f"{c.stats.context_switches:,}"),
        ]))

        # --- Memory ---
        m = r.memory
        sections.append(_section("Memory", [
            ("Total GB", m.total_gb), ("Used GB", m.used_gb),
            ("Available GB", m.available_gb), ("Usage %", f"{m.usage_percent}%"),
            ("Swap Total GB", m.swap_total_gb), ("Swap Used GB", m.swap_used_gb),
            ("Swap %", f"{m.swap_percent}%"),
        ]))

        # --- Disk ---
        disk_rows = "".join(
            f"<tr><td>{p.mount_point}</td><td>{p.filesystem}</td>"
            f"<td>{p.total_gb}</td><td>{p.used_gb}</td>"
            f"<td>{p.free_gb}</td><td>{p.usage_percent}%</td></tr>"
            for p in r.disk.partitions
        )
        disk_table = (
            "<table><thead><tr>"
            "<th>Mount</th><th>FS</th><th>Total GB</th>"
            "<th>Used GB</th><th>Free GB</th><th>Usage %</th>"
            "</tr></thead><tbody>" + disk_rows + "</tbody></table>"
        )
        sections.append(_raw_section("Disk", disk_table))

        # --- GPU ---
        if r.gpu.available and r.gpu.devices:
            gpu_rows = "".join(
                f"<tr><td>{d.id}</td><td>{d.name}</td><td>{d.load_percent}%</td>"
                f"<td>{d.memory_total_mb}</td><td>{d.memory_used_mb}</td>"
                f"<td>{d.temperature_c}°C</td><td>{d.driver}</td></tr>"
                for d in r.gpu.devices
            )
            gpu_table = (
                "<table><thead><tr>"
                "<th>ID</th><th>Name</th><th>Load %</th>"
                "<th>VRAM Total MB</th><th>VRAM Used MB</th>"
                "<th>Temp °C</th><th>Driver</th>"
                "</tr></thead><tbody>" + gpu_rows + "</tbody></table>"
            )
            sections.append(_raw_section("GPU", gpu_table))
        else:
            sections.append(_raw_section("GPU", "<p>No NVIDIA GPU detected.</p>"))

        # --- Network ---
        net_rows = "".join(
            f"<tr><td>{i.name}</td><td>{'UP' if i.is_up else 'DOWN'}</td>"
            f"<td>{', '.join(i.ipv4_addresses) or '—'}</td>"
            f"<td>{i.mac_address}</td><td>{i.speed_mbps}</td></tr>"
            for i in r.network.interfaces
        )
        net_table = (
            f"<p>Hostname: <strong>{r.network.hostname}</strong>  "
            f"Active connections: <strong>{r.network.active_connections}</strong></p>"
            "<table><thead><tr><th>Interface</th><th>Status</th>"
            "<th>IPv4</th><th>MAC</th><th>Speed Mbps</th>"
            "</tr></thead><tbody>" + net_rows + "</tbody></table>"
        )
        sections.append(_raw_section("Network", net_table))

        # --- Software ---
        sw_rows = "".join(
            f"<tr><td>{e.name}</td>"
            f"<td class='{'ok' if e.installed else 'bad'}'>{'Yes' if e.installed else 'No'}</td>"
            f"<td>{e.version or '—'}</td></tr>"
            for e in r.software.entries
        )
        sw_table = (
            "<table><thead><tr><th>Software</th><th>Installed</th><th>Version</th>"
            "</tr></thead><tbody>" + sw_rows + "</tbody></table>"
        )
        sections.append(_raw_section("Installed Software", sw_table))

        # --- Package Managers ---
        pm_rows = "".join(
            f"<tr><td>{e.name}</td>"
            f"<td class='{'ok' if e.installed else 'bad'}'>{'Yes' if e.installed else 'No'}</td>"
            f"<td>{e.version or '—'}</td></tr>"
            for e in r.package_managers.entries
        )
        pm_table = (
            "<table><thead><tr><th>Manager</th><th>Installed</th><th>Version</th>"
            "</tr></thead><tbody>" + pm_rows + "</tbody></table>"
        )
        sections.append(_raw_section("Package Managers", pm_table))

        # --- Security ---
        sec = r.security
        fw = sec.firewall
        fw_str = (
            f"Domain: {'ON' if fw.domain_profile else 'OFF'}  "
            f"Private: {'ON' if fw.private_profile else 'OFF'}  "
            f"Public: {'ON' if fw.public_profile else 'OFF'}"
            if fw else "N/A"
        )
        sections.append(_section("Security", [
            ("Administrator", _yn(sec.is_admin)),
            ("UAC Enabled", _yn(sec.uac_enabled)),
            ("Antivirus", ", ".join(sec.antivirus_products) or "None"),
            ("Firewall", fw_str),
            ("Secure Boot", str(sec.secure_boot_enabled)),
            ("TPM Present", str(sec.tpm_present)),
        ]))

        # --- Health ---
        status_class = {
            "Healthy": "ok", "Warning": "warn", "Critical": "bad"
        }.get(r.health.overall_status, "")
        flag_rows = "".join(
            f"<tr class='{f.status}'><td>{f.category}</td><td>{f.status.upper()}</td><td>{f.message}</td></tr>"
            for f in r.health.flags
        )
        health_html = (
            f"<p>Overall Status: <strong class='{status_class}'>{r.health.overall_status}</strong></p>"
            "<table><thead><tr><th>Category</th><th>Status</th><th>Message</th>"
            "</tr></thead><tbody>" + flag_rows + "</tbody></table>"
        )
        sections.append(_raw_section("Health Summary", health_html))

        body = "\n".join(sections)
        return _html_page(PROJECT_NAME, PROJECT_VERSION, r.timestamp, body)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _section(title: str, rows: list) -> str:
    cells = "".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows
    )
    return f"<section><h2>{title}</h2><table><tbody>{cells}</tbody></table></section>"


def _raw_section(title: str, inner_html: str) -> str:
    return f"<section><h2>{title}</h2>{inner_html}</section>"


def _yn(value: bool) -> str:
    return "Yes" if value else "No"


def _html_page(name: str, version: str, timestamp: str, body: str) -> str:
    return textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{name} — Report</title>
      <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
          font-family: 'Segoe UI', system-ui, sans-serif;
          background: #0d1117; color: #c9d1d9;
          margin: 0; padding: 2rem;
        }}
        header {{ margin-bottom: 2rem; border-bottom: 1px solid #30363d; padding-bottom: 1rem; }}
        header h1 {{ margin: 0; color: #58a6ff; font-size: 1.8rem; }}
        header p  {{ margin: 0.3rem 0 0; color: #8b949e; }}
        section   {{ margin-bottom: 2rem; }}
        section h2 {{
          font-size: 1rem; text-transform: uppercase; letter-spacing: 0.08em;
          color: #58a6ff; border-bottom: 1px solid #21262d; padding-bottom: 0.4rem;
          margin-bottom: 0.6rem;
        }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th, td {{
          padding: 0.45rem 0.75rem; text-align: left;
          border-bottom: 1px solid #21262d;
        }}
        thead th {{ color: #8b949e; font-weight: 600; background: #161b22; }}
        tr:hover td {{ background: #1c2128; }}
        tbody tr th {{ color: #8b949e; font-weight: 500; width: 220px; white-space: nowrap; }}
        .ok   {{ color: #3fb950; }}
        .warn {{ color: #d29922; }}
        .bad  {{ color: #f85149; }}
        p {{ color: #8b949e; font-size: 0.875rem; }}
      </style>
    </head>
    <body>
      <header>
        <h1>{name}</h1>
        <p>Version {version} &nbsp;|&nbsp; Generated: {timestamp}</p>
      </header>
      {body}
    </body>
    </html>
    """)
