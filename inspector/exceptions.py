"""
exceptions.py

Exception hierarchy for DevPilot System Inspector.

Every public-facing error raised by the SDK is a subclass of
InspectorError, so callers can catch the whole tree with a single
``except InspectorError`` or handle specific domains individually.
"""


class InspectorError(Exception):
    """Base exception for all SDK errors."""


# ---------------------------------------------------------------------------
# Inspection-domain errors
# ---------------------------------------------------------------------------

class HardwareInspectionError(InspectorError):
    """Raised when CPU, memory, disk, or GPU inspection fails."""


class SoftwareInspectionError(InspectorError):
    """Raised when installed-software or package-manager inspection fails."""


class NetworkInspectionError(InspectorError):
    """Raised when network interface or connectivity inspection fails."""


class ProcessInspectionError(InspectorError):
    """Raised when process enumeration fails."""


class ServiceInspectionError(InspectorError):
    """Raised when Windows service enumeration fails."""


class SecurityInspectionError(InspectorError):
    """Raised when security-posture inspection fails."""


class EnvironmentInspectionError(InspectorError):
    """Raised when environment-variable or PATH inspection fails."""


# ---------------------------------------------------------------------------
# Access / permission errors
# ---------------------------------------------------------------------------

class InsufficientPermissionsError(InspectorError):
    """
    Raised when an operation requires elevated (Administrator) privileges
    that the current process does not hold.
    """


# ---------------------------------------------------------------------------
# Export errors
# ---------------------------------------------------------------------------

class ExportError(InspectorError):
    """Raised when report export fails (I/O error, unsupported format, etc.)."""


class UnsupportedExportFormatError(ExportError):
    """Raised when an unsupported export format is requested."""

    def __init__(self, fmt: str, supported: list[str]) -> None:
        super().__init__(
            f"Unsupported export format '{fmt}'. "
            f"Supported formats: {', '.join(supported)}"
        )
        self.fmt = fmt
        self.supported = supported


# ---------------------------------------------------------------------------
# Analysis errors
# ---------------------------------------------------------------------------

class AnalysisError(InspectorError):
    """Raised when the top-level analyzer fails to produce a report."""
