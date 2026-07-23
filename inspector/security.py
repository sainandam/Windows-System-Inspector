"""
security.py

Security posture inspector — checks admin privileges, UAC status,
Windows Firewall profiles, registered antivirus products, Secure Boot,
and TPM presence.

All detections are best-effort; failures in individual checks degrade
gracefully (None / empty list) rather than aborting the inspection.
"""

from __future__ import annotations

import ctypes
import subprocess
from typing import List, Optional

from inspector.exceptions import SecurityInspectionError
from inspector.logger import get_logger
from inspector.models import FirewallStatus, SecurityInfo
from inspector.utils import run_command

log = get_logger(__name__)


class SecurityInspector:
    """
    Audits the security posture of the local Windows machine.

    Returns a :class:`~inspector.models.SecurityInfo`.
    """

    def inspect(self) -> SecurityInfo:
        """
        Return a :class:`~inspector.models.SecurityInfo`.

        Raises
        ------
        SecurityInspectionError
            If the overall inspection fails critically.
        """
        log.debug("Collecting security information.")
        try:
            return SecurityInfo(
                is_admin=self._is_admin(),
                uac_enabled=self._uac_enabled(),
                antivirus_products=self._antivirus_products(),
                firewall=self._firewall_status(),
                secure_boot_enabled=self._secure_boot(),
                tpm_present=self._tpm_present(),
            )
        except Exception as exc:
            log.error("Security inspection failed: %s", exc)
            raise SecurityInspectionError(
                f"Failed to collect security information: {exc}"
            ) from exc

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
    def _uac_enabled() -> bool:
        """
        Check if User Account Control is enabled via the registry.

        Reads HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System
        EnableLUA value (1 = enabled, 0 = disabled).
        """
        try:
            result = run_command(
                'reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion'
                '\\Policies\\System" /v EnableLUA',
                timeout=5,
            )
            if result.success and "0x1" in result.stdout:
                return True
            if result.success and "0x0" in result.stdout:
                return False
        except Exception as exc:
            log.debug("UAC registry check failed: %s", exc)
        return False

    @staticmethod
    def _antivirus_products() -> List[str]:
        """
        Query WMI SecurityCenter2 for registered antivirus products.

        Returns a list of product display names, or an empty list if
        WMI is unavailable or returns no results.
        """
        try:
            result = run_command(
                'powershell -NoProfile -Command "'
                'Get-CimInstance -Namespace root/SecurityCenter2 '
                '-ClassName AntiVirusProduct | '
                'Select-Object -ExpandProperty displayName"',
                timeout=10,
            )
            if result.success and result.stdout:
                return [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
        except Exception as exc:
            log.debug("Antivirus WMI query failed: %s", exc)
        return []

    @staticmethod
    def _firewall_status() -> Optional[FirewallStatus]:
        """
        Read Windows Firewall enabled state for all three profiles
        (Domain, Private, Public) via netsh.
        """
        try:
            result = run_command(
                "netsh advfirewall show allprofiles state", timeout=5
            )
            if not result.success:
                return None

            output = result.stdout.lower()
            domain = _profile_on(output, "domain")
            private = _profile_on(output, "private")
            public = _profile_on(output, "public")

            return FirewallStatus(
                domain_profile=domain,
                private_profile=private,
                public_profile=public,
            )
        except Exception as exc:
            log.debug("Firewall status check failed: %s", exc)
            return None

    @staticmethod
    def _secure_boot() -> Optional[bool]:
        """
        Detect Secure Boot state via PowerShell Confirm-SecureBootUEFI.

        Returns True/False/None (None = indeterminate / non-UEFI system).
        """
        try:
            result = run_command(
                "powershell -NoProfile -Command Confirm-SecureBootUEFI",
                timeout=5,
            )
            if result.success:
                return result.stdout.strip().lower() == "true"
        except Exception as exc:
            log.debug("Secure boot check failed: %s", exc)
        return None

    @staticmethod
    def _tpm_present() -> Optional[bool]:
        """
        Detect TPM presence via Get-Tpm PowerShell cmdlet.

        Returns True/False/None (None = cmdlet not available).
        """
        try:
            result = run_command(
                'powershell -NoProfile -Command '
                '"(Get-Tpm).TpmPresent"',
                timeout=5,
            )
            if result.success and result.stdout:
                return result.stdout.strip().lower() == "true"
        except Exception as exc:
            log.debug("TPM detection failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _profile_on(output: str, profile: str) -> bool:
    """
    Parse a single firewall profile state from netsh output.

    netsh advfirewall output format:
        Domain Profile Settings:
        ----
        State                ON
        ...
        Private Profile Settings:
        ...

    We find the profile header line, then scan subsequent lines for the
    first ``State`` entry and read its value.
    """
    lines = output.splitlines()
    in_profile = False
    for line in lines:
        stripped = line.strip().lower()
        # Detect the profile section header, e.g. "domain profile settings:"
        if profile in stripped and "profile" in stripped:
            in_profile = True
            continue
        if in_profile:
            # Stop at the next profile section header
            if "profile settings" in stripped:
                break
            if stripped.startswith("state"):
                return "on" in stripped
    return False
