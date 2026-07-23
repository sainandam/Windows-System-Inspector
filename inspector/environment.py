"""
environment.py

Environment inspector — reads environment variables, PATH entries,
and well-known Windows directory variables.
"""

from __future__ import annotations

import os
from typing import Dict, List

from inspector.exceptions import EnvironmentInspectionError
from inspector.logger import get_logger
from inspector.models import EnvironmentInfo

log = get_logger(__name__)

# Well-known Windows env vars that are always shown on the dashboard.
# Presence is not guaranteed on every Windows edition, so each is
# accessed with a safe fallback.
_KNOWN_VARS = (
    "TEMP",
    "TMP",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "WINDIR",
    "ProgramFiles",
    "ProgramFiles(x86)",
    "APPDATA",
    "LOCALAPPDATA",
    "ComSpec",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "OS",
)


class EnvironmentInspector:
    """
    Reads environment variables and PATH from the current process.

    Returns a :class:`~inspector.models.EnvironmentInfo`.
    """

    def inspect(self) -> EnvironmentInfo:
        """
        Return a :class:`~inspector.models.EnvironmentInfo`.

        Raises
        ------
        EnvironmentInspectionError
            If environment data cannot be collected.
        """
        log.debug("Collecting environment information.")
        try:
            env = dict(os.environ)
            path_entries = self._path_entries(env)

            return EnvironmentInfo(
                variables=env,
                path_entries=path_entries,
                temp_dir=env.get("TEMP") or env.get("TMP", ""),
                home_dir=env.get("USERPROFILE", ""),
                user_profile=env.get("USERPROFILE", ""),
                system_drive=env.get("SYSTEMDRIVE", ""),
                program_files=env.get("ProgramFiles", ""),
                program_files_x86=env.get("ProgramFiles(x86)", ""),
            )
        except Exception as exc:
            log.error("Environment inspection failed: %s", exc)
            raise EnvironmentInspectionError(
                f"Failed to collect environment information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _path_entries(env: Dict[str, str]) -> List[str]:
        """
        Split the PATH variable into individual directory entries.

        Strips empty strings and deduplicates while preserving order.
        """
        raw_path = env.get("PATH") or env.get("Path", "")
        seen: set[str] = set()
        entries: List[str] = []
        for entry in raw_path.split(os.pathsep):
            normalized = entry.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                entries.append(normalized)
        return entries
