"""
services.py

Windows service inspector — enumerates SCM services, their status,
start type, and the PID of the hosting process when running.

Uses psutil.win_service_iter() which wraps the Windows Service Control
Manager via the Win32 API.  Falls back gracefully on non-Windows or on
permission errors.
"""

from __future__ import annotations

from typing import List, Optional

import psutil

from inspector.exceptions import ServiceInspectionError
from inspector.logger import get_logger
from inspector.models import ServiceEntry, ServicesInfo

log = get_logger(__name__)

# Status strings as returned by psutil on Windows
_STATUS_RUNNING = "running"
_STATUS_STOPPED = "stopped"


class ServiceInspector:
    """
    Enumerates Windows services via the Service Control Manager.

    Returns a :class:`~inspector.models.ServicesInfo` with aggregate
    counts and a flat list of every service entry.
    """

    def inspect(self) -> ServicesInfo:
        """
        Return a :class:`~inspector.models.ServicesInfo`.

        Raises
        ------
        ServiceInspectionError
            If service enumeration fails critically.
        """
        log.debug("Collecting Windows services information.")
        try:
            entries = self._enumerate_services()
            running = sum(1 for s in entries if s.status == _STATUS_RUNNING)
            stopped = sum(1 for s in entries if s.status == _STATUS_STOPPED)

            return ServicesInfo(
                total_count=len(entries),
                running_count=running,
                stopped_count=stopped,
                entries=entries,
            )
        except Exception as exc:
            log.error("Service inspection failed: %s", exc)
            raise ServiceInspectionError(
                f"Failed to collect service information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _enumerate_services() -> List[ServiceEntry]:
        """
        Iterate all Windows services and convert to ServiceEntry objects.

        Services that cannot be opened individually are skipped with a
        warning rather than aborting the whole enumeration.
        """
        entries: List[ServiceEntry] = []

        try:
            service_iter = psutil.win_service_iter()
        except (AttributeError, psutil.AccessDenied) as exc:
            log.warning("Cannot enumerate services: %s", exc)
            return entries

        for svc in service_iter:
            try:
                info = svc.as_dict()
                entries.append(
                    ServiceEntry(
                        name=info.get("name", ""),
                        display_name=info.get("display_name", ""),
                        status=info.get("status", "unknown"),
                        start_type=info.get("start_type", "unknown"),
                        pid=info.get("pid"),
                    )
                )
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                log.debug("Skipping inaccessible service: %s", getattr(svc, "name", "?"))
            except Exception as exc:
                log.warning("Failed to read service entry: %s", exc)

        return entries
