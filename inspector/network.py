"""
network.py

Network inspector — enumerates physical and virtual interfaces,
their IP addresses, link state, and aggregate I/O counters.
"""

from __future__ import annotations

import socket
from typing import List, Optional

import psutil

from inspector.exceptions import NetworkInspectionError
from inspector.logger import get_logger
from inspector.models import NetworkInfo, NetworkInterface, NetworkIOCounters

log = get_logger(__name__)

# Address family constants (portable across Python versions)
_AF_INET = socket.AF_INET
_AF_INET6 = socket.AF_INET6
try:
    import psutil._common  # noqa: F401
    _AF_LINK = psutil.AF_LINK
except AttributeError:
    _AF_LINK = -1


class NetworkInspector:
    """
    Collects network interface metadata and I/O statistics.

    Returns a :class:`~inspector.models.NetworkInfo` containing every
    detected interface with its addresses and a live-connection count.
    """

    def inspect(self) -> NetworkInfo:
        """
        Return a fully-populated :class:`~inspector.models.NetworkInfo`.

        Raises
        ------
        NetworkInspectionError
            If interface enumeration fails critically.
        """
        log.debug("Collecting network information.")
        try:
            return NetworkInfo(
                hostname=socket.gethostname(),
                fqdn=socket.getfqdn(),
                interfaces=self._interfaces(),
                io_counters=self._io_counters(),
                active_connections=self._active_connections(),
            )
        except Exception as exc:
            log.error("Network inspection failed: %s", exc)
            raise NetworkInspectionError(
                f"Failed to collect network information: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _interfaces() -> List[NetworkInterface]:
        """
        Build a list of network interfaces with address and stats info.

        Merges ``net_if_addrs()`` and ``net_if_stats()`` keyed by name.
        """
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        interfaces: List[NetworkInterface] = []

        for name, addr_list in addrs.items():
            mac = ""
            ipv4: List[str] = []
            ipv6: List[str] = []

            for addr in addr_list:
                if addr.family == _AF_INET:
                    ipv4.append(addr.address)
                elif addr.family == _AF_INET6:
                    # Strip scope id suffix (e.g. %eth0) for readability
                    ipv6.append(addr.address.split("%")[0])
                elif addr.family == _AF_LINK:
                    mac = addr.address or ""

            stat = stats.get(name)
            is_up = stat.isup if stat else False
            speed = stat.speed if stat else 0
            mtu = stat.mtu if stat else 0

            interfaces.append(
                NetworkInterface(
                    name=name,
                    mac_address=mac,
                    ipv4_addresses=ipv4,
                    ipv6_addresses=ipv6,
                    is_up=is_up,
                    speed_mbps=speed,
                    mtu=mtu,
                )
            )

        return interfaces

    @staticmethod
    def _io_counters() -> Optional[NetworkIOCounters]:
        """Return aggregate network I/O counters, or None if unavailable."""
        try:
            counters = psutil.net_io_counters()
            if counters is None:
                return None
            return NetworkIOCounters(
                bytes_sent=counters.bytes_sent,
                bytes_recv=counters.bytes_recv,
                packets_sent=counters.packets_sent,
                packets_recv=counters.packets_recv,
                errors_in=counters.errin,
                errors_out=counters.errout,
                drop_in=counters.dropin,
                drop_out=counters.dropout,
            )
        except Exception as exc:
            log.warning("Network I/O counters unavailable: %s", exc)
            return None

    @staticmethod
    def _active_connections() -> int:
        """
        Return the count of active TCP/UDP connections.

        Falls back to 0 on permission errors (common without elevation).
        """
        try:
            return len(psutil.net_connections())
        except (psutil.AccessDenied, PermissionError) as exc:
            log.debug("Cannot count connections (elevation required): %s", exc)
            return 0
        except Exception as exc:
            log.warning("Failed to count active connections: %s", exc)
            return 0
