import math
import unittest

from vaultvoice_service.provider import LocalEnergyTranscriptionProvider


class LocalEnergyTranscriptionProviderTests(unittest.TestCase):
    def test_emits_streaming_partial_from_decoded_speech(self) -> None:
        provider = LocalEnergyTranscriptionProvider()
        session_id = provider.start_session()

        provider.transcribe_chunk(session_id, _tone_word_pcm("vault"))
        partial = provider.transcribe_chunk(session_id, _silence_pcm(1600))

        self.assertFalse(partial.is_final)
        self.assertEqual(partial.text, "vault")
        self.assertIsNotNone(partial.confidence)
        self.assertGreater(partial.confidence or 0.0, 0.0)

    def test_finalize_returns_decoded_words_for_spoken_content(self) -> None:
        provider = LocalEnergyTranscriptionProvider()
        session_id = provider.start_session()

        provider.transcribe_chunk(session_id, _tone_word_pcm("hello"))
        provider.transcribe_chunk(session_id, _silence_pcm(1600))
        provider.transcribe_chunk(session_id, _tone_word_pcm("world"))

        final = provider.finalize_session(session_id)

        self.assertTrue(final.is_final)
        self.assertEqual(final.text, "hello world")
        self.assertIsNotNone(final.confidence)

    def test_finalize_returns_empty_for_silence(self) -> None:
        provider = LocalEnergyTranscriptionProvider()
        session_id = provider.start_session()

        provider.transcribe_chunk(session_id, _silence_pcm(3200))
        final = provider.finalize_session(session_id)

        self.assertTrue(final.is_final)
        self.assertEqual(final.text, "")


_WORD_FREQUENCIES_HZ = {
    "vault": 220.0,
    "voice": 260.0,
    "hello": 300.0,
    "world": 340.0,
}


def _tone_word_pcm(word: str, sample_count: int = 3200, sample_rate_hz: int = 16_000) -> bytes:
    frequency_hz = _WORD_FREQUENCIES_HZ[word]
    samples: list[int] = []
    for i in range(sample_count):
        t = i / sample_rate_hz
        samples.append(int(8_500 * math.sin(2 * math.pi * frequency_hz * t)))
    return b"".join(sample.to_bytes(2, byteorder="little", signed=True) for sample in samples)


def _silence_pcm(sample_count: int) -> bytes:
    return b"\x00\x00" * sample_count


if __name__ == "__main__":
    unittest.main()
