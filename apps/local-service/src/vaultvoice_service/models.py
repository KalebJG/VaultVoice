from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptResult:
    text: str
    is_final: bool
    confidence: float | None = None


@dataclass(slots=True)
class ServiceHealth:
    status: str
    retention_mode: str
