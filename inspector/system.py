"""
system.py

Collects general system and operating-system information.

Merges the former os_info.py into a single cohesive inspector.
os_info.py is no longer needed and will be removed in the cleanup step.
"""

from __future__ import annotations

import ctypes
import getpass
import platform
import socket
import uuid
from datetime import datetime

import psutil

from inspector.exceptions import HardwareInspectionError
from inspector.logger import get_logger
from inspector.models import SystemInfo

log = get_logger(__name__)


class SystemInspector:
    """
    Collects host identity, OS metadata, uptime, and privilege level.

    All data is gathered once during construction so that repeated
    calls to ``inspect()`` are cheap.
    """

    def inspect(self) -> SystemInfo:
        """
        Return a fully-populated :class:`~inspector.models.SystemInfo`.

        Raises
        ------
        HardwareInspectionError
            If a critical piece of system information cannot be retrieved.
        """
        log.debug("Collecting system information.")
        try:
            return SystemInfo(
                hostname=self._hostname(),
                username=self._username(),
                mac_address=self._mac_address(),
                boot_time=self._boot_time(),
                uptime=self._uptime(),
                os_name=platform.system(),
                os_release=platform.release(),
                os_version=platform.version(),
                os_architecture=platform.architecture()[0],
                os_platform=platform.platform(),
                python_version=platform.python_version(),
                is_admin=self._is_admin(),
                machine=platform.machine(),
                node=platform.node(),
            )
        except Exception as exc:
            log.error("System inspection failed: %s", exc)
            raise HardwareInspectionError(
                f"Failed to collect system information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hostname() -> str:
        return socket.gethostname()

    @staticmethod
    def _username() -> str:
        return getpass.getuser()

    @staticmethod
    def _mac_address() -> str:
        """Return the primary MAC address in XX:XX:XX:XX:XX:XX format."""
        raw = uuid.getnode()
        octets = [
            "{:02x}".format((raw >> (8 * i)) & 0xFF)
            for i in reversed(range(6))
        ]
        return ":".join(octets).upper()

    @staticmethod
    def _boot_time() -> str:
        dt = datetime.fromtimestamp(psutil.boot_time())
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _uptime() -> str:
        boot = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @staticmethod
    def _is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
