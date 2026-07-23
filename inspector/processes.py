"""
processes.py

Process inspector — enumerates running processes and returns the
top N by CPU and memory usage.
"""

from __future__ import annotations

from typing import List

import psutil

from inspector.constants import TOP_PROCESSES_COUNT
from inspector.exceptions import ProcessInspectionError
from inspector.logger import get_logger
from inspector.models import ProcessEntry, ProcessesInfo
from inspector.utils import bytes_to_mb

log = get_logger(__name__)


class ProcessInspector:
    """
    Collects running process metadata and returns top-N by resource usage.

    Returns a :class:`~inspector.models.ProcessesInfo` containing the
    total process count and separate lists for CPU and memory leaders.
    """

    def inspect(self) -> ProcessesInfo:
        """
        Return a :class:`~inspector.models.ProcessesInfo`.

        Raises
        ------
        ProcessInspectionError
            If process enumeration fails critically.
        """
        log.debug("Collecting process information.")
        try:
            all_procs = self._gather_processes()
            return ProcessesInfo(
                total_count=len(all_procs),
                top_by_cpu=self._top_by_cpu(all_procs),
                top_by_memory=self._top_by_memory(all_procs),
            )
        except Exception as exc:
            log.error("Process inspection failed: %s", exc)
            raise ProcessInspectionError(
                f"Failed to collect process information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _gather_processes() -> List[ProcessEntry]:
        """
        Enumerate all accessible processes and convert to ProcessEntry objects.

        Processes that cannot be accessed (permission denied) are skipped.
        """
        entries: List[ProcessEntry] = []
        for proc in psutil.process_iter(["pid", "name", "status", "username"]):
            try:
                info = proc.info
                # Measure CPU and memory usage on-demand
                cpu = proc.cpu_percent(interval=0)  # non-blocking
                mem_bytes = proc.memory_info().rss

                entries.append(
                    ProcessEntry(
                        pid=info["pid"],
                        name=info["name"] or "Unknown",
                        status=info["status"] or "unknown",
                        cpu_percent=round(cpu, 1),
                        memory_mb=bytes_to_mb(mem_bytes),
                        username=info.get("username") or "N/A",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip inaccessible or transient processes
                pass
        return entries

    @staticmethod
    def _top_by_cpu(processes: List[ProcessEntry]) -> List[ProcessEntry]:
        """Return the top N processes by CPU usage (descending)."""
        return sorted(processes, key=lambda p: p.cpu_percent, reverse=True)[
            :TOP_PROCESSES_COUNT
        ]

    @staticmethod
    def _top_by_memory(processes: List[ProcessEntry]) -> List[ProcessEntry]:
        """Return the top N processes by memory usage (descending)."""
        return sorted(processes, key=lambda p: p.memory_mb, reverse=True)[
            :TOP_PROCESSES_COUNT
        ]
