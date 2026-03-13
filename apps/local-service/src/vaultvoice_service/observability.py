from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
import os

from .logging_utils import assert_safe_log_fields


@dataclass(slots=True)
class MetricsSnapshot:
    total_sessions_started: int
    total_chunks_processed: int
    total_chunks_skipped: int
    total_errors: int
    last_stream_latency_ms: float | None
    last_finalize_latency_ms: float | None
    cpu_load: float | None


@dataclass
class PrivacySafeMetrics:
    total_sessions_started: int = 0
    total_chunks_processed: int = 0
    total_chunks_skipped: int = 0
    total_errors: int = 0
    _last_stream_latency_ms: float | None = None
    _last_finalize_latency_ms: float | None = None

    def session_started(self) -> None:
        self.total_sessions_started += 1

    def chunk_processed(self) -> None:
        self.total_chunks_processed += 1

    def chunk_skipped(self) -> None:
        self.total_chunks_skipped += 1

    def record_error(self) -> None:
        self.total_errors += 1

    def measure(self):
        return _LatencyRecorder(self)

    def safe_event(self, event: str, **fields: object) -> dict[str, object]:
        payload = {"event": event, **fields}
        assert_safe_log_fields(payload)
        return payload

    def snapshot(self) -> MetricsSnapshot:
        cpu_load = _read_cpu_load()
        return MetricsSnapshot(
            total_sessions_started=self.total_sessions_started,
            total_chunks_processed=self.total_chunks_processed,
            total_chunks_skipped=self.total_chunks_skipped,
            total_errors=self.total_errors,
            last_stream_latency_ms=self._last_stream_latency_ms,
            last_finalize_latency_ms=self._last_finalize_latency_ms,
            cpu_load=cpu_load,
        )


@dataclass
class _LatencyRecorder:
    metrics: PrivacySafeMetrics
    operation: str | None = None
    _start_time: float = field(default=0.0)

    def __enter__(self) -> "_LatencyRecorder":
        self._start_time = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (perf_counter() - self._start_time) * 1000
        if self.operation == "stream_chunk":
            self.metrics._last_stream_latency_ms = elapsed_ms
        elif self.operation == "finalize":
            self.metrics._last_finalize_latency_ms = elapsed_ms
        if exc is not None:
            self.metrics.record_error()


def _read_cpu_load() -> float | None:
    try:
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return load1 / cpu_count
    except (AttributeError, OSError):
        return None
