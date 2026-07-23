"""
software.py

Software inspector — probes the system PATH for a curated list of
developer tools and returns their install state and version.

The list of executables to check lives entirely in constants.py so
new tools can be added without changing any logic here.
"""

from __future__ import annotations

from typing import List, Optional

from inspector.constants import COMMON_SOFTWARE, SOFTWARE_DISPLAY_NAMES
from inspector.exceptions import SoftwareInspectionError
from inspector.logger import get_logger
from inspector.models import SoftwareEntry, SoftwareInfo
from inspector.utils import command_exists, get_command_version, run_command

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Per-executable version-flag overrides.
# Most tools respond to --version; exceptions are listed here.
# ---------------------------------------------------------------------------
_VERSION_FLAGS: dict[str, str] = {
    "java": "-version",
    "node": "--version",
    "mongod": "--version",
    "redis-server": "--version",
    "go": "version",
    "dotnet": "--version",
    "rustc": "--version",
    "cargo": "--version",
}

# Tools that are known to be slow to start (e.g. JVM, Node via NVM).
# These get a longer timeout so we don't prematurely give up.
_SLOW_TOOLS: dict[str, int] = {
    "java": 15,
    "node": 15,
    "dotnet": 15,
}

# Some tools write version output to stderr (e.g. java -version)
_STDERR_TOOLS: set[str] = {"java"}


class SoftwareInspector:
    """
    Probes installed developer software by querying the system PATH.

    For each executable in :data:`~inspector.constants.COMMON_SOFTWARE`
    the inspector checks existence, then attempts to read a version string.
    Results are returned as a :class:`~inspector.models.SoftwareInfo`.
    """

    def inspect(self) -> SoftwareInfo:
        """
        Return a :class:`~inspector.models.SoftwareInfo`.

        Raises
        ------
        SoftwareInspectionError
            If the overall probe cannot be completed.
        """
        log.debug("Collecting installed software information.")
        try:
            entries = [self._probe(exe) for exe in COMMON_SOFTWARE]
            return SoftwareInfo(entries=entries)
        except Exception as exc:
            log.error("Software inspection failed: %s", exc)
            raise SoftwareInspectionError(
                f"Failed to collect software information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _probe(self, executable: str) -> SoftwareEntry:
        """
        Probe a single executable and return a :class:`SoftwareEntry`.

        Parameters
        ----------
        executable:
            The bare executable name, e.g. ``"git"`` or ``"node"``.
        """
        display_name = SOFTWARE_DISPLAY_NAMES.get(executable, executable.capitalize())

        if not command_exists(executable):
            log.debug("Not found on PATH: %s", executable)
            return SoftwareEntry(
                name=display_name,
                installed=False,
                version=None,
                path=None,
            )

        path = self._resolve_path(executable)
        version = self._resolve_version(executable)
        log.debug("Found %s — version: %s, path: %s", display_name, version, path)

        return SoftwareEntry(
            name=display_name,
            installed=True,
            version=version,
            path=path,
        )

    @staticmethod
    def _resolve_path(executable: str) -> Optional[str]:
        """Return the full filesystem path of *executable*, or None."""
        result = run_command(f"where {executable}", timeout=5)
        if result.success and result.stdout:
            # `where` may return multiple lines; take the first.
            return result.stdout.splitlines()[0].strip()
        return None

    @staticmethod
    def _resolve_version(executable: str) -> Optional[str]:
        """
        Return a cleaned version string for *executable*, or None.

        Handles tools that write version info to stderr (e.g. ``java``),
        and tools that are slow to start (e.g. ``node`` via NVM).
        """
        flag = _VERSION_FLAGS.get(executable, "--version")
        timeout = _SLOW_TOOLS.get(executable, 5)
        result = run_command(f"{executable} {flag}", timeout=timeout)

        # Some tools (java) write to stderr even on success
        raw = result.stdout or ""
        if executable in _STDERR_TOOLS and result.stderr:
            raw = result.stderr

        if not raw:
            return None

        # Return only the first non-empty line, stripped of extra whitespace
        first_line = next(
            (line.strip() for line in raw.splitlines() if line.strip()), None
        )
        return first_line
