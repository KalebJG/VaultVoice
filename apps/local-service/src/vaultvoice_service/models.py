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
    active_profile: str = "accuracy"
    fallback_active: bool = False
    fallback_reason: str | None = None
