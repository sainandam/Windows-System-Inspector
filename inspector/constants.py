"""
constants.py

Project-wide constants for DevPilot System Inspector.
All magic values live here; nothing is hardcoded in modules.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project Metadata
# ---------------------------------------------------------------------------

PROJECT_NAME: str = "DevPilot System Inspector"
PROJECT_VERSION: str = "1.0.0"
AUTHOR: str = "Sai Kiran"
GITHUB_URL: str = "https://github.com/saikiran/devpilot-system-inspector"

# ---------------------------------------------------------------------------
# Directory Layout
# ---------------------------------------------------------------------------

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
INSPECTOR_DIR: Path = ROOT_DIR / "inspector"
REPORTS_DIR: Path = ROOT_DIR / "reports"
SCREENSHOTS_DIR: Path = ROOT_DIR / "screenshots"
LOG_FILE: Path = REPORTS_DIR / "system_inspector.log"

# Report output paths (overridable at runtime via Exporter)
JSON_REPORT: Path = REPORTS_DIR / "system_report.json"
HTML_REPORT: Path = REPORTS_DIR / "system_report.html"
CSV_REPORT: Path = REPORTS_DIR / "system_report.csv"

# ---------------------------------------------------------------------------
# Supported Package Managers
# Ordered by priority for detection.
# ---------------------------------------------------------------------------

PACKAGE_MANAGERS: list[str] = [
    "winget",
    "choco",
    "scoop",
    "pip",
    "npm",
    "yarn",
    "cargo",
    "gem",
    "go",
]

# ---------------------------------------------------------------------------
# Software to detect
# Extend freely; no code changes required elsewhere.
# ---------------------------------------------------------------------------

COMMON_SOFTWARE: list[str] = [
    "git",
    "python",
    "python3",
    "java",
    "node",
    "npm",
    "docker",
    "code",          # VS Code
    "postman",
    "mysql",
    "psql",          # PostgreSQL
    "mongod",        # MongoDB
    "redis-server",
    "kubectl",
    "terraform",
    "ansible",
    "rustc",
    "cargo",
    "go",
    "dotnet",
]

# Human-readable names mapped from executable names
SOFTWARE_DISPLAY_NAMES: dict[str, str] = {
    "git": "Git",
    "python": "Python",
    "python3": "Python 3",
    "java": "Java",
    "node": "Node.js",
    "npm": "npm",
    "docker": "Docker",
    "code": "Visual Studio Code",
    "postman": "Postman",
    "mysql": "MySQL",
    "psql": "PostgreSQL",
    "mongod": "MongoDB",
    "redis-server": "Redis",
    "kubectl": "Kubernetes CLI",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "rustc": "Rust",
    "cargo": "Cargo",
    "go": "Go",
    "dotnet": ".NET SDK",
}

# ---------------------------------------------------------------------------
# Process Inspector
# ---------------------------------------------------------------------------

TOP_PROCESSES_COUNT: int = 10   # top N by CPU and by memory

# ---------------------------------------------------------------------------
# Health Thresholds
# ---------------------------------------------------------------------------

CPU_WARN_PERCENT: float = 75.0
CPU_CRIT_PERCENT: float = 90.0

MEMORY_WARN_PERCENT: float = 75.0
MEMORY_CRIT_PERCENT: float = 90.0

DISK_WARN_PERCENT: float = 80.0
DISK_CRIT_PERCENT: float = 95.0

SWAP_WARN_PERCENT: float = 50.0
SWAP_CRIT_PERCENT: float = 80.0

# ---------------------------------------------------------------------------
# Status Labels
# ---------------------------------------------------------------------------

STATUS_OK: str = "ok"
STATUS_WARNING: str = "warning"
STATUS_CRITICAL: str = "critical"

OVERALL_HEALTHY: str = "Healthy"
OVERALL_WARNING: str = "Warning"
OVERALL_CRITICAL: str = "Critical"

# ---------------------------------------------------------------------------
# Export Formats
# ---------------------------------------------------------------------------

EXPORT_JSON: str = "json"
EXPORT_CSV: str = "csv"
EXPORT_HTML: str = "html"

SUPPORTED_EXPORT_FORMATS: list[str] = [EXPORT_JSON, EXPORT_CSV, EXPORT_HTML]
