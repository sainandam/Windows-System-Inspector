"""
analyzer.py

Orchestration engine — instantiates every domain inspector, runs them
in sequence, evaluates health, and assembles the final InspectionReport.

Design notes:
- Each inspector runs inside an individual try/except so one failure
  does not abort the entire analysis.
- The health evaluator runs last so it can assess the complete report.
- Timestamps and version are stamped here rather than in individual
  inspectors to keep them pure data-collection modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from inspector.constants import (
    CPU_CRIT_PERCENT,
    CPU_WARN_PERCENT,
    DISK_CRIT_PERCENT,
    DISK_WARN_PERCENT,
    MEMORY_CRIT_PERCENT,
    MEMORY_WARN_PERCENT,
    OVERALL_CRITICAL,
    OVERALL_HEALTHY,
    OVERALL_WARNING,
    PROJECT_VERSION,
    STATUS_CRITICAL,
    STATUS_OK,
    STATUS_WARNING,
    SWAP_CRIT_PERCENT,
    SWAP_WARN_PERCENT,
)
from inspector.cpu import CPUInspector
from inspector.disk import DiskInspector
from inspector.environment import EnvironmentInspector
from inspector.exceptions import AnalysisError
from inspector.gpu import GPUInspector
from inspector.logger import get_logger
from inspector.memory import MemoryInspector
from inspector.models import (
    CPUInfo,
    DiskInfo,
    EnvironmentInfo,
    GPUInfo,
    HealthFlag,
    HealthSummary,
    InspectionReport,
    MemoryInfo,
    NetworkInfo,
    PackageManagerInfo,
    PermissionsInfo,
    ProcessesInfo,
    SecurityInfo,
    ServicesInfo,
    SoftwareInfo,
    SystemInfo,
)
from inspector.network import NetworkInspector
from inspector.package_managers import PackageManagerInspector
from inspector.permissions import PermissionChecker
from inspector.processes import ProcessInspector
from inspector.security import SecurityInspector
from inspector.services import ServiceInspector
from inspector.software import SoftwareInspector
from inspector.system import SystemInspector as _SystemInspector

log = get_logger(__name__)


class Analyzer:
    """
    Orchestrates all domain inspectors and produces an
    :class:`~inspector.models.InspectionReport`.

    Usage::

        report = Analyzer().run()
        print(report.cpu.name)
        print(report.memory.total_gb)

    Each domain is collected independently; a failure in one inspector
    is logged and a safe default is substituted so the rest of the
    report remains usable.
    """

    def run(self) -> InspectionReport:
        """
        Execute all inspectors and return a complete :class:`InspectionReport`.

        Raises
        ------
        AnalysisError
            Only if the report cannot be assembled at all (catastrophic
            failure).  Individual inspector failures are non-fatal.
        """
        log.info("Starting full system inspection.")
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            system = self._run("system", _SystemInspector().inspect, _default_system)
            cpu = self._run("cpu", CPUInspector().inspect, _default_cpu)
            memory = self._run("memory", MemoryInspector().inspect, _default_memory)
            disk = self._run("disk", DiskInspector().inspect, _default_disk)
            gpu = self._run("gpu", GPUInspector().inspect, _default_gpu)
            network = self._run("network", NetworkInspector().inspect, _default_network)
            software = self._run("software", SoftwareInspector().inspect, _default_software)
            package_managers = self._run(
                "package_managers",
                PackageManagerInspector().inspect,
                _default_package_managers,
            )
            processes = self._run("processes", ProcessInspector().inspect, _default_processes)
            services = self._run("services", ServiceInspector().inspect, _default_services)
            security = self._run("security", SecurityInspector().inspect, _default_security)
            environment = self._run(
                "environment", EnvironmentInspector().inspect, _default_environment
            )
            permissions = self._run(
                "permissions", PermissionChecker().inspect, _default_permissions
            )

            health = HealthEvaluator(cpu, memory, disk, security).evaluate()

            report = InspectionReport(
                system=system,
                cpu=cpu,
                memory=memory,
                disk=disk,
                gpu=gpu,
                network=network,
                software=software,
                package_managers=package_managers,
                processes=processes,
                services=services,
                security=security,
                environment=environment,
                permissions=permissions,
                health=health,
                timestamp=timestamp,
                inspector_version=PROJECT_VERSION,
            )
            log.info("System inspection complete — status: %s", health.overall_status)
            return report

        except Exception as exc:
            log.error("Fatal error during analysis: %s", exc)
            raise AnalysisError(f"Analysis failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run(name: str, fn, default_fn):
        """
        Run *fn* and return its result.  On any exception, log a warning
        and return the result of *default_fn* instead.
        """
        try:
            log.debug("Running inspector: %s", name)
            return fn()
        except Exception as exc:
            log.warning("Inspector '%s' failed — using defaults. Error: %s", name, exc)
            return default_fn()


# ---------------------------------------------------------------------------
# Health evaluator
# ---------------------------------------------------------------------------

class HealthEvaluator:
    """
    Evaluates the health of the system based on collected metrics and
    produces a :class:`~inspector.models.HealthSummary`.
    """

    def __init__(
        self,
        cpu: CPUInfo,
        memory: MemoryInfo,
        disk: DiskInfo,
        security: SecurityInfo,
    ) -> None:
        self._cpu = cpu
        self._memory = memory
        self._disk = disk
        self._security = security

    def evaluate(self) -> HealthSummary:
        flags: List[HealthFlag] = []

        flags.extend(self._check_cpu())
        flags.extend(self._check_memory())
        flags.extend(self._check_disk())
        flags.extend(self._check_security())

        overall = self._overall_status(flags)
        return HealthSummary(overall_status=overall, flags=flags)

    # ------------------------------------------------------------------

    def _check_cpu(self) -> List[HealthFlag]:
        flags = []
        usage = self._cpu.usage_percent
        if usage >= CPU_CRIT_PERCENT:
            flags.append(HealthFlag("CPU", STATUS_CRITICAL, f"CPU usage is critical: {usage}%"))
        elif usage >= CPU_WARN_PERCENT:
            flags.append(HealthFlag("CPU", STATUS_WARNING, f"CPU usage is high: {usage}%"))
        else:
            flags.append(HealthFlag("CPU", STATUS_OK, f"CPU usage normal: {usage}%"))
        return flags

    def _check_memory(self) -> List[HealthFlag]:
        flags = []
        usage = self._memory.usage_percent
        if usage >= MEMORY_CRIT_PERCENT:
            flags.append(HealthFlag("Memory", STATUS_CRITICAL, f"Memory usage is critical: {usage}%"))
        elif usage >= MEMORY_WARN_PERCENT:
            flags.append(HealthFlag("Memory", STATUS_WARNING, f"Memory usage is high: {usage}%"))
        else:
            flags.append(HealthFlag("Memory", STATUS_OK, f"Memory usage normal: {usage}%"))

        swap = self._memory.swap_percent
        if swap >= SWAP_CRIT_PERCENT:
            flags.append(HealthFlag("Swap", STATUS_CRITICAL, f"Swap usage is critical: {swap}%"))
        elif swap >= SWAP_WARN_PERCENT:
            flags.append(HealthFlag("Swap", STATUS_WARNING, f"Swap usage is elevated: {swap}%"))
        return flags

    def _check_disk(self) -> List[HealthFlag]:
        flags = []
        for partition in self._disk.partitions:
            usage = partition.usage_percent
            label = partition.mount_point
            if usage >= DISK_CRIT_PERCENT:
                flags.append(
                    HealthFlag("Disk", STATUS_CRITICAL, f"Disk {label} nearly full: {usage}%")
                )
            elif usage >= DISK_WARN_PERCENT:
                flags.append(
                    HealthFlag("Disk", STATUS_WARNING, f"Disk {label} usage high: {usage}%")
                )
            else:
                flags.append(
                    HealthFlag("Disk", STATUS_OK, f"Disk {label} usage normal: {usage}%")
                )
        return flags

    def _check_security(self) -> List[HealthFlag]:
        flags = []
        if not self._security.antivirus_products:
            flags.append(
                HealthFlag("Security", STATUS_WARNING, "No registered antivirus product detected.")
            )
        else:
            av_list = ", ".join(self._security.antivirus_products)
            flags.append(
                HealthFlag("Security", STATUS_OK, f"Antivirus detected: {av_list}")
            )

        fw = self._security.firewall
        if fw is not None:
            if fw.public_profile:
                flags.append(HealthFlag("Firewall", STATUS_OK, "Public firewall profile is ON."))
            else:
                flags.append(
                    HealthFlag("Firewall", STATUS_WARNING, "Public firewall profile is OFF.")
                )
        return flags

    @staticmethod
    def _overall_status(flags: List[HealthFlag]) -> str:
        statuses = {f.status for f in flags}
        if STATUS_CRITICAL in statuses:
            return OVERALL_CRITICAL
        if STATUS_WARNING in statuses:
            return OVERALL_WARNING
        return OVERALL_HEALTHY


# ---------------------------------------------------------------------------
# Safe defaults — returned when an individual inspector raises
# ---------------------------------------------------------------------------

def _default_system() -> SystemInfo:
    return SystemInfo(
        hostname="unknown", username="unknown", mac_address="unknown",
        boot_time="unknown", uptime="unknown", os_name="unknown",
        os_release="unknown", os_version="unknown", os_architecture="unknown",
        os_platform="unknown", python_version="unknown",
        is_admin=False, machine="unknown", node="unknown",
    )

def _default_cpu() -> CPUInfo:
    from inspector.models import CPUStats
    return CPUInfo(
        name="unknown", vendor="unknown", architecture="unknown",
        physical_cores=0, logical_cores=0, frequency=None,
        usage_percent=0.0, usage_per_core=[],
        stats=CPUStats(0, 0, 0, 0), load_average=None,
    )


def _default_memory() -> MemoryInfo:
    return MemoryInfo(
        total_gb=0.0, available_gb=0.0, used_gb=0.0, free_gb=0.0,
        usage_percent=0.0, swap_total_gb=0.0, swap_used_gb=0.0,
        swap_free_gb=0.0, swap_percent=0.0,
    )


def _default_disk() -> DiskInfo:
    return DiskInfo(partitions=[], io_counters=None)


def _default_gpu() -> GPUInfo:
    return GPUInfo(available=False, devices=[])


def _default_network() -> NetworkInfo:
    return NetworkInfo(
        hostname="unknown", fqdn="unknown",
        interfaces=[], io_counters=None, active_connections=0,
    )


def _default_software() -> SoftwareInfo:
    return SoftwareInfo(entries=[])


def _default_package_managers() -> PackageManagerInfo:
    return PackageManagerInfo(entries=[])


def _default_processes() -> ProcessesInfo:
    return ProcessesInfo(total_count=0, top_by_cpu=[], top_by_memory=[])


def _default_services() -> ServicesInfo:
    return ServicesInfo(total_count=0, running_count=0, stopped_count=0, entries=[])


def _default_security() -> SecurityInfo:
    return SecurityInfo(
        is_admin=False, uac_enabled=False, antivirus_products=[],
        firewall=None, secure_boot_enabled=None, tpm_present=None,
    )


def _default_environment() -> EnvironmentInfo:
    return EnvironmentInfo(
        variables={}, path_entries=[], temp_dir="", home_dir="",
        user_profile="", system_drive="", program_files="",
        program_files_x86="",
    )


def _default_permissions() -> PermissionsInfo:
    return PermissionsInfo(
        is_admin=False, can_read_event_logs=False,
        can_access_system32=False, can_write_reports_dir=False,
    )
