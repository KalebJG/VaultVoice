from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import pairwise
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
    voiced_chunks: int = 0
    syllable_events: int = 0
    total_samples: int = 0
    bytes_seen: int = 0
    latest_partial: str = ""


class LocalEnergyTranscriptionProvider(TranscriptionProvider):
    """CPU-only lightweight local provider used in non-test environments.

    This provider is intentionally model-free and dependency-free so it can run
    on constrained machines while still exercising the full partial/final
    transcription flow.
    """

    _VOICED_RMS_THRESHOLD = 700.0
    _SYLLABLE_DELTA_THRESHOLD = 500.0

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

        state.bytes_seen += len(pcm_chunk)
        state.total_samples += len(samples)
        rms = _root_mean_square(samples)
        if rms >= self._VOICED_RMS_THRESHOLD:
            state.voiced_chunks += 1
            state.syllable_events += _count_energy_pulses(samples, threshold=self._SYLLABLE_DELTA_THRESHOLD)

        state.latest_partial = self._partial_hypothesis(state)
        confidence = min(0.99, 0.55 + (state.voiced_chunks * 0.05)) if state.voiced_chunks else 0.0
        return TranscriptResult(text=state.latest_partial, is_final=False, confidence=confidence)

    def finalize_session(self, session_id: str) -> TranscriptResult:
        state = self._sessions.pop(session_id, None)
        if state is None:
            raise KeyError(f"Unknown session_id: {session_id}")

        if state.voiced_chunks == 0:
            return TranscriptResult(text="", is_final=True, confidence=0.0)

        text = self._final_hypothesis(state)
        confidence = min(0.99, 0.65 + (state.voiced_chunks * 0.03))
        return TranscriptResult(text=text, is_final=True, confidence=confidence)

    def _require_session(self, session_id: str) -> _SessionState:
        state = self._sessions.get(session_id)
        if state is None:
            raise KeyError(f"Unknown session_id: {session_id}")
        return state

    def _partial_hypothesis(self, state: _SessionState) -> str:
        if state.voiced_chunks == 0:
            return ""
        if state.voiced_chunks == 1:
            return "listening…"
        if state.voiced_chunks < 4:
            return "capturing speech…"
        return "capturing continuous speech…"

    def _final_hypothesis(self, state: _SessionState) -> str:
        syllables = max(1, state.syllable_events // 2)
        pace = "brief" if state.voiced_chunks < 3 else "natural"
        return f"detected {pace} speech ({syllables} syllable-like events)"


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


def _count_energy_pulses(samples: list[int], threshold: float) -> int:
    if len(samples) < 2:
        return 0

    envelope = [abs(sample) for sample in samples]
    return sum(1 for previous, current in pairwise(envelope) if current - previous >= threshold)
