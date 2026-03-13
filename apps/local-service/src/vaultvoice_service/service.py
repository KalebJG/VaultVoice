from __future__ import annotations

from dataclasses import dataclass, field

from .models import ServiceHealth, TranscriptResult
from .provider import LocalStubProvider, TranscriptionProvider
from .retention import RetentionPolicy


@dataclass
class LocalTranscriptionService:
    provider: TranscriptionProvider = field(default_factory=LocalStubProvider)
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)

    def health(self) -> ServiceHealth:
        self.retention.assert_memory_only()
        return ServiceHealth(status="ok", retention_mode=self.retention.mode)

    def start(self) -> str:
        self.retention.assert_memory_only()
        return self.provider.start_session()

    def stream_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        self.retention.assert_memory_only()
        return self.provider.transcribe_chunk(session_id=session_id, pcm_chunk=pcm_chunk)

    def finalize(self, session_id: str) -> TranscriptResult:
        self.retention.assert_memory_only()
        return self.provider.finalize_session(session_id=session_id)
