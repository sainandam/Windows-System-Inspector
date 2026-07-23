"""
dashboard.py

Rich-based professional CLI dashboard for DevPilot System Inspector.

Renders every inspection domain in its own panel with colour-coded
status indicators.  All rendering logic lives here; the rest of the
SDK has no Rich dependency.
"""

from __future__ import annotations

from typing import Optional

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

from inspector.constants import (
    OVERALL_CRITICAL,
    OVERALL_HEALTHY,
    OVERALL_WARNING,
    PROJECT_NAME,
    PROJECT_VERSION,
    STATUS_CRITICAL,
    STATUS_OK,
    STATUS_WARNING,
)
from inspector.models import InspectionReport

# Colour palette
_OK_STYLE = "bold green"
_WARN_STYLE = "bold yellow"
_CRIT_STYLE = "bold red"
_HEADER_STYLE = "bold cyan"
_DIM_STYLE = "dim"
_INSTALLED_STYLE = "green"
_MISSING_STYLE = "red"

console = Console()


class Dashboard:
    """
    Renders an :class:`~inspector.models.InspectionReport` to the terminal
    using Rich.

    Usage::

        from inspector.dashboard import Dashboard
        Dashboard(report).render()
    """

    def __init__(self, report: InspectionReport) -> None:
        self._r = report

   
    def render(self):
        self._print_header()

        # System Overview
        self._print_system()

        # Hardware Summary
        self._print_cpu_memory()
        self._print_disk()

        # Connectivity
        self._print_network()

        # Development Environment
        self._print_package_managers()
        self._print_software()

        # Security & Health
        # self._print_security()
        self._print_health()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _print_header(self) -> None:
        r = self._r
        title = Text(f"  {PROJECT_NAME}  v{PROJECT_VERSION}", style="bold white on dark_blue")
        subtitle = Text(
            f"  {r.system.hostname}  |  {r.system.username}  |  {r.timestamp}  |  "
            f"{r.system.os_name} {r.system.os_release}",
            style="dim",
        )
        console.print()
        console.print(Panel(title, subtitle=str(subtitle), box=box.DOUBLE, expand=True))
        console.print()

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def _print_system(self) -> None:
        s = self._r.system
        t = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        t.add_column("Key", style=_HEADER_STYLE, width=22)
        t.add_column("Value")

        rows = [
            ("Hostname", s.hostname),
            ("Username", s.username),
            ("Node", s.node),
            ("MAC Address", s.mac_address),
            ("OS", f"{s.os_name} {s.os_release}  ({s.os_architecture})"),
            ("OS Version", s.os_version),
            ("Platform", s.os_platform),
            ("Python", s.python_version),
            ("Boot Time", s.boot_time),
            ("Uptime", s.uptime),
            ("Administrator", _bool_icon(s.is_admin)),
        ]
        for key, val in rows:
            t.add_row(key, str(val))

        console.print(Panel(t, title="[bold]System[/bold]", box=box.ROUNDED))

    # ------------------------------------------------------------------
    # CPU + Memory side-by-side
    # ------------------------------------------------------------------

    def _print_cpu_memory(self) -> None:
        cpu_panel = self._cpu_table()
        mem_panel = self._memory_table()
        console.print(Columns([cpu_panel, mem_panel], equal=True, expand=True))

    def _cpu_table(self) -> Panel:
        c = self._r.cpu
        t = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        t.add_column("Key", style=_HEADER_STYLE, width=22)
        t.add_column("Value")

        freq = c.frequency
        freq_str = (
            f"{freq.current_mhz} MHz  (max {freq.max_mhz} MHz)"
            if freq else "N/A"
        )
        usage_style = _threshold_style(c.usage_percent, 75, 90)

        t.add_row("Name", c.name)
        t.add_row("Vendor", c.vendor)
        t.add_row("Architecture", c.architecture)
        t.add_row("Physical Cores", str(c.physical_cores))
        t.add_row("Logical Cores", str(c.logical_cores))
        t.add_row("Frequency", freq_str)
        t.add_row("Usage", Text(f"{c.usage_percent}%", style=usage_style))
        t.add_row(
            "Per-Core Usage",
            "  ".join(f"{v}%" for v in c.usage_per_core) or "N/A",
        )
        t.add_row("Context Switches", f"{c.stats.context_switches:,}")
        t.add_row("Interrupts", f"{c.stats.interrupts:,}")

        return Panel(t, title="[bold]CPU[/bold]", box=box.ROUNDED)

    def _memory_table(self) -> Panel:
        m = self._r.memory
        t = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        t.add_column("Key", style=_HEADER_STYLE, width=22)
        t.add_column("Value")

        ram_style = _threshold_style(m.usage_percent, 75, 90)
        swap_style = _threshold_style(m.swap_percent, 50, 80)

        t.add_row("Total RAM", f"{m.total_gb} GB")
        t.add_row("Used", f"{m.used_gb} GB")
        t.add_row("Available", f"{m.available_gb} GB")
        t.add_row("Free", f"{m.free_gb} GB")
        t.add_row("Usage", Text(f"{m.usage_percent}%", style=ram_style))
        t.add_row("", "")
        t.add_row("Swap Total", f"{m.swap_total_gb} GB")
        t.add_row("Swap Used", f"{m.swap_used_gb} GB")
        t.add_row("Swap Free", f"{m.swap_free_gb} GB")
        t.add_row("Swap Usage", Text(f"{m.swap_percent}%", style=swap_style))

        return Panel(t, title="[bold]Memory[/bold]", box=box.ROUNDED)

    # ------------------------------------------------------------------
    # Disk
    # ------------------------------------------------------------------

    def _print_disk(self) -> None:
        d = self._r.disk
        t = Table(box=box.SIMPLE, pad_edge=False)
        t.add_column("Drive", style=_HEADER_STYLE)
        t.add_column("FS")
        t.add_column("Total GB", justify="right")
        t.add_column("Used GB", justify="right")
        t.add_column("Free GB", justify="right")
        t.add_column("Usage %", justify="right")

        for part in d.partitions:
            style = _threshold_style(part.usage_percent, 80, 95)
            t.add_row(
                part.mount_point,
                part.filesystem or "N/A",
                str(part.total_gb),
                str(part.used_gb),
                str(part.free_gb),
                Text(f"{part.usage_percent}%", style=style),
            )

        if d.io_counters:
            io = d.io_counters
            io_text = (
                f"  Reads: {io.read_count:,}  ({io.read_bytes // (1024**2):,} MB)   "
                f"Writes: {io.write_count:,}  ({io.write_bytes // (1024**2):,} MB)"
            )
            console.print(Panel(t, title="[bold]Disk Partitions[/bold]", subtitle=io_text, box=box.ROUNDED))
        else:
            console.print(Panel(t, title="[bold]Disk Partitions[/bold]", box=box.ROUNDED))

    # ------------------------------------------------------------------
    # GPU
    # ------------------------------------------------------------------

    def _print_gpu(self) -> None:
        g = self._r.gpu
        if not g.available or not g.devices:
            console.print(
                Panel(
                    Text("No NVIDIA GPU detected or driver unavailable.", style=_DIM_STYLE),
                    title="[bold]GPU[/bold]",
                    box=box.ROUNDED,
                )
            )
            return

        t = Table(box=box.SIMPLE, pad_edge=False)
        t.add_column("ID")
        t.add_column("Name", style=_HEADER_STYLE)
        t.add_column("Load %", justify="right")
        t.add_column("VRAM Total MB", justify="right")
        t.add_column("VRAM Used MB", justify="right")
        t.add_column("VRAM Free MB", justify="right")
        t.add_column("Temp °C", justify="right")
        t.add_column("Driver")

        for dev in g.devices:
            t.add_row(
                str(dev.id),
                dev.name,
                f"{dev.load_percent}%",
                str(dev.memory_total_mb),
                str(dev.memory_used_mb),
                str(dev.memory_free_mb),
                str(dev.temperature_c),
                dev.driver,
            )

        console.print(Panel(t, title="[bold]GPU[/bold]", box=box.ROUNDED))

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------

    def _print_network(self) -> None:
        n = self._r.network
        t = Table(box=box.SIMPLE, pad_edge=False)
        t.add_column("Interface", style=_HEADER_STYLE)
        t.add_column("Status")
        t.add_column("IPv4")
        t.add_column("IPv6")
        t.add_column("MAC")
        t.add_column("Speed Mbps", justify="right")
        t.add_column("MTU", justify="right")

        for iface in n.interfaces:
            status = Text("UP", style=_OK_STYLE) if iface.is_up else Text("DOWN", style=_CRIT_STYLE)
            t.add_row(
                iface.name,
                status,
                "\n".join(iface.ipv4_addresses) or "—",
                "\n".join(iface.ipv6_addresses[:1]) or "—",  # show first IPv6 only
                iface.mac_address or "—",
                str(iface.speed_mbps) if iface.speed_mbps else "—",
                str(iface.mtu),
            )

        subtitle = (
            f"Hostname: {n.hostname}   FQDN: {n.fqdn}   "
            f"Active connections: {n.active_connections}"
        )
        console.print(
            Panel(t, title="[bold]Network Interfaces[/bold]", subtitle=subtitle, box=box.ROUNDED)
        )

    # ------------------------------------------------------------------
    # Installed Software
    # ------------------------------------------------------------------

    def _print_software(self) -> None:
        sw = self._r.software
        t = Table(box=box.SIMPLE, pad_edge=False)
        t.add_column("Software", style=_HEADER_STYLE, width=24)
        t.add_column("Status", width=12)
        t.add_column("Version")
        t.add_column("Path")

        for entry in sw.entries:
            if entry.installed:
                status = Text("Installed", style=_INSTALLED_STYLE)
                version = entry.version or "unknown"
                path = entry.path or "—"
            else:
                status = Text("Not found", style=_MISSING_STYLE)
                version = "—"
                path = "—"
            t.add_row(entry.name, status, version, path)

        console.print(Panel(t, title="[bold]Installed Software[/bold]", box=box.ROUNDED))

    # ------------------------------------------------------------------
    # Package Managers
    # ------------------------------------------------------------------

    def _print_package_managers(self) -> None:
        pm = self._r.package_managers
        t = Table(box=box.SIMPLE, pad_edge=False)
        t.add_column("Package Manager", style=_HEADER_STYLE, width=20)
        t.add_column("Status", width=12)
        t.add_column("Version")
        t.add_column("Executable")

        for entry in pm.entries:
            if entry.installed:
                status = Text("Installed", style=_INSTALLED_STYLE)
                version = entry.version or "unknown"
                exe = entry.executable or "—"
            else:
                status = Text("Not found", style=_MISSING_STYLE)
                version = "—"
                exe = "—"
            t.add_row(entry.name, status, version, exe)

        console.print(Panel(t, title="[bold]Package Managers[/bold]", box=box.ROUNDED))

    # ------------------------------------------------------------------
    # Top Processes
    # ------------------------------------------------------------------

    def _print_processes(self) -> None:
        p = self._r.processes
        subtitle = f"Total processes: {p.total_count}"

        cpu_table = Table(box=box.SIMPLE, pad_edge=False, title="Top by CPU")
        cpu_table.add_column("PID", justify="right")
        cpu_table.add_column("Name", style=_HEADER_STYLE)
        cpu_table.add_column("Status")
        cpu_table.add_column("CPU %", justify="right")
        cpu_table.add_column("Memory MB", justify="right")
        cpu_table.add_column("User")
        for proc in p.top_by_cpu:
            cpu_table.add_row(
                str(proc.pid), proc.name, proc.status,
                f"{proc.cpu_percent}%", str(proc.memory_mb), proc.username,
            )

        mem_table = Table(box=box.SIMPLE, pad_edge=False, title="Top by Memory")
        mem_table.add_column("PID", justify="right")
        mem_table.add_column("Name", style=_HEADER_STYLE)
        mem_table.add_column("Status")
        mem_table.add_column("CPU %", justify="right")
        mem_table.add_column("Memory MB", justify="right")
        mem_table.add_column("User")
        for proc in p.top_by_memory:
            mem_table.add_row(
                str(proc.pid), proc.name, proc.status,
                f"{proc.cpu_percent}%", str(proc.memory_mb), proc.username,
            )

        console.print(
            Panel(
                Columns([cpu_table, mem_table], equal=True, expand=True),
                title="[bold]Processes[/bold]",
                subtitle=subtitle,
                box=box.ROUNDED,
            )
        )


    # ------------------------------------------------------------------
    # Health Summary
    # ------------------------------------------------------------------

    def _print_health(self) -> None:
        h = self._r.health

        overall_style = {
            OVERALL_HEALTHY: _OK_STYLE,
            OVERALL_WARNING: _WARN_STYLE,
            OVERALL_CRITICAL: _CRIT_STYLE,
        }.get(h.overall_status, "white")

        t = Table(box=box.SIMPLE, pad_edge=False)
        t.add_column("Category", style=_HEADER_STYLE, width=14)
        t.add_column("Status", width=12)
        t.add_column("Message")

        status_styles = {
            STATUS_OK: _OK_STYLE,
            STATUS_WARNING: _WARN_STYLE,
            STATUS_CRITICAL: _CRIT_STYLE,
        }
        status_icons = {
            STATUS_OK: "✓",
            STATUS_WARNING: "⚠",
            STATUS_CRITICAL: "✗",
        }

        for flag in h.flags:
            style = status_styles.get(flag.status, "white")
            icon = status_icons.get(flag.status, "?")
            t.add_row(
                flag.category,
                Text(f"{icon} {flag.status.upper()}", style=style),
                flag.message,
            )

        overall_text = Text(
            f"  Overall Status: {h.overall_status}  ",
            style=f"bold white on {'dark_green' if h.overall_status == OVERALL_HEALTHY else 'dark_orange' if h.overall_status == OVERALL_WARNING else 'red'}",
        )
        console.print(
            Panel(
                t,
                title="[bold]Health Summary[/bold]",
                subtitle=str(overall_text),
                box=box.HEAVY,
            )
        )
        console.print()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _bool_icon(value: bool) -> Text:
    return Text("✓ Yes", style=_OK_STYLE) if value else Text("✗ No", style=_CRIT_STYLE)


def _tristate(value: Optional[bool]) -> Text:
    if value is True:
        return Text("✓ Yes", style=_OK_STYLE)
    if value is False:
        return Text("✗ No", style=_CRIT_STYLE)
    return Text("Unknown", style=_DIM_STYLE)


def _threshold_style(value: float, warn: float, crit: float) -> str:
    if value >= crit:
        return _CRIT_STYLE
    if value >= warn:
        return _WARN_STYLE
    return _OK_STYLE
