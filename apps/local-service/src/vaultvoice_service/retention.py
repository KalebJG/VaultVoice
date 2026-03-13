from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    mode: str = "memory_only"

    def assert_memory_only(self) -> None:
        if self.mode != "memory_only":
            raise ValueError("Only memory_only retention mode is permitted in MVP")


def assert_no_persistence_target(path: str | Path) -> None:
    """Guard against introducing transcript/audio persistence writes in MVP."""
    raise RuntimeError(
        f"Persistence blocked by policy for path: {Path(path)}"
    )
