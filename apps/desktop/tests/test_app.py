import unittest
from dataclasses import dataclass, field
import math

from vaultvoice_desktop.app import DictationSessionController, ServiceSessionClient
from vaultvoice_desktop.hud import FloatingHUDController, HUDStatus
from vaultvoice_service.models import TranscriptResult
from vaultvoice_service.provider import TranscriptionProvider
from vaultvoice_service.service import LocalTranscriptionService


class _DesktopProvider(TranscriptionProvider):
    def __init__(self) -> None:
        self._chunks: dict[str, int] = {}

    def start_session(self) -> str:
        session_id = f"desktop-session-{len(self._chunks) + 1}"
        self._chunks[session_id] = 0
        return session_id

    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        _ = pcm_chunk
        self._chunks[session_id] += 1
        return TranscriptResult(text=f"partial-{self._chunks[session_id]}", is_final=False, confidence=0.7)

    def finalize_session(self, session_id: str) -> TranscriptResult:
        chunk_count = self._chunks.get(session_id, 0)
        return TranscriptResult(text=f"final-{chunk_count}", is_final=True, confidence=0.9)


@dataclass
class _FakeSessionClient:
    partial_text: str = "partial"
    starts: int = 0
    stream_sizes: list[int] = field(default_factory=list)

    def start(self) -> str:
        self.starts += 1
        return f"s-{self.starts}"

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]:
        _ = session_id
        self.stream_sizes.append(len(pcm_frame))
        return [TranscriptResult(text=self.partial_text, is_final=False, confidence=0.5)]

    def finalize(self, session_id: str) -> TranscriptResult:
        _ = session_id
        return TranscriptResult(text="final", is_final=True, confidence=0.9)




@dataclass
class _FailingFinalizeClient(_FakeSessionClient):
    def finalize(self, session_id: str) -> TranscriptResult:
        _ = session_id
        raise RuntimeError("finalize failed")


class DictationSessionControllerTests(unittest.TestCase):
    def test_integration_real_provider_returns_non_empty_final_text(self) -> None:
        service = LocalTranscriptionService()
        controller = DictationSessionController(client=ServiceSessionClient(service=service))

        controller.key_down()
        controller.push_microphone_frame(_speech_like_pcm(4096))
        controller.push_microphone_frame(_speech_like_pcm(4096, phase_offset=0.15))
        final = controller.key_up()

        self.assertIsNotNone(final)
        assert final is not None
        self.assertTrue(final.is_final)
        self.assertNotEqual(final.text.strip(), "")
        self.assertNotEqual(controller.transcript.final_text.strip(), "")

    def test_push_to_talk_session_updates_partial_and_final_transcript(self) -> None:
        service = LocalTranscriptionService(provider=_DesktopProvider())
        controller = DictationSessionController(client=ServiceSessionClient(service=service))

        controller.key_down()
        controller.push_microphone_frame(b"\xe8\x03" * 6000)
        final = controller.key_up()

        self.assertIsNotNone(final)
        self.assertFalse(controller.transcript.is_listening)
        self.assertEqual(controller.transcript.partial_text, "")
        self.assertEqual(controller.transcript.final_text, "final-2")

    def test_ignores_audio_and_finalize_without_active_session(self) -> None:
        service = LocalTranscriptionService(provider=_DesktopProvider())
        controller = DictationSessionController(client=ServiceSessionClient(service=service))

        controller.push_microphone_frame(b"\xe8\x03" * 100)
        final = controller.key_up()

        self.assertIsNone(final)
        self.assertEqual(controller.transcript.final_text, "")

    def test_discards_short_utterance_below_minimum_threshold(self) -> None:
        client = _FakeSessionClient()
        controller = DictationSessionController(
            client=client,
            min_utterance_seconds=0.1,
            pre_roll_seconds=0.0,
        )

        controller.key_down()
        controller.push_microphone_frame(b"\x00\x01" * 1000)
        final = controller.key_up()

        self.assertIsNone(final)
        self.assertEqual(controller.transcript.final_text, "")

    def test_pre_roll_audio_is_streamed_when_session_starts(self) -> None:
        client = _FakeSessionClient()
        controller = DictationSessionController(client=client, pre_roll_seconds=0.1)

        controller.push_microphone_frame(b"\x00\x01" * 500)
        controller.push_microphone_frame(b"\x00\x01" * 700)
        controller.key_down()

        self.assertEqual(client.starts, 1)
        self.assertEqual(client.stream_sizes[0], 2400)

    def test_debounce_ignores_immediate_keydown_after_keyup(self) -> None:
        clock_times = iter([0.0, 0.2, 0.22])
        client = _FakeSessionClient()
        controller = DictationSessionController(
            client=client,
            debounce_window_seconds=0.05,
            clock=lambda: next(clock_times),
            pre_roll_seconds=0.0,
        )

        controller.key_down()
        controller.push_microphone_frame(b"\x00\x01" * 2000)
        controller.key_up()
        controller.key_down()

        self.assertEqual(client.starts, 1)

    def test_hud_tracks_listening_processing_and_idle(self) -> None:
        client = _FakeSessionClient()
        hud = FloatingHUDController()
        controller = DictationSessionController(client=client, hud=hud, pre_roll_seconds=0.0)

        controller.key_down()
        self.assertEqual(hud.state.status, HUDStatus.LISTENING)

        controller.push_microphone_frame(b"\x00\x01" * 2000)
        result = controller.key_up()

        self.assertIsNotNone(result)
        self.assertEqual(hud.state.status, HUDStatus.IDLE)

    def test_hud_moves_to_error_when_finalize_fails(self) -> None:
        client = _FailingFinalizeClient()
        hud = FloatingHUDController()
        controller = DictationSessionController(client=client, hud=hud, pre_roll_seconds=0.0)

        controller.key_down()
        controller.push_microphone_frame(b"\x00\x01" * 2000)

        with self.assertRaises(RuntimeError):
            controller.key_up()

        self.assertEqual(hud.state.status, HUDStatus.ERROR)
        self.assertEqual(hud.state.error_message, "finalize failed")


if __name__ == "__main__":
    unittest.main()


def _speech_like_pcm(sample_count: int, sample_rate_hz: int = 16_000, phase_offset: float = 0.0) -> bytes:
    samples: list[int] = []
    for i in range(sample_count):
        t = (i / sample_rate_hz) + phase_offset
        carrier = math.sin(2 * math.pi * 220 * t)
        envelope = 0.35 + (0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * 5.0 * t)))
        value = int(10_000 * carrier * envelope)
        samples.append(value)

    return b"".join(sample.to_bytes(2, byteorder="little", signed=True) for sample in samples)
