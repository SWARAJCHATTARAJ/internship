"""Best-effort process and host resource sampling without mandatory GPU support."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ResourceSnapshot:
    elapsed_seconds: float
    process_cpu_percent: float | None = None
    system_cpu_percent: float | None = None
    system_ram_percent: float | None = None
    process_memory_mb: float | None = None
    peak_process_memory_mb: float | None = None
    gpu_utilization_percent: float | None = None
    gpu_memory_used_mb: float | None = None
    gpu_memory_total_mb: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResourceMonitor:
    """Sample psutil and, when already available, PyTorch CUDA statistics."""

    def __init__(self, interval_seconds: float = 0.1) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start = 0.0
        self._process: Any = None
        self._peak_rss = 0
        self._current_rss = 0
        self._process_cpu = 0.0
        self._system_cpu = 0.0
        self._process_cpu_total = 0.0
        self._system_cpu_total = 0.0
        self._cpu_samples = 0
        self._system_ram = 0.0
        self._sampled = False
        self._gpu_utilization: float | None = None
        self._gpu_memory_used: float | None = None
        self._gpu_memory_total: float | None = None

    def __enter__(self) -> "ResourceMonitor":
        self._start = time.perf_counter()
        try:
            import psutil

            self._process = psutil.Process()
            self._process.cpu_percent(None)
            self._sample()
            self._thread = threading.Thread(target=self._sample_loop, daemon=True)
            self._thread.start()
        except ImportError:
            self._process = None
        return self

    def _sample(self) -> None:
        if self._process is None:
            return
        try:
            import psutil

            self._process_cpu = self._process.cpu_percent(None)
            self._system_cpu = psutil.cpu_percent(None)
            self._process_cpu_total += self._process_cpu
            self._system_cpu_total += self._system_cpu
            self._cpu_samples += 1
            self._system_ram = psutil.virtual_memory().percent
            self._current_rss = self._process.memory_info().rss
            self._peak_rss = max(self._peak_rss, self._current_rss)
            self._sampled = True
        except (OSError, psutil.Error):
            return

    def _sample_gpu(self) -> None:
        try:
            import torch

            if not torch.cuda.is_available():
                return
            free, total = torch.cuda.mem_get_info()
            self._gpu_memory_total = total / (1024 * 1024)
            self._gpu_memory_used = (total - free) / (1024 * 1024)
            try:
                import pynvml
            except ImportError:
                return
            try:
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(torch.cuda.current_device())
                self._gpu_utilization = float(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu)
            except (pynvml.NVMLError, OSError, RuntimeError):
                self._gpu_utilization = None
        except (ImportError, RuntimeError, OSError, AttributeError, ValueError):
            return

    def _sample_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._sample()

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
        self._sample()
        self._sample_gpu()

    def snapshot(self) -> ResourceSnapshot:
        process_memory = self._current_rss / (1024 * 1024) if self._sampled else None
        peak_memory = self._peak_rss / (1024 * 1024) if self._sampled else None
        return ResourceSnapshot(
            elapsed_seconds=max(0.0, time.perf_counter() - self._start),
            process_cpu_percent=self._process_cpu_total / self._cpu_samples if self._cpu_samples else None,
            system_cpu_percent=self._system_cpu_total / self._cpu_samples if self._cpu_samples else None,
            system_ram_percent=self._system_ram if self._sampled else None,
            process_memory_mb=process_memory,
            peak_process_memory_mb=peak_memory,
            gpu_utilization_percent=self._gpu_utilization,
            gpu_memory_used_mb=self._gpu_memory_used,
            gpu_memory_total_mb=self._gpu_memory_total,
        )


def system_information() -> dict[str, Any]:
    """Return observed hardware/runtime details; unknown values remain null."""
    import platform
    import sys

    information: dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "operating_system": platform.platform(),
        "cpu": platform.processor() or None,
        "cpu_count": None,
        "ram_total_mb": None,
        "gpu": None,
    }
    try:
        import psutil

        information["cpu_count"] = psutil.cpu_count()
        information["ram_total_mb"] = psutil.virtual_memory().total / (1024 * 1024)
    except ImportError:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            properties = torch.cuda.get_device_properties(torch.cuda.current_device())
            information["gpu"] = {
                "name": properties.name,
                "memory_total_mb": properties.total_memory / (1024 * 1024),
            }
    except (ImportError, RuntimeError, OSError, AttributeError, ValueError):
        pass
    return information
