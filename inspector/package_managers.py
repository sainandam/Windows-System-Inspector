"""
package_managers.py

Package manager inspector — detects winget, choco, scoop, pip, npm,
cargo, etc., and reads their versions if installed.

The list of package managers lives in constants.py.
"""

from __future__ import annotations

from typing import List, Optional

from inspector.constants import PACKAGE_MANAGERS
from inspector.exceptions import SoftwareInspectionError
from inspector.logger import get_logger
from inspector.models import PackageManagerEntry, PackageManagerInfo
from inspector.utils import command_exists, get_command_version, run_command

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Per-manager version-flag overrides.
# Most package managers respond to --version; exceptions are listed here.
# ---------------------------------------------------------------------------
_VERSION_FLAGS: dict[str, str] = {
    "pip": "--version",
    "npm": "--version",
    "yarn": "--version",
    "cargo": "--version",
    "gem": "--version",
    "go": "version",
    "choco": "--version",
    
}


class PackageManagerInspector:
    """
    Probes installed package managers by querying the system PATH.

    For each entry in :data:`~inspector.constants.PACKAGE_MANAGERS`
    the inspector checks existence, then attempts to read a version string.
    Results are returned as a :class:`~inspector.models.PackageManagerInfo`.
    """

    def inspect(self) -> PackageManagerInfo:
        """
        Return a :class:`~inspector.models.PackageManagerInfo`.

        Raises
        ------
        SoftwareInspectionError
            If the overall probe cannot be completed.
        """
        log.debug("Collecting installed package managers.")
        try:
            entries = [self._probe(pm) for pm in PACKAGE_MANAGERS]
            return PackageManagerInfo(entries=entries)
        except Exception as exc:
            log.error("Package manager inspection failed: %s", exc)
            raise SoftwareInspectionError(
                f"Failed to collect package manager information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _probe(self, pm_name: str) -> PackageManagerEntry:
        """
        Probe a single package manager and return a
        :class:`~inspector.models.PackageManagerEntry`.

        Parameters
        ----------
        pm_name:
            The bare executable name, e.g. ``"winget"`` or ``"npm"``.
        """
        if not command_exists(pm_name):
            log.debug("Package manager not found: %s", pm_name)
            return PackageManagerEntry(
                name=pm_name,
                installed=False,
                version=None,
                executable=None,
            )

        exe_path = self._resolve_path(pm_name)
        version = self._resolve_version(pm_name)
        log.debug("Found %s — version: %s, path: %s", pm_name, version, exe_path)

        return PackageManagerEntry(
            name=pm_name,
            installed=True,
            version=version,
            executable=exe_path,
        )

    @staticmethod
    def _resolve_path(pm_name: str) -> Optional[str]:
        """Return the full filesystem path of *pm_name*, or None."""
        result = run_command(f"where {pm_name}", timeout=5)
        if result.success and result.stdout:
            # `where` may return multiple lines; take the first.
            return result.stdout.splitlines()[0].strip()
        return None

    @staticmethod
    def _resolve_version(pm_name: str) -> Optional[str]:
        """
        Return a cleaned version string for *pm_name*, or None.
        """
        flag = _VERSION_FLAGS.get(pm_name, "--version")
        result = run_command(f"{pm_name} {flag}", timeout=5)

        if not result.success or not result.stdout:
            return None

        # Return only the first non-empty line
        first_line = next(
            (line.strip() for line in result.stdout.splitlines() if line.strip()),
            None,
        )
        return first_line
