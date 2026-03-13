from __future__ import annotations

from array import array
from dataclasses import dataclass, field


@dataclass(slots=True)
class AudioChunk:
    pcm: bytes
    is_speech: bool


@dataclass(slots=True)
class AudioPreprocessor:
    vad_threshold: int = 500
    target_peak: int = 12000
    overlap_ms: int = 120
    sample_rate_hz: int = 16000

    def preprocess_chunk(self, pcm_chunk: bytes) -> AudioChunk:
        _ensure_pcm16_byte_alignment(pcm_chunk)
        normalized = normalize_pcm16(pcm_chunk, target_peak=self.target_peak)
        return AudioChunk(
            pcm=normalized,
            is_speech=contains_speech(normalized, self.vad_threshold),
        )

    def overlap_bytes(self, pcm_chunk: bytes) -> bytes:
        _ensure_pcm16_byte_alignment(pcm_chunk)
        samples_to_keep = int((self.overlap_ms / 1000) * self.sample_rate_hz)
        bytes_to_keep = max(samples_to_keep * 2, 0)
        if bytes_to_keep == 0:
            return b""
        return pcm_chunk[-bytes_to_keep:]


@dataclass(slots=True)
class MicrophoneChunker:
    """Buffers live microphone frames into provider-sized PCM16 chunks."""

    chunk_ms: int = 320
    sample_rate_hz: int = 16000
    bytes_per_sample: int = 2
    _buffer: bytearray = field(default_factory=bytearray, init=False, repr=False)

    def push_frame(self, pcm_frame: bytes) -> list[bytes]:
        _ensure_pcm16_byte_alignment(pcm_frame)
        if not pcm_frame:
            return []

        self._buffer.extend(pcm_frame)
        chunk_size = self.chunk_size_bytes
        chunks: list[bytes] = []

        while len(self._buffer) >= chunk_size:
            chunks.append(bytes(self._buffer[:chunk_size]))
            del self._buffer[:chunk_size]

        return chunks

    def flush(self) -> bytes:
        if not self._buffer:
            return b""

        remainder = bytes(self._buffer)
        self._buffer.clear()
        return remainder

    @property
    def chunk_size_bytes(self) -> int:
        samples_per_chunk = int((self.chunk_ms / 1000) * self.sample_rate_hz)
        return max(samples_per_chunk * self.bytes_per_sample, self.bytes_per_sample)


def normalize_pcm16(pcm_chunk: bytes, target_peak: int = 12000) -> bytes:
    _ensure_pcm16_byte_alignment(pcm_chunk)
    if not pcm_chunk:
        return pcm_chunk

    samples = array("h")
    samples.frombytes(pcm_chunk)
    peak = max(abs(v) for v in samples)
    if peak == 0:
        return pcm_chunk

    scale = min(target_peak / peak, 1.0)
    if scale == 1.0:
        return pcm_chunk

    out = array("h", (int(sample * scale) for sample in samples))
    return out.tobytes()


def contains_speech(pcm_chunk: bytes, threshold: int = 500) -> bool:
    _ensure_pcm16_byte_alignment(pcm_chunk)
    if not pcm_chunk:
        return False

    samples = array("h")
    samples.frombytes(pcm_chunk)
    avg_abs = sum(abs(v) for v in samples) / len(samples)
    return avg_abs >= threshold


def _ensure_pcm16_byte_alignment(pcm_chunk: bytes) -> None:
    if len(pcm_chunk) % 2 != 0:
        raise ValueError("PCM16 chunks must contain an even number of bytes")
