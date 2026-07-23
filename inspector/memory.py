"""
memory.py

Memory inspector — collects physical RAM and swap statistics.
"""

from __future__ import annotations

import psutil

from inspector.exceptions import HardwareInspectionError
from inspector.logger import get_logger
from inspector.models import MemoryInfo
from inspector.utils import bytes_to_gb

log = get_logger(__name__)


class MemoryInspector:
    """
    Collects virtual memory and swap statistics via psutil and returns
    a :class:`~inspector.models.MemoryInfo`.
    """

    def inspect(self) -> MemoryInfo:
        """
        Return a fully-populated :class:`~inspector.models.MemoryInfo`.

        Raises
        ------
        HardwareInspectionError
            If memory statistics cannot be retrieved.
        """
        log.debug("Collecting memory information.")
        try:
            vm = psutil.virtual_memory()
            sw = psutil.swap_memory()

            return MemoryInfo(
                total_gb=bytes_to_gb(vm.total),
                available_gb=bytes_to_gb(vm.available),
                used_gb=bytes_to_gb(vm.used),
                free_gb=bytes_to_gb(vm.free),
                usage_percent=vm.percent,
                swap_total_gb=bytes_to_gb(sw.total),
                swap_used_gb=bytes_to_gb(sw.used),
                swap_free_gb=bytes_to_gb(sw.free),
                swap_percent=sw.percent,
            )
        except Exception as exc:
            log.error("Memory inspection failed: %s", exc)
            raise HardwareInspectionError(
                f"Failed to collect memory information: {exc}"
            ) from exc
