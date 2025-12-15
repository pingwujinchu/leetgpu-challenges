from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueueNames:
    """
    Keep queue naming stable across api/worker.

    We route primarily by gpu_vendor. Optionally extend by gpu_arch later:
      jobs:nvidia:sm80, jobs:amd:gfx90a, ...
    """

    prefix: str = "jobs"

    def for_vendor(self, vendor: str) -> str:
        v = (vendor or "any").strip().lower()
        if v in {"nvidia", "amd", "intel", "apple", "cpu", "any"}:
            return f"{self.prefix}:{v}"
        return f"{self.prefix}:any"

