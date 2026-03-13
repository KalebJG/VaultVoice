import unittest

from vaultvoice_desktop.app_controller import DesktopAppController, DictationState
from vaultvoice_service.models import TranscriptResult
from vaultvoice_service.service import LocalTranscriptionService


class _FakeStreamingService(LocalTranscriptionService):
    def __init__(self) -> None:
        super().__init__()
        self._partials = ["hello", "hello world"]

    def stream_microphone_frame(self, session_id: str, pcm_frame: bytes) -> list[TranscriptResult]:
        _ = (session_id, pcm_frame)
        if not self._partials:
            return []
        return [TranscriptResult(text=self._partials.pop(0), is_final=False, confidence=0.9)]

    def finalize(self, session_id: str) -> TranscriptResult:
        _ = session_id
        return TranscriptResult(text="hello world", is_final=True, confidence=0.95)


class _FailingStartService:
    def start(self) -> str:
        raise RuntimeError("service unavailable")


class DesktopAppControllerTests(unittest.TestCase):
    def test_push_to_talk_lifecycle_updates_transcript_in_memory(self) -> None:
        controller = DesktopAppController(service_client=_FakeStreamingService())

        controller.push_to_talk_down()
        self.assertEqual(controller.state.status, DictationState.LISTENING)
        self.assertIsNotNone(controller.state.active_session_id)

        controller.ingest_microphone_frame(b"\x00\x00" * 100)
        self.assertEqual(controller.state.live_transcript, "hello")

        controller.ingest_microphone_frame(b"\x00\x00" * 100)
        self.assertEqual(controller.state.live_transcript, "hello world")

        controller.push_to_talk_up()
        self.assertEqual(controller.state.status, DictationState.IDLE)
        self.assertIsNone(controller.state.active_session_id)
        self.assertEqual(controller.state.final_transcript, "hello world")
        self.assertEqual(controller.state.live_transcript, "hello world")

    def test_start_failure_transitions_to_error_state(self) -> None:
        controller = DesktopAppController(service_client=_FailingStartService())

        controller.push_to_talk_down()

        self.assertEqual(controller.state.status, DictationState.ERROR)
        self.assertIn("Unable to start dictation session", controller.state.last_error or "")


if __name__ == "__main__":
    unittest.main()
