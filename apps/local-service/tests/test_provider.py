import math
import unittest

from vaultvoice_service.provider import LocalEnergyTranscriptionProvider


class LocalEnergyTranscriptionProviderTests(unittest.TestCase):
    def test_emits_partial_for_voiced_chunk(self) -> None:
        provider = LocalEnergyTranscriptionProvider()
        session_id = provider.start_session()

        voiced_chunk = b"\xe8\x03" * 400
        partial = provider.transcribe_chunk(session_id, voiced_chunk)

        self.assertFalse(partial.is_final)
        self.assertNotEqual(partial.text, "")
        self.assertIsNotNone(partial.confidence)
        self.assertGreater(partial.confidence or 0.0, 0.0)

    def test_finalize_returns_non_empty_for_speech_like_input(self) -> None:
        provider = LocalEnergyTranscriptionProvider()
        session_id = provider.start_session()

        for _ in range(4):
            provider.transcribe_chunk(session_id, _speech_like_pcm(3200))

        final = provider.finalize_session(session_id)

        self.assertTrue(final.is_final)
        self.assertNotEqual(final.text, "")
        self.assertIsNotNone(final.confidence)

    def test_finalize_returns_empty_for_silence(self) -> None:
        provider = LocalEnergyTranscriptionProvider()
        session_id = provider.start_session()

        provider.transcribe_chunk(session_id, b"\x00\x00" * 3200)
        final = provider.finalize_session(session_id)

        self.assertTrue(final.is_final)
        self.assertEqual(final.text, "")



def _speech_like_pcm(sample_count: int, sample_rate_hz: int = 16_000) -> bytes:
    samples: list[int] = []
    for i in range(sample_count):
        carrier = math.sin(2 * math.pi * 190 * (i / sample_rate_hz))
        envelope = 0.45 + (0.55 * math.sin(2 * math.pi * 4.5 * (i / sample_rate_hz)))
        value = int(9_500 * carrier * envelope)
        samples.append(value)

    return b"".join(sample.to_bytes(2, byteorder="little", signed=True) for sample in samples)


if __name__ == "__main__":
    unittest.main()
