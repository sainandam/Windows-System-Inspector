"""
gpu.py

GPU inspector — detects NVIDIA GPUs via GPUtil and falls back
gracefully when no compatible GPU or driver is present.

GPUtil only supports NVIDIA hardware. On systems without a supported
GPU the inspector still returns a valid GPUInfo with available=False
and an empty device list, so the rest of the pipeline is never broken.
"""

from __future__ import annotations

from typing import List

from inspector.exceptions import HardwareInspectionError
from inspector.logger import get_logger
from inspector.models import GPUDevice, GPUInfo

log = get_logger(__name__)


class GPUInspector:
    """
    Detects GPU devices and returns a :class:`~inspector.models.GPUInfo`.

    Relies on GPUtil for NVIDIA hardware.  When GPUtil raises (no NVIDIA
    driver, no CUDA, etc.) the result is a valid object with
    ``available=False`` and ``devices=[]`` rather than an exception.
    """

    def inspect(self) -> GPUInfo:
        """
        Return a :class:`~inspector.models.GPUInfo`.

        Never raises — missing GPU is a valid state, not an error.
        """
        log.debug("Collecting GPU information.")
        try:
            import GPUtil  # local import so the rest of the SDK works without it

            gpus = GPUtil.getGPUs()
            if not gpus:
                log.debug("No NVIDIA GPUs detected by GPUtil.")
                return GPUInfo(available=False, devices=[])

            devices = [self._build_device(gpu) for gpu in gpus]
            return GPUInfo(available=True, devices=devices)

        except ImportError:
            log.warning("GPUtil is not installed — GPU detection skipped.")
            return GPUInfo(available=False, devices=[])
        except Exception as exc:
            # Non-fatal: GPU absence should not abort a full inspection.
            log.warning("GPU detection failed: %s", exc)
            return GPUInfo(available=False, devices=[])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_device(gpu: object) -> GPUDevice:
        """Convert a GPUtil GPU object to a :class:`GPUDevice` dataclass."""
        return GPUDevice(
            id=gpu.id,
            name=gpu.name,
            load_percent=round(gpu.load * 100, 1),
            memory_total_mb=round(gpu.memoryTotal, 1),
            memory_used_mb=round(gpu.memoryUsed, 1),
            memory_free_mb=round(gpu.memoryFree, 1),
            temperature_c=round(gpu.temperature, 1),
            driver=gpu.driver,
        )
