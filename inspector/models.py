"""
models.py

Strongly-typed dataclasses for every inspection domain.

These are the canonical data contracts for the entire SDK.
All inspectors return instances of these models; no raw dicts
are exposed through the public API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

@dataclass
class CPUFrequency:
    current_mhz: float
    min_mhz: float
    max_mhz: float


@dataclass
class CPUStats:
    context_switches: int
    interrupts: int
    soft_interrupts: int
    syscalls: int


@dataclass
class CPUInfo:
    name: str
    vendor: str
    architecture: str
    physical_cores: int
    logical_cores: int
    frequency: Optional[CPUFrequency]
    usage_percent: float
    usage_per_core: List[float]
    stats: CPUStats
    load_average: Optional[tuple]


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@dataclass
class MemoryInfo:
    total_gb: float
    available_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_free_gb: float
    swap_percent: float


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

@dataclass
class DiskPartition:
    device: str
    mount_point: str
    filesystem: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float


@dataclass
class DiskIOCounters:
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int
    read_time_ms: int
    write_time_ms: int


@dataclass
class DiskInfo:
    partitions: List[DiskPartition]
    io_counters: Optional[DiskIOCounters]


# ---------------------------------------------------------------------------
# GPU
# ---------------------------------------------------------------------------

@dataclass
class GPUDevice:
    id: int
    name: str
    load_percent: float
    memory_total_mb: float
    memory_used_mb: float
    memory_free_mb: float
    temperature_c: float
    driver: str


@dataclass
class GPUInfo:
    available: bool
    devices: List[GPUDevice]


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

@dataclass
class NetworkInterface:
    name: str
    mac_address: str
    ipv4_addresses: List[str]
    ipv6_addresses: List[str]
    is_up: bool
    speed_mbps: int
    mtu: int


@dataclass
class NetworkIOCounters:
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drop_in: int
    drop_out: int


@dataclass
class NetworkInfo:
    hostname: str
    fqdn: str
    interfaces: List[NetworkInterface]
    io_counters: Optional[NetworkIOCounters]
    active_connections: int


# ---------------------------------------------------------------------------
# System / OS
# ---------------------------------------------------------------------------

@dataclass
class SystemInfo:
    hostname: str
    username: str
    mac_address: str
    boot_time: str
    uptime: str
    os_name: str
    os_release: str
    os_version: str
    os_architecture: str
    os_platform: str
    python_version: str
    is_admin: bool
    machine: str
    node: str


# ---------------------------------------------------------------------------
# Software
# ---------------------------------------------------------------------------

@dataclass
class SoftwareEntry:
    name: str
    installed: bool
    version: Optional[str]
    path: Optional[str]


@dataclass
class SoftwareInfo:
    entries: List[SoftwareEntry]

    def get(self, name: str) -> Optional[SoftwareEntry]:
        """Case-insensitive lookup by software name."""
        name_lower = name.lower()
        for entry in self.entries:
            if entry.name.lower() == name_lower:
                return entry
        return None


# ---------------------------------------------------------------------------
# Package Managers
# ---------------------------------------------------------------------------

@dataclass
class PackageManagerEntry:
    name: str
    installed: bool
    version: Optional[str]
    executable: Optional[str]


@dataclass
class PackageManagerInfo:
    entries: List[PackageManagerEntry]

    def get(self, name: str) -> Optional[PackageManagerEntry]:
        """Case-insensitive lookup by package manager name."""
        name_lower = name.lower()
        for entry in self.entries:
            if entry.name.lower() == name_lower:
                return entry
        return None


# ---------------------------------------------------------------------------
# Processes
# ---------------------------------------------------------------------------

@dataclass
class ProcessEntry:
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float
    username: str


@dataclass
class ProcessesInfo:
    total_count: int
    top_by_cpu: List[ProcessEntry]
    top_by_memory: List[ProcessEntry]


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@dataclass
class ServiceEntry:
    name: str
    display_name: str
    status: str
    start_type: str
    pid: Optional[int]


@dataclass
class ServicesInfo:
    total_count: int
    running_count: int
    stopped_count: int
    entries: List[ServiceEntry]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

@dataclass
class FirewallStatus:
    domain_profile: bool
    private_profile: bool
    public_profile: bool


@dataclass
class SecurityInfo:
    is_admin: bool
    uac_enabled: bool
    antivirus_products: List[str]
    firewall: Optional[FirewallStatus]
    secure_boot_enabled: Optional[bool]
    tpm_present: Optional[bool]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@dataclass
class EnvironmentInfo:
    variables: Dict[str, str]
    path_entries: List[str]
    temp_dir: str
    home_dir: str
    user_profile: str
    system_drive: str
    program_files: str
    program_files_x86: str


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@dataclass
class PermissionsInfo:
    is_admin: bool
    can_read_event_logs: bool
    can_access_system32: bool
    can_write_reports_dir: bool


# ---------------------------------------------------------------------------
# Health Summary
# ---------------------------------------------------------------------------

@dataclass
class HealthFlag:
    category: str
    status: str       # "ok" | "warning" | "critical"
    message: str


@dataclass
class HealthSummary:
    overall_status: str   # "Healthy" | "Warning" | "Critical"
    flags: List[HealthFlag]


# ---------------------------------------------------------------------------
# Top-level Inspection Report
# ---------------------------------------------------------------------------

@dataclass
class InspectionReport:
    """
    The single strongly-typed object returned by SystemInspector.analyze().

    Every field is populated by the corresponding inspector; nothing is
    left as a raw dict.
    """
    system: SystemInfo
    cpu: CPUInfo
    memory: MemoryInfo
    disk: DiskInfo
    gpu: GPUInfo
    network: NetworkInfo
    software: SoftwareInfo
    package_managers: PackageManagerInfo
    processes: ProcessesInfo
    services: ServicesInfo
    security: SecurityInfo
    environment: EnvironmentInfo
    permissions: PermissionsInfo
    health: HealthSummary
    timestamp: str
    inspector_version: str
