"""
permissions.py

Permissions checker — probes what the current process can actually do:
admin elevation, access to the Windows event log, read access to
System32, and write access to the reports directory.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

from inspector.constants import REPORTS_DIR
from inspector.exceptions import InsufficientPermissionsError
from inspector.logger import get_logger
from inspector.models import PermissionsInfo
from inspector.utils import run_command

log = get_logger(__name__)


class PermissionChecker:
    """
    Probes runtime permissions and returns a :class:`~inspector.models.PermissionsInfo`.

    All checks are best-effort; a failed check returns False rather
    than raising an exception.
    """

    def inspect(self) -> PermissionsInfo:
        """
        Return a :class:`~inspector.models.PermissionsInfo`.
        """
        log.debug("Checking runtime permissions.")
        return PermissionsInfo(
            is_admin=self._is_admin(),
            can_read_event_logs=self._can_read_event_logs(),
            can_access_system32=self._can_access_system32(),
            can_write_reports_dir=self._can_write_reports_dir(),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_admin() -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @staticmethod
    def _can_read_event_logs() -> bool:
        """
        Try to read one record from the System event log via wevtutil.

        Requires elevation on most Windows configurations.
        """
        try:
            result = run_command(
                "wevtutil qe System /c:1 /rd:true /f:text", timeout=5
            )
            return result.success
        except Exception as exc:
            log.debug("Event log read check failed: %s", exc)
            return False

    @staticmethod
    def _can_access_system32() -> bool:
        """Check read access to %SystemRoot%\\System32."""
        try:
            system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
            return system32.is_dir() and os.access(system32, os.R_OK)
        except Exception as exc:
            log.debug("System32 access check failed: %s", exc)
            return False

    @staticmethod
    def _can_write_reports_dir() -> bool:
        """
        Check that the reports/ directory is writable by the current user.

        Attempts to create the directory first in case it does not exist.
        """
        try:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            test_file = REPORTS_DIR / ".permission_probe"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as exc:
            log.debug("Reports dir write check failed: %s", exc)
            return False
