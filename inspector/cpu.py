"""
cpu.py

CPU inspector — collects processor identity, topology, frequency,
real-time utilisation, and kernel statistics.
"""

from __future__ import annotations

import platform
from typing import Optional

import psutil
import cpuinfo

from inspector.exceptions import HardwareInspectionError
from inspector.logger import get_logger
from inspector.models import CPUFrequency, CPUInfo, CPUStats

log = get_logger(__name__)


class CPUInspector:
    """
    Collects CPU information and returns a :class:`~inspector.models.CPUInfo`.

    ``cpuinfo.get_cpu_info()`` is slow (spawns a subprocess on some
    platforms), so it is called once during construction and cached.
    """

    def __init__(self) -> None:
        log.debug("Initialising CPUInspector — fetching cpuinfo (may take a moment).")
        self._raw: dict = cpuinfo.get_cpu_info()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def inspect(self) -> CPUInfo:
        """
        Return a fully-populated :class:`~inspector.models.CPUInfo`.

        Raises
        ------
        HardwareInspectionError
            If any critical CPU metric cannot be retrieved.
        """
        log.debug("Collecting CPU information.")
        try:
            return CPUInfo(
                name=self._name(),
                vendor=self._vendor(),
                architecture=self._architecture(),
                physical_cores=psutil.cpu_count(logical=False) or 0,
                logical_cores=psutil.cpu_count(logical=True) or 0,
                frequency=self._frequency(),
                usage_percent=psutil.cpu_percent(interval=1),
                usage_per_core=psutil.cpu_percent(interval=1, percpu=True),
                stats=self._stats(),
                load_average=self._load_average(),
            )
        except Exception as exc:
            log.error("CPU inspection failed: %s", exc)
            raise HardwareInspectionError(
                f"Failed to collect CPU information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _name(self) -> str:
        return self._raw.get("brand_raw", "Unknown")

    def _vendor(self) -> str:
        return self._raw.get("vendor_id_raw", "Unknown")

    def _architecture(self) -> str:
        return self._raw.get("arch", platform.machine())

    @staticmethod
    def _frequency() -> Optional[CPUFrequency]:
        freq = psutil.cpu_freq()
        if freq is None:
            return None
        return CPUFrequency(
            current_mhz=round(freq.current, 2),
            min_mhz=round(freq.min, 2),
            max_mhz=round(freq.max, 2),
        )

    @staticmethod
    def _stats() -> CPUStats:
        s = psutil.cpu_stats()
        return CPUStats(
            context_switches=s.ctx_switches,
            interrupts=s.interrupts,
            soft_interrupts=getattr(s, "soft_interrupts", 0),
            syscalls=getattr(s, "syscalls", 0),
        )

    @staticmethod
    def _load_average() -> Optional[tuple]:
        try:
            return psutil.getloadavg()
        except (AttributeError, OSError):
            # getloadavg() is not available on Windows prior to 3.9
            return None
