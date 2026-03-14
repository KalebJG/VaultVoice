import unittest

from vaultvoice_desktop.app import (
    AudioCapturePolicy,
    DictationLifecycleState,
    DictationLifecycleStateMachine,
    DictationSessionController,
    ServiceSessionClient,
)
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


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class AudioCapturePolicyTests(unittest.TestCase):
    def test_pre_roll_is_capped_and_flushed(self) -> None:
        policy = AudioCapturePolicy(pre_roll_max_bytes=8, minimum_utterance_bytes=6)

        policy.capture_frame(b"aa", listening=False)
        policy.capture_frame(b"bbbb", listening=False)
        policy.capture_frame(b"cccc", listening=False)

        self.assertEqual(policy.flush_pre_roll(), [b"bbbb", b"cccc"])

    def test_minimum_utterance_uses_listening_bytes_only(self) -> None:
        policy = AudioCapturePolicy(pre_roll_max_bytes=20, minimum_utterance_bytes=6)

        policy.capture_frame(b"pre-roll", listening=False)
        pre_roll = policy.begin_utterance()
        policy.capture_frame(b"1234", listening=True)

        self.assertEqual(pre_roll, [b"pre-roll"])
        self.assertFalse(policy.has_minimum_utterance())


class DictationLifecycleStateMachineTests(unittest.TestCase):
    def test_debounce_blocks_immediate_restart(self) -> None:
        clock = _FakeClock()
        lifecycle = DictationLifecycleStateMachine(debounce_seconds=0.2, clock=clock)

        self.assertTrue(lifecycle.start_listening())
        self.assertTrue(lifecycle.stop_listening())
        lifecycle.complete()

        self.assertFalse(lifecycle.start_listening())
        clock.now += 0.21
        self.assertTrue(lifecycle.start_listening())

    def test_error_transition(self) -> None:
        lifecycle = DictationLifecycleStateMachine()
        lifecycle.fail()
        self.assertEqual(lifecycle.state, DictationLifecycleState.ERROR)


class DictationSessionControllerTests(unittest.TestCase):
    def test_orchestrates_pre_roll_streaming_and_finalize(self) -> None:
        service = LocalTranscriptionService(provider=_DesktopProvider())
        controller = DictationSessionController(client=ServiceSessionClient(service=service))

        controller.push_microphone_frame(b"\xe8\x03" * 50)
        controller.key_down()
        controller.push_microphone_frame(b"\xe8\x03" * 6000)
        final = controller.key_up()

        self.assertIsNotNone(final)
        self.assertFalse(controller.transcript.is_listening)
        self.assertEqual(controller.transcript.partial_text, "")
        self.assertEqual(controller.transcript.final_text, "final-2")


if __name__ == "__main__":
    unittest.main()
