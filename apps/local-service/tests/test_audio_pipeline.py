import unittest
from array import array

from vaultvoice_service.audio_pipeline import (
    AudioPreprocessor,
    MicrophoneChunker,
    contains_speech,
    normalize_pcm16,
)


class AudioPipelineTests(unittest.TestCase):
    def test_normalize_scales_down_loud_audio(self) -> None:
        src = array("h", [0, 20000, -20000, 10000]).tobytes()
        normalized = normalize_pcm16(src, target_peak=10000)
        out = array("h")
        out.frombytes(normalized)

        self.assertLessEqual(max(abs(v) for v in out), 10000)

    def test_contains_speech_detects_silence(self) -> None:
        silence = array("h", [0] * 100).tobytes()
        speech = array("h", [1500] * 100).tobytes()

        self.assertFalse(contains_speech(silence, threshold=200))
        self.assertTrue(contains_speech(speech, threshold=200))

    def test_preprocess_chunk_sets_vad_and_overlap(self) -> None:
        preprocessor = AudioPreprocessor(vad_threshold=300, overlap_ms=100, sample_rate_hz=1000)
        chunk = array("h", [400] * 500).tobytes()

        result = preprocessor.preprocess_chunk(chunk)
        overlap = preprocessor.overlap_bytes(chunk)

        self.assertTrue(result.is_speech)
        self.assertEqual(len(overlap), 200)


    def test_microphone_chunker_buffers_until_chunk_boundary(self) -> None:
        chunker = MicrophoneChunker(chunk_ms=100, sample_rate_hz=1000)

        first = chunker.push_frame(b"\x01\x00" * 80)
        second = chunker.push_frame(b"\x01\x00" * 40)

        self.assertEqual(first, [])
        self.assertEqual(len(second), 1)
        self.assertEqual(len(second[0]), 200)

    def test_microphone_chunker_flush_returns_remainder(self) -> None:
        chunker = MicrophoneChunker(chunk_ms=100, sample_rate_hz=1000)
        chunker.push_frame(b"\x01\x00" * 50)

        tail = chunker.flush()

        self.assertEqual(len(tail), 100)
        self.assertEqual(chunker.flush(), b"")

    def test_invalid_odd_sized_pcm_chunk_raises(self) -> None:
        with self.assertRaises(ValueError):
            normalize_pcm16(b"\x00")


if __name__ == "__main__":
    unittest.main()
