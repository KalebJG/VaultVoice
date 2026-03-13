from __future__ import annotations

from abc import ABC, abstractmethod

from .models import TranscriptResult


class TranscriptionProvider(ABC):
    @abstractmethod
    def start_session(self) -> str:
        """Begin a transcription session and return a session id."""

    @abstractmethod
    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        """Process audio chunk and return partial or final text."""

    @abstractmethod
    def finalize_session(self, session_id: str) -> TranscriptResult:
        """Finalize a session and return final transcript."""


class LocalStubProvider(TranscriptionProvider):
    """Scaffold provider for end-to-end plumbing before STT integration."""

    def start_session(self) -> str:
        return "session-stub"

    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        _ = (session_id, pcm_chunk)
        return TranscriptResult(text="", is_final=False, confidence=None)

    def finalize_session(self, session_id: str) -> TranscriptResult:
        _ = session_id
        return TranscriptResult(text="", is_final=True, confidence=None)
