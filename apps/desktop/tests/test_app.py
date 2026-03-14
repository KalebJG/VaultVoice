import math
import time
import unittest
from dataclasses import dataclass, field

from vaultvoice_desktop.app import DictationSessionController, ErrorCategory, ServiceSessionClient
from vaultvoice_desktop.hud import FloatingHUDController, HUDStatus
from vaultvoice_service.models import ServiceHealth, TranscriptResult
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
    health_state: ServiceHealth = field(default_factory=lambda: ServiceHealth(status="ok", retention_mode="memory"))

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

    def health(self) -> ServiceHealth:
        return self.health_state


@dataclass
class _FinalizeErrorClient(_FakeSessionClient):
    error: Exception = field(default_factory=lambda: RuntimeError("finalize failed"))

    def finalize(self, session_id: str) -> TranscriptResult:
        _ = session_id
        raise self.error


@dataclass
class _StreamErrorClient(_FakeSessionClient):
    error: Exception = field(default_factory=lambda: ConnectionError("stream disconnected"))

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]:
        _ = (session_id, pcm_frame)
        raise self.error


@dataclass
class _StartErrorClient(_FakeSessionClient):
    error: Exception = field(default_factory=lambda: PermissionError("mic permission denied"))

    def start(self) -> str:
        raise self.error


@dataclass
class _SlowFinalizeClient(_FakeSessionClient):
    delay_seconds: float = 0.1

    def finalize(self, session_id: str) -> TranscriptResult:
        _ = session_id
        time.sleep(self.delay_seconds)
        return TranscriptResult(text="final", is_final=True, confidence=0.9)


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
        self.assertEqual(hud.state.service_status, "connected")

    def test_finalize_timeout_maps_to_retry_and_recovers_to_idle(self) -> None:
        client = _SlowFinalizeClient()
        hud = FloatingHUDController()
        controller = DictationSessionController(
            client=client,
            hud=hud,
            pre_roll_seconds=0.0,
            service_call_timeout_seconds=0.01,
        )

        controller.key_down()
        controller.push_microphone_frame(b"\x00\x01" * 2000)
        final = controller.key_up()

        self.assertIsNone(final)
        self.assertEqual(hud.state.status, HUDStatus.ERROR)
        self.assertEqual(hud.state.error_category, ErrorCategory.TIMEOUT)
        self.assertEqual(hud.state.recovery_message, "Retry dictation.")

        controller.key_down()
        self.assertEqual(hud.state.status, HUDStatus.LISTENING)

    def test_permission_error_maps_to_reenable_mic_recovery(self) -> None:
        client = _StartErrorClient()
        hud = FloatingHUDController()
        controller = DictationSessionController(client=client, hud=hud, pre_roll_seconds=0.0)

        controller.key_down()

        self.assertEqual(hud.state.status, HUDStatus.ERROR)
        self.assertEqual(hud.state.error_category, ErrorCategory.MIC_PERMISSION)
        self.assertIn("Re-enable microphone permission", hud.state.error_message)

    def test_connection_error_maps_to_reconnect_recovery_and_session_resets(self) -> None:
        client = _StreamErrorClient()
        hud = FloatingHUDController()
        controller = DictationSessionController(client=client, hud=hud, pre_roll_seconds=0.0)

        controller.key_down()
        controller.push_microphone_frame(b"\x00\x01" * 2000)

        self.assertEqual(hud.state.status, HUDStatus.ERROR)
        self.assertEqual(hud.state.error_category, ErrorCategory.SERVICE_CONNECTION)
        self.assertEqual(hud.state.recovery_message, "Reconnect the device/service and retry.")

        healthy_client = _FakeSessionClient()
        controller.client = healthy_client
        controller.key_down()
        controller.push_microphone_frame(b"\x00\x01" * 2000)
        final = controller.key_up()

        self.assertIsNotNone(final)
        self.assertEqual(hud.state.status, HUDStatus.IDLE)


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
