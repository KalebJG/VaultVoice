from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from vaultvoice_service.models import TranscriptResult
from vaultvoice_service.service import LocalTranscriptionService


class SessionClient(Protocol):
    def start(self) -> str: ...

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]: ...

    def finalize(self, session_id: str) -> TranscriptResult: ...


@dataclass
class ServiceSessionClient:
    """Adapter used by the desktop shell to call the local service API."""

    service: LocalTranscriptionService = field(default_factory=LocalTranscriptionService)

    def start(self) -> str:
        return self.service.start()

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]:
        return self.service.stream_microphone_frame(session_id=session_id, pcm_frame=pcm_frame)

    def finalize(self, session_id: str) -> TranscriptResult:
        return self.service.finalize(session_id=session_id)


@dataclass(slots=True)
class TranscriptState:
    partial_text: str = ""
    final_text: str = ""
    is_listening: bool = False
    last_session_id: str | None = None


@dataclass
class DictationSessionController:
    """Desktop shell controller for push-to-talk dictation lifecycle."""

    client: SessionClient
    transcript: TranscriptState = field(default_factory=TranscriptState)
    _active_session_id: str | None = None

    def key_down(self) -> None:
        if self._active_session_id is not None:
            return

        session_id = self.client.start()
        self._active_session_id = session_id
        self.transcript.is_listening = True
        self.transcript.last_session_id = session_id
        self.transcript.partial_text = ""

    def push_microphone_frame(self, pcm_frame: bytes) -> None:
        if self._active_session_id is None:
            return

        partials = self.client.stream_microphone_frame(self._active_session_id, pcm_frame)
        latest_partial = next((result for result in reversed(partials) if not result.is_final), None)
        if latest_partial is not None:
            self.transcript.partial_text = latest_partial.text

    def key_up(self) -> TranscriptResult | None:
        if self._active_session_id is None:
            return None

        session_id = self._active_session_id
        self._active_session_id = None
        self.transcript.is_listening = False

        final = self.client.finalize(session_id)
        self.transcript.final_text = final.text
        self.transcript.partial_text = ""
        return final
