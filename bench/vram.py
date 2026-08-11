"""GPU VRAM sampling via nvidia-smi.

Windows WDDM does not expose per-process GPU memory through nvidia-smi, so this measures
whole-card memory.used and reports it net of an idle baseline. Sample the baseline right
before a run: other processes on this machine may already hold VRAM.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from dataclasses import dataclass, field


def query_used_mb() -> float:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return float(out.stdout.strip().splitlines()[0])


@dataclass
class VramSummary:
    baseline_mb: float
    peak_mb: float
    peak_delta_mb: float
    samples: int


class VramPoller:
    """Background poller: `async with VramPoller(interval) as p: ...` then p.summary()."""

    def __init__(self, interval_sec: float = 0.5):
        self.interval_sec = interval_sec
        self.baseline_mb: float = 0.0
        self._peak_mb: float = 0.0
        self._samples = 0
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def __aenter__(self) -> "VramPoller":
        self.baseline_mb = query_used_mb()
        self._peak_mb = self.baseline_mb
        self._samples = 1
        self._stop.clear()
        self._task = asyncio.create_task(self._poll_loop())
        return self

    async def __aexit__(self, *exc):
        self._stop.set()
        if self._task:
            await self._task

    async def _poll_loop(self):
        while not self._stop.is_set():
            try:
                used = query_used_mb()
                self._peak_mb = max(self._peak_mb, used)
                self._samples += 1
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_sec)
            except asyncio.TimeoutError:
                pass

    def summary(self) -> VramSummary:
        return VramSummary(
            baseline_mb=self.baseline_mb,
            peak_mb=self._peak_mb,
            peak_delta_mb=self._peak_mb - self.baseline_mb,
            samples=self._samples,
        )


def check_baseline(warn_threshold_mb: float = 2048.0) -> float:
    """One-shot baseline check for CLI use -- prints a warning if other processes hold significant VRAM."""
    used = query_used_mb()
    if used > warn_threshold_mb:
        print(
            f"[WARN] Idle VRAM baseline is {used:.0f} MB (> {warn_threshold_mb:.0f} MB threshold). "
            "Another process may be using the GPU -- results will record this baseline, "
            "but consider closing other GPU workloads for cleaner numbers."
        )
    else:
        print(f"Idle VRAM baseline: {used:.0f} MB")
    return used


if __name__ == "__main__":
    check_baseline()
