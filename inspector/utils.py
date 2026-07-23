"""
utils.py

Shared utility helpers for DevPilot System Inspector.

Rules:
- No logging configuration here — use logger.get_logger(__name__).
- No module-level side-effects beyond the logger instance.
- All helpers are pure or wrap a single OS concern.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from inspector.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

@dataclass
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int


def run_command(command: str, timeout: int = 10) -> CommandResult:
    """
    Execute a shell command and return a structured result.

    Parameters
    ----------
    command:
        The command string to execute via the system shell.
    timeout:
        Seconds to wait before killing the subprocess.  Defaults to 10.

    Returns
    -------
    CommandResult
        Always returns a result; never raises on subprocess failure.
    """
    log.debug("Running command: %s", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired:
        log.warning("Command timed out after %ds: %s", timeout, command)
        return CommandResult(
            success=False,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            returncode=-1,
        )
    except Exception as exc:
        log.error("Command execution failed: %s — %s", command, exc)
        return CommandResult(
            success=False,
            stdout="",
            stderr=str(exc),
            returncode=-1,
        )


def command_exists(executable: str) -> bool:
    """
    Return True if *executable* is on the system PATH.

    Uses ``where`` on Windows.
    """
    result = run_command(f"where {executable}", timeout=5)
    return result.success


def get_command_version(executable: str, flag: str = "--version") -> Optional[str]:
    """
    Return the first line of ``<executable> <flag>`` output, or None.

    Parameters
    ----------
    executable:
        The program to query, e.g. ``"git"``.
    flag:
        The version flag.  Defaults to ``"--version"``.
    """
    result = run_command(f"{executable} {flag}", timeout=5)
    if result.success and result.stdout:
        return result.stdout.splitlines()[0].strip()
    return None


# ---------------------------------------------------------------------------
# Unit conversion helpers
# ---------------------------------------------------------------------------

def bytes_to_gb(value: int) -> float:
    """Convert bytes to gigabytes, rounded to 2 decimal places."""
    return round(value / (1024 ** 3), 2)


def bytes_to_mb(value: int) -> float:
    """Convert bytes to megabytes, rounded to 2 decimal places."""
    return round(value / (1024 ** 2), 2)


def bytes_to_kb(value: int) -> float:
    """Convert bytes to kilobytes, rounded to 2 decimal places."""
    return round(value / 1024, 2)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> Path:
    """
    Create *path* (and any missing parents) if it does not exist.

    Returns the path for chaining.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def truncate(text: str, max_length: int = 60) -> str:
    """Return *text* truncated to *max_length* characters with an ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def safe_first_line(text: str) -> str:
    """Return the first non-empty line of *text*, or an empty string."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
