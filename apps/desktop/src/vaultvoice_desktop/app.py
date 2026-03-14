from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Callable, Protocol

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


class DictationLifecycleState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class DictationLifecycleStateMachine:
    """Small lifecycle state machine for dictation control transitions."""

    debounce_seconds: float = 0.075
    clock: Callable[[], float] = monotonic
    state: DictationLifecycleState = DictationLifecycleState.IDLE
    _last_release_at: float | None = None

    @property
    def is_listening(self) -> bool:
        return self.state == DictationLifecycleState.LISTENING

    def can_start(self) -> bool:
        if self.state != DictationLifecycleState.IDLE:
            return False
        if self._last_release_at is None:
            return True
        return (self.clock() - self._last_release_at) >= self.debounce_seconds

    def start_listening(self) -> bool:
        if not self.can_start():
            return False
        self.state = DictationLifecycleState.LISTENING
        return True

    def stop_listening(self) -> bool:
        if self.state != DictationLifecycleState.LISTENING:
            return False
        self.state = DictationLifecycleState.PROCESSING
        self._last_release_at = self.clock()
        return True

    def complete(self) -> None:
        self.state = DictationLifecycleState.IDLE

    def fail(self) -> None:
        self.state = DictationLifecycleState.ERROR

    def reset(self) -> None:
        self.state = DictationLifecycleState.IDLE


@dataclass
class AudioCapturePolicy:
    """Tracks pre-roll buffering and minimum utterance gating."""

    pre_roll_max_bytes: int = 3_200
    minimum_utterance_bytes: int = 1_600
    _pre_roll_frames: deque[bytes] = field(default_factory=deque)
    _pre_roll_buffered_bytes: int = 0
    _current_utterance_bytes: int = 0

    def _append_pre_roll(self, pcm_frame: bytes) -> None:
        if not pcm_frame:
            return
        self._pre_roll_frames.append(pcm_frame)
        self._pre_roll_buffered_bytes += len(pcm_frame)

        while self._pre_roll_buffered_bytes > self.pre_roll_max_bytes and self._pre_roll_frames:
            dropped = self._pre_roll_frames.popleft()
            self._pre_roll_buffered_bytes -= len(dropped)

    def capture_frame(self, pcm_frame: bytes, listening: bool) -> None:
        if listening:
            self._current_utterance_bytes += len(pcm_frame)
            return
        self._append_pre_roll(pcm_frame)

    def flush_pre_roll(self) -> list[bytes]:
        frames = list(self._pre_roll_frames)
        self._pre_roll_frames.clear()
        self._pre_roll_buffered_bytes = 0
        return frames

    def begin_utterance(self) -> list[bytes]:
        self._current_utterance_bytes = 0
        return self.flush_pre_roll()

    def has_minimum_utterance(self) -> bool:
        return self._current_utterance_bytes >= self.minimum_utterance_bytes


@dataclass
class DictationSessionController:
    """Desktop shell controller for push-to-talk dictation lifecycle."""

    client: SessionClient
    transcript: TranscriptState = field(default_factory=TranscriptState)
    audio_policy: AudioCapturePolicy = field(default_factory=AudioCapturePolicy)
    lifecycle: DictationLifecycleStateMachine = field(default_factory=DictationLifecycleStateMachine)
    _active_session_id: str | None = None

    def key_down(self) -> None:
        if not self.lifecycle.start_listening():
            return

        session_id = self.client.start()
        self._active_session_id = session_id
        self.transcript.is_listening = True
        self.transcript.last_session_id = session_id
        self.transcript.partial_text = ""

        for pre_roll_frame in self.audio_policy.begin_utterance():
            self._stream_and_update_partial(pre_roll_frame)

    def push_microphone_frame(self, pcm_frame: bytes) -> None:
        listening = self.lifecycle.is_listening and self._active_session_id is not None
        self.audio_policy.capture_frame(pcm_frame=pcm_frame, listening=listening)
        if not listening:
            return

        self._stream_and_update_partial(pcm_frame)

    def key_up(self) -> TranscriptResult | None:
        if not self.lifecycle.stop_listening() or self._active_session_id is None:
            return None

        session_id = self._active_session_id
        self._active_session_id = None
        self.transcript.is_listening = False

        if not self.audio_policy.has_minimum_utterance():
            self.transcript.partial_text = ""
            self.lifecycle.complete()
            return None

        try:
            final = self.client.finalize(session_id)
        except Exception:
            self.lifecycle.fail()
            raise

        self.transcript.final_text = final.text
        self.transcript.partial_text = ""
        self.lifecycle.complete()
        return final

    def _stream_and_update_partial(self, pcm_frame: bytes) -> None:
        if self._active_session_id is None:
            return

        partials = self.client.stream_microphone_frame(self._active_session_id, pcm_frame)
        latest_partial = next((result for result in reversed(partials) if not result.is_final), None)
        if latest_partial is not None:
            self.transcript.partial_text = latest_partial.text
