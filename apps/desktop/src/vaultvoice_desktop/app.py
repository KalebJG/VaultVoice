from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Callable, Protocol

from vaultvoice_service.models import TranscriptResult
from vaultvoice_service.service import LocalTranscriptionService

from .hud import FloatingHUDController


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
    hud: FloatingHUDController | None = None
    sample_rate_hz: int = 16_000
    bytes_per_sample: int = 2
    debounce_window_seconds: float = 0.04
    min_utterance_seconds: float = 0.1
    pre_roll_seconds: float = 0.12
    clock: Callable[[], float] = monotonic
    _active_session_id: str | None = None
    _captured_audio_bytes: int = 0
    _last_key_down_at: float | None = None
    _last_key_up_at: float | None = None
    _pre_roll_frames: deque[bytes] = field(default_factory=deque)
    _pre_roll_bytes: int = 0

    def key_down(self) -> None:
        now = self.clock()
        if self._active_session_id is not None:
            return

        if self._last_key_up_at is not None and now - self._last_key_up_at < self.debounce_window_seconds:
            return

        session_id = self.client.start()
        self._active_session_id = session_id
        self._captured_audio_bytes = 0
        self._last_key_down_at = now
        self.transcript.is_listening = True
        self.transcript.last_session_id = session_id
        self.transcript.partial_text = ""
        if self.hud is not None:
            self.hud.on_key_down()

        if self._pre_roll_frames:
            pre_roll_pcm = b"".join(self._pre_roll_frames)
            self._pre_roll_frames.clear()
            self._pre_roll_bytes = 0
            self._stream_active_frame(pre_roll_pcm)

    def push_microphone_frame(self, pcm_frame: bytes) -> None:
        if self._active_session_id is None:
            self._append_pre_roll(pcm_frame)
            return

        self._stream_active_frame(pcm_frame)

    def key_up(self) -> TranscriptResult | None:
        if self._active_session_id is None:
            return None

        now = self.clock()
        session_id = self._active_session_id
        self._active_session_id = None
        self.transcript.is_listening = False
        self._last_key_up_at = now

        if self.hud is not None:
            self.hud.on_key_up()

        try:
            final = self.client.finalize(session_id)
        except Exception as exc:
            if self.hud is not None:
                self.hud.on_error(str(exc))
            raise

        self.transcript.partial_text = ""

        if self._captured_audio_bytes < self._minimum_utterance_bytes():
            self.transcript.final_text = ""
            if self.hud is not None:
                self.hud.on_transcription_complete()
            return None

        self.transcript.final_text = final.text
        if self.hud is not None:
            self.hud.on_transcription_complete()
        return final

    def _stream_active_frame(self, pcm_frame: bytes) -> None:
        if self._active_session_id is None:
            return

        self._captured_audio_bytes += len(pcm_frame)
        partials = self.client.stream_microphone_frame(self._active_session_id, pcm_frame)
        latest_partial = next((result for result in reversed(partials) if not result.is_final), None)
        if latest_partial is not None:
            self.transcript.partial_text = latest_partial.text

    def _append_pre_roll(self, pcm_frame: bytes) -> None:
        self._pre_roll_frames.append(pcm_frame)
        self._pre_roll_bytes += len(pcm_frame)
        max_pre_roll_bytes = self._pre_roll_max_bytes()
        while self._pre_roll_bytes > max_pre_roll_bytes and self._pre_roll_frames:
            removed = self._pre_roll_frames.popleft()
            self._pre_roll_bytes -= len(removed)

    def _pre_roll_max_bytes(self) -> int:
        return int(self.pre_roll_seconds * self.sample_rate_hz * self.bytes_per_sample)

    def _minimum_utterance_bytes(self) -> int:
        return int(self.min_utterance_seconds * self.sample_rate_hz * self.bytes_per_sample)
