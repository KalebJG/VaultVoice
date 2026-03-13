from __future__ import annotations

from dataclasses import dataclass, field

from .audio_pipeline import AudioPreprocessor
from .models import ServiceHealth, TranscriptResult
from .observability import MetricsSnapshot, PrivacySafeMetrics
from .provider import LocalStubProvider, TranscriptionProvider
from .retention import RetentionPolicy


@dataclass
class LocalTranscriptionService:
    provider: TranscriptionProvider = field(default_factory=LocalStubProvider)
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    metrics: PrivacySafeMetrics = field(default_factory=PrivacySafeMetrics)
    preprocessor: AudioPreprocessor = field(default_factory=AudioPreprocessor)
    _session_overlap: dict[str, bytes] = field(default_factory=dict)

    def health(self) -> ServiceHealth:
        self.retention.assert_memory_only()
        return ServiceHealth(status="ok", retention_mode=self.retention.mode)

    def start(self) -> str:
        self.retention.assert_memory_only()
        self.metrics.session_started()
        session_id = self.provider.start_session()
        self._session_overlap[session_id] = b""
        return session_id

    def stream_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        self.retention.assert_memory_only()
        with self.metrics.measure() as timer:
            timer.operation = "stream_chunk"
            processed = self.preprocessor.preprocess_chunk(pcm_chunk)
            if not processed.is_speech:
                self.metrics.chunk_skipped()
                return TranscriptResult(text="", is_final=False, confidence=None)

            overlap = self._session_overlap.get(session_id, b"")
            provider_chunk = overlap + processed.pcm
            result = self.provider.transcribe_chunk(
                session_id=session_id,
                pcm_chunk=provider_chunk,
            )

            self._session_overlap[session_id] = self.preprocessor.overlap_bytes(processed.pcm)

        self.metrics.chunk_processed()
        return result

    def finalize(self, session_id: str) -> TranscriptResult:
        self.retention.assert_memory_only()
        with self.metrics.measure() as timer:
            timer.operation = "finalize"
            result = self.provider.finalize_session(session_id=session_id)
        self._session_overlap.pop(session_id, None)
        return result

    def metrics_snapshot(self) -> MetricsSnapshot:
        return self.metrics.snapshot()
