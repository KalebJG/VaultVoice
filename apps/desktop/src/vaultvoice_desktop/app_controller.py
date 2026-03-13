from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from vaultvoice_service.models import TranscriptResult


class DictationState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


class LocalServiceClient(Protocol):
    def start(self) -> str: ...

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]: ...

    def finalize(self, session_id: str) -> TranscriptResult: ...


@dataclass(slots=True)
class DesktopState:
    status: DictationState = DictationState.IDLE
    live_transcript: str = ""
    final_transcript: str = ""
    active_session_id: str | None = None
    last_error: str | None = None


class DesktopAppController:
    """Minimal desktop shell controller for push-to-talk lifecycle wiring."""

    def __init__(self, service_client: LocalServiceClient) -> None:
        self._service = service_client
        self._state = DesktopState()

    @property
    def state(self) -> DesktopState:
        return self._state

    def push_to_talk_down(self) -> DesktopState:
        if self._state.active_session_id is not None:
            return self._state

        try:
            session_id = self._service.start()
        except Exception as exc:  # noqa: BLE001
            return self._set_error(f"Unable to start dictation session: {exc}")

        self._state.status = DictationState.LISTENING
        self._state.active_session_id = session_id
        self._state.live_transcript = ""
        self._state.final_transcript = ""
        self._state.last_error = None
        return self._state

    def ingest_microphone_frame(self, pcm_frame: bytes) -> DesktopState:
        session_id = self._state.active_session_id
        if session_id is None:
            return self._state

        try:
            chunk_results = self._service.stream_microphone_frame(session_id, pcm_frame)
        except Exception as exc:  # noqa: BLE001
            return self._set_error(f"Audio stream failed: {exc}")

        partial_texts = [r.text for r in chunk_results if r.text]
        if partial_texts:
            self._state.live_transcript = " ".join(partial_texts).strip()
        return self._state

    def push_to_talk_up(self) -> DesktopState:
        session_id = self._state.active_session_id
        if session_id is None:
            return self._state

        self._state.status = DictationState.PROCESSING
        try:
            final_result = self._service.finalize(session_id)
        except Exception as exc:  # noqa: BLE001
            return self._set_error(f"Unable to finalize dictation: {exc}")

        if final_result.text:
            self._state.final_transcript = final_result.text
            self._state.live_transcript = final_result.text

        self._state.status = DictationState.IDLE
        self._state.active_session_id = None
        return self._state

    def _set_error(self, message: str) -> DesktopState:
        self._state.status = DictationState.ERROR
        self._state.last_error = message
        self._state.active_session_id = None
        return self._state
