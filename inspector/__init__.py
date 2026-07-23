"""
DevPilot System Inspector
=========================

A production-quality Windows System Inspection SDK.

Public API
----------
The only import consumers need::

    from inspector import SystemInspector

    report = SystemInspector().analyze()
    print(report.cpu.name)
    print(report.memory.total_gb)
    print(report.disk.partitions[0].free_gb)
    print(report.health.overall_status)

All models are also re-exported here for type-annotation convenience::

    from inspector import InspectionReport, CPUInfo, MemoryInfo
"""

from inspector.inspector import SystemInspector
from inspector.models import (
    CPUFrequency,
    CPUInfo,
    CPUStats,
    DiskInfo,
    DiskIOCounters,
    DiskPartition,
    EnvironmentInfo,
    FirewallStatus,
    GPUDevice,
    GPUInfo,
    HealthFlag,
    HealthSummary,
    InspectionReport,
    MemoryInfo,
    NetworkInfo,
    NetworkInterface,
    NetworkIOCounters,
    PackageManagerEntry,
    PackageManagerInfo,
    PermissionsInfo,
    ProcessEntry,
    ProcessesInfo,
    SecurityInfo,
    ServiceEntry,
    ServicesInfo,
    SoftwareEntry,
    SoftwareInfo,
    SystemInfo,
)
from inspector.exceptions import (
    AnalysisError,
    EnvironmentInspectionError,
    ExportError,
    HardwareInspectionError,
    InspectorError,
    InsufficientPermissionsError,
    NetworkInspectionError,
    ProcessInspectionError,
    SecurityInspectionError,
    ServiceInspectionError,
    SoftwareInspectionError,
    UnsupportedExportFormatError,
)
from inspector.constants import PROJECT_NAME, PROJECT_VERSION

__all__ = [
    # Primary entry point
    "SystemInspector",
    # Report
    "InspectionReport",
    # Domain models
    "SystemInfo",
    "CPUInfo",
    "CPUFrequency",
    "CPUStats",
    "MemoryInfo",
    "DiskInfo",
    "DiskPartition",
    "DiskIOCounters",
    "GPUInfo",
    "GPUDevice",
    "NetworkInfo",
    "NetworkInterface",
    "NetworkIOCounters",
    "SoftwareInfo",
    "SoftwareEntry",
    "PackageManagerInfo",
    "PackageManagerEntry",
    "ProcessesInfo",
    "ProcessEntry",
    "ServicesInfo",
    "ServiceEntry",
    "SecurityInfo",
    "FirewallStatus",
    "EnvironmentInfo",
    "PermissionsInfo",
    "HealthSummary",
    "HealthFlag",
    # Exceptions
    "InspectorError",
    "HardwareInspectionError",
    "SoftwareInspectionError",
    "NetworkInspectionError",
    "ProcessInspectionError",
    "ServiceInspectionError",
    "SecurityInspectionError",
    "EnvironmentInspectionError",
    "InsufficientPermissionsError",
    "ExportError",
    "UnsupportedExportFormatError",
    "AnalysisError",
    # Metadata
    "PROJECT_NAME",
    "PROJECT_VERSION",
]
