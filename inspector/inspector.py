"""
inspector.py

Public API entry point for the DevPilot System Inspector SDK.

This is the only class SDK consumers should import::

    from inspector import SystemInspector

    report = SystemInspector().analyze()
    print(report.cpu.name)
    print(report.memory.total_gb)
    print(report.disk.partitions[0].free_gb)
    print(report.software.get("Git").version)

The class is intentionally thin — it delegates all work to
:class:`~inspector.analyzer.Analyzer` and exposes a stable,
well-documented public interface.
"""

from __future__ import annotations

from inspector.analyzer import Analyzer
from inspector.exceptions import AnalysisError
from inspector.logger import get_logger
from inspector.models import InspectionReport

log = get_logger(__name__)


class SystemInspector:
    """
    Primary SDK entry point.

    Instantiate once and call :meth:`analyze` to collect a complete
    snapshot of the Windows system state.

    Parameters
    ----------
    None — all configuration is driven by constants.py.

    Examples
    --------
    Basic usage::

        from inspector import SystemInspector

        report = SystemInspector().analyze()
        print(report.health.overall_status)

    Accessing specific domains::

        inspector = SystemInspector()
        report    = inspector.analyze()

        # CPU
        print(report.cpu.name)
        print(report.cpu.usage_percent)

        # Memory
        print(report.memory.total_gb)
        print(report.memory.usage_percent)

        # Disk partitions
        for partition in report.disk.partitions:
            print(partition.mount_point, partition.free_gb, "GB free")

        # Software
        git = report.software.get("Git")
        if git and git.installed:
            print("Git version:", git.version)

        # Package managers
        pip = report.package_managers.get("pip")
        if pip and pip.installed:
            print("pip version:", pip.version)

        # Health
        for flag in report.health.flags:
            print(flag.category, flag.status, flag.message)
    """

    def __init__(self) -> None:
        self._analyzer = Analyzer()

    def analyze(self) -> InspectionReport:
        """
        Run a complete system inspection and return an
        :class:`~inspector.models.InspectionReport`.

        This method is the single entry point for the entire SDK.
        It is safe to call multiple times; each call produces a fresh
        snapshot.

        Returns
        -------
        InspectionReport
            A strongly-typed dataclass containing every domain's data.

        Raises
        ------
        AnalysisError
            Only on a catastrophic failure that prevents report assembly.
            Individual inspector failures are handled gracefully and
            never surface here.
        """
        log.info("SystemInspector.analyze() called.")
        report = self._analyzer.run()
        log.info("Analysis complete — overall status: %s", report.health.overall_status)
        return report
