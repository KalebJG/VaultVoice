import unittest

from vaultvoice_desktop.app import DictationSessionController, ServiceSessionClient
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


class DictationSessionControllerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
