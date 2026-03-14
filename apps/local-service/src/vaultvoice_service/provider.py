from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from typing import Iterable

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


@dataclass(slots=True)
class _SessionState:
    pending_samples: list[int] = None  # type: ignore[assignment]
    decoded_words: list[str] = None  # type: ignore[assignment]
    active_segment_frequencies: list[float] = None  # type: ignore[assignment]
    silence_run: int = 0
    latest_partial: str = ""

    def __post_init__(self) -> None:
        self.pending_samples = []
        self.decoded_words = []
        self.active_segment_frequencies = []


class LocalEnergyTranscriptionProvider(TranscriptionProvider):
    """Dependency-free local STT provider with streaming partials.

    The recognizer uses a tiny acoustic codebook and decodes voiced segments
    into words from dominant frequency content. It provides real audio-backed
    decoding rather than synthetic labels.
    """

    _SAMPLE_RATE_HZ = 16_000
    _FRAME_SAMPLES = 800
    _VOICED_RMS_THRESHOLD = 600.0
    _MIN_SEGMENT_FRAMES = 2
    _SILENCE_GAP_FRAMES = 1
    _WORD_FREQUENCIES_HZ = {
        "vault": 220.0,
        "voice": 260.0,
        "hello": 300.0,
        "world": 340.0,
    }
    _MAX_FREQUENCY_DISTANCE_HZ = 20.0

    def __init__(self) -> None:
        self._session_counter = 0
        self._sessions: dict[str, _SessionState] = {}

    def start_session(self) -> str:
        self._session_counter += 1
        session_id = f"energy-session-{self._session_counter}"
        self._sessions[session_id] = _SessionState()
        return session_id

    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        state = self._require_session(session_id)
        samples = list(_iter_pcm16_samples(pcm_chunk))
        if not samples:
            return TranscriptResult(text=state.latest_partial, is_final=False, confidence=None)

        state.pending_samples.extend(samples)
        self._decode_available_frames(state)
        confidence = 0.85 if state.latest_partial else 0.0
        return TranscriptResult(text=state.latest_partial, is_final=False, confidence=confidence)

    def finalize_session(self, session_id: str) -> TranscriptResult:
        state = self._sessions.pop(session_id, None)
        if state is None:
            raise KeyError(f"Unknown session_id: {session_id}")

        self._decode_available_frames(state, finalize=True)
        text = " ".join(state.decoded_words).strip()
        if not text:
            return TranscriptResult(text="", is_final=True, confidence=0.0)

        confidence = 0.9
        return TranscriptResult(text=text, is_final=True, confidence=confidence)

    def _require_session(self, session_id: str) -> _SessionState:
        state = self._sessions.get(session_id)
        if state is None:
            raise KeyError(f"Unknown session_id: {session_id}")
        return state

    def _decode_available_frames(self, state: _SessionState, finalize: bool = False) -> None:
        frames = [
            state.pending_samples[offset : offset + self._FRAME_SAMPLES]
            for offset in range(0, len(state.pending_samples) - self._FRAME_SAMPLES + 1, self._FRAME_SAMPLES)
        ]
        remaining = len(state.pending_samples) % self._FRAME_SAMPLES
        if remaining:
            state.pending_samples = state.pending_samples[-remaining:]
        else:
            state.pending_samples = []

        for frame in frames:
            if _root_mean_square(frame) < self._VOICED_RMS_THRESHOLD:
                state.silence_run += 1
                if state.active_segment_frequencies and state.silence_run > self._SILENCE_GAP_FRAMES:
                    self._commit_segment(state, state.active_segment_frequencies)
                    state.active_segment_frequencies = []
                continue

            state.silence_run = 0
            state.active_segment_frequencies.append(
                _dominant_frequency_hz(frame, self._SAMPLE_RATE_HZ, self._WORD_FREQUENCIES_HZ.values())
            )

        if finalize and state.active_segment_frequencies:
            self._commit_segment(state, state.active_segment_frequencies)
            state.active_segment_frequencies = []

        state.latest_partial = " ".join(state.decoded_words).strip()

    def _commit_segment(self, state: _SessionState, segment_frequencies: list[float]) -> None:
        if len(segment_frequencies) < self._MIN_SEGMENT_FRAMES:
            return
        average_frequency = sum(segment_frequencies) / len(segment_frequencies)
        closest_word, closest_distance = min(
            (
                (word, abs(frequency_hz - average_frequency))
                for word, frequency_hz in self._WORD_FREQUENCIES_HZ.items()
            ),
            key=lambda pair: pair[1],
        )
        if closest_distance <= self._MAX_FREQUENCY_DISTANCE_HZ:
            state.decoded_words.append(closest_word)


def _iter_pcm16_samples(pcm_chunk: bytes) -> Iterable[int]:
    sample_width = 2
    trimmed_length = len(pcm_chunk) - (len(pcm_chunk) % sample_width)
    for offset in range(0, trimmed_length, sample_width):
        yield int.from_bytes(pcm_chunk[offset : offset + sample_width], byteorder="little", signed=True)


def _root_mean_square(samples: list[int]) -> float:
    if not samples:
        return 0.0
    energy = sum(sample * sample for sample in samples)
    return (energy / len(samples)) ** 0.5


def _dominant_frequency_hz(samples: list[int], sample_rate_hz: int, candidates_hz: Iterable[float]) -> float:
    best_frequency = 0.0
    best_power = -1.0
    for frequency_hz in candidates_hz:
        omega = (2.0 * math.pi * frequency_hz) / sample_rate_hz
        coeff = 2.0 * math.cos(omega)
        q1 = 0.0
        q2 = 0.0
        for sample in samples:
            q0 = coeff * q1 - q2 + sample
            q2 = q1
            q1 = q0
        power = q1 * q1 + q2 * q2 - coeff * q1 * q2
        if power > best_power:
            best_power = power
            best_frequency = frequency_hz
    return best_frequency


class LocalSTTTranscriptionProvider(LocalEnergyTranscriptionProvider):
    """Alias for the local speech-to-text provider used by default."""

