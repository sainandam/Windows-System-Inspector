"""
disk.py

Disk inspector — enumerates all mounted partitions and optionally
collects I/O counters (reads, writes, times).
"""

from __future__ import annotations

from typing import List, Optional

import psutil

from inspector.exceptions import HardwareInspectionError
from inspector.logger import get_logger
from inspector.models import DiskInfo, DiskIOCounters, DiskPartition
from inspector.utils import bytes_to_gb

log = get_logger(__name__)


class DiskInspector:
    """
    Collects disk partition details and I/O counters.

    Returns a :class:`~inspector.models.DiskInfo` containing a list of
    partitions and optional I/O statistics.
    """

    def inspect(self) -> DiskInfo:
        """
        Return a fully-populated :class:`~inspector.models.DiskInfo`.

        Raises
        ------
        HardwareInspectionError
            If disk enumeration fails critically.
        """
        log.debug("Collecting disk information.")
        try:
            return DiskInfo(
                partitions=self._partitions(),
                io_counters=self._io_counters(),
            )
        except Exception as exc:
            log.error("Disk inspection failed: %s", exc)
            raise HardwareInspectionError(
                f"Failed to collect disk information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _partitions() -> List[DiskPartition]:
        """
        Enumerate all mounted partitions.

        On Windows this typically includes C:\\, D:\\, etc.
        Skips partitions where usage cannot be determined (access denied).
        """
        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append(
                    DiskPartition(
                        device=part.device,
                        mount_point=part.mountpoint,
                        filesystem=part.fstype,
                        total_gb=bytes_to_gb(usage.total),
                        used_gb=bytes_to_gb(usage.used),
                        free_gb=bytes_to_gb(usage.free),
                        usage_percent=usage.percent,
                    )
                )
            except PermissionError:
                log.warning("Access denied to partition %s — skipping.", part.device)
            except Exception as e:
                log.warning("Failed to read partition %s: %s", part.device, e)
        return partitions

    @staticmethod
    def _io_counters() -> Optional[DiskIOCounters]:
        """
        Return aggregate disk I/O counters, or None if unavailable.

        On Windows, psutil.disk_io_counters() aggregates all physical disks.
        """
        try:
            counters = psutil.disk_io_counters()
            if counters is None:
                return None
            return DiskIOCounters(
                read_bytes=counters.read_bytes,
                write_bytes=counters.write_bytes,
                read_count=counters.read_count,
                write_count=counters.write_count,
                read_time_ms=counters.read_time,
                write_time_ms=counters.write_time,
            )
        except Exception as e:
            log.warning("Disk I/O counters unavailable: %s", e)
            return None
