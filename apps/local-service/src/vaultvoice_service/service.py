from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv

from .audio_pipeline import AudioPreprocessor, MicrophoneChunker
from .models import ServiceHealth, TranscriptResult
from .observability import MetricsSnapshot, PrivacySafeMetrics
from .profile import AccuracyProfileController
from .provider import LocalEnergyTranscriptionProvider, LocalStubProvider, TranscriptionProvider
from .retention import RetentionPolicy


def _default_provider() -> TranscriptionProvider:
    use_real_provider = getenv("VAULTVOICE_USE_REAL_PROVIDER", "1").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if use_real_provider:
        return LocalEnergyTranscriptionProvider()
    return LocalStubProvider()


@dataclass
class LocalTranscriptionService:
    provider: TranscriptionProvider = field(default_factory=_default_provider)
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    metrics: PrivacySafeMetrics = field(default_factory=PrivacySafeMetrics)
    preprocessor: AudioPreprocessor = field(default_factory=AudioPreprocessor)
    profile_controller: AccuracyProfileController = field(default_factory=AccuracyProfileController)
    _session_overlap: dict[str, bytes] = field(default_factory=dict)
    _session_chunkers: dict[str, MicrophoneChunker] = field(default_factory=dict)

    def health(self) -> ServiceHealth:
        self.retention.assert_memory_only()
        state = self.profile_controller.state
        return ServiceHealth(
            status="ok",
            retention_mode=self.retention.mode,
            active_profile=state.active_profile,
            fallback_active=state.fallback_active,
            fallback_reason=state.fallback_reason,
        )

    def start(self) -> str:
        self.retention.assert_memory_only()
        self.metrics.session_started()
        session_id = self.provider.start_session()
        self._session_overlap[session_id] = b""
        self._session_chunkers[session_id] = MicrophoneChunker(
            sample_rate_hz=self.preprocessor.sample_rate_hz
        )
        return session_id

    def stream_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        self.retention.assert_memory_only()
        if session_id not in self._session_chunkers:
            raise KeyError(f"Unknown session_id: {session_id}")

        with self.metrics.measure() as timer:
            timer.operation = "stream_chunk"
            processed = self.preprocessor.preprocess_chunk(pcm_chunk)
            if not processed.is_speech:
                self.metrics.chunk_skipped()
                return TranscriptResult(text="", is_final=False, confidence=None)

            cpu_load = self.metrics.snapshot().cpu_load
            self.profile_controller.observe_cpu_load(cpu_load)

            overlap = self._session_overlap.get(session_id, b"")
            provider_chunk = overlap + processed.pcm
            result = self.provider.transcribe_chunk(
                session_id=session_id,
                pcm_chunk=provider_chunk,
            )

            self._session_overlap[session_id] = self.preprocessor.overlap_bytes(processed.pcm)

        self.metrics.chunk_processed()
        return result

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]:
        self.retention.assert_memory_only()
        chunker = self._session_chunkers.get(session_id)
        if chunker is None:
            raise KeyError(f"Unknown session_id: {session_id}")

        results: list[TranscriptResult] = []
        for chunk in chunker.push_frame(pcm_frame):
            results.append(self.stream_chunk(session_id=session_id, pcm_chunk=chunk))
        return results

    def finalize(self, session_id: str) -> TranscriptResult:
        self.retention.assert_memory_only()
        chunker = self._session_chunkers.get(session_id)
        if chunker is None:
            raise KeyError(f"Unknown session_id: {session_id}")

        try:
            tail = chunker.flush()
            if tail:
                self.stream_chunk(session_id=session_id, pcm_chunk=tail)

            with self.metrics.measure() as timer:
                timer.operation = "finalize"
                result = self.provider.finalize_session(session_id=session_id)
            return result
        finally:
            self._session_chunkers.pop(session_id, None)
            self._session_overlap.pop(session_id, None)

    def metrics_snapshot(self) -> MetricsSnapshot:
        return self.metrics.snapshot()
