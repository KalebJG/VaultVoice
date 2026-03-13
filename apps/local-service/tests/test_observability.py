import unittest

from vaultvoice_service.logging_utils import assert_safe_log_fields
from vaultvoice_service.observability import PrivacySafeMetrics
from vaultvoice_service.provider import TranscriptionProvider
from vaultvoice_service.service import LocalTranscriptionService
from vaultvoice_service.models import TranscriptResult


class _FixedProvider(TranscriptionProvider):
    def __init__(self) -> None:
        self.last_chunk: bytes | None = None
        self.chunks: list[bytes] = []

    def start_session(self) -> str:
        return "session-1"

    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        _ = session_id
        self.last_chunk = pcm_chunk
        self.chunks.append(pcm_chunk)
        return TranscriptResult(text="", is_final=False)

    def finalize_session(self, session_id: str) -> TranscriptResult:
        _ = session_id
        return TranscriptResult(text="", is_final=True)


class _FailingProvider(_FixedProvider):
    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        _ = (session_id, pcm_chunk)
        raise RuntimeError("provider error")




class _CpuSequenceMetrics(PrivacySafeMetrics):
    def __init__(self, loads: list[float | None]) -> None:
        super().__init__()
        self._loads = list(loads)

    def snapshot(self):
        load = self._loads.pop(0) if self._loads else None
        snap = super().snapshot()
        snap.cpu_load = load
        return snap


class ObservabilityTests(unittest.TestCase):
    def test_metrics_capture_session_chunk_and_latencies(self) -> None:
        service = LocalTranscriptionService(provider=_FixedProvider())

        session_id = service.start()
        partial = service.stream_chunk(session_id, b"\xe8\x03" * 160)
        final = service.finalize(session_id)
        snapshot = service.metrics_snapshot()

        self.assertEqual(partial.is_final, False)
        self.assertEqual(final.is_final, True)
        self.assertEqual(snapshot.total_sessions_started, 1)
        self.assertEqual(snapshot.total_chunks_processed, 1)
        self.assertEqual(snapshot.total_chunks_skipped, 0)
        self.assertEqual(snapshot.total_errors, 0)
        self.assertIsNotNone(snapshot.last_stream_latency_ms)
        self.assertIsNotNone(snapshot.last_finalize_latency_ms)

    def test_silence_chunk_skipped(self) -> None:
        provider = _FixedProvider()
        service = LocalTranscriptionService(provider=provider)
        session_id = service.start()

        response = service.stream_chunk(session_id, b"\x00\x00" * 100)
        snapshot = service.metrics_snapshot()

        self.assertFalse(response.is_final)
        self.assertEqual(response.text, "")
        self.assertEqual(snapshot.total_chunks_processed, 0)
        self.assertEqual(snapshot.total_chunks_skipped, 1)
        self.assertIsNone(provider.last_chunk)

    def test_overlap_prepended_for_following_speech_chunks(self) -> None:
        provider = _FixedProvider()
        service = LocalTranscriptionService(provider=provider)
        session_id = service.start()

        first_chunk = b"\xe8\x03" * 200
        second_chunk = b"\xd0\x07" * 200

        service.stream_chunk(session_id, first_chunk)
        service.stream_chunk(session_id, second_chunk)

        expected_overlap = service.preprocessor.overlap_bytes(first_chunk)
        self.assertEqual(provider.last_chunk, expected_overlap + second_chunk)


    def test_microphone_frames_chunked_and_flushed_on_finalize(self) -> None:
        provider = _FixedProvider()
        service = LocalTranscriptionService(provider=provider)
        session_id = service.start()

        frame = b"\xe8\x03" * 6000
        partials = service.stream_microphone_frame(session_id, frame)
        final = service.finalize(session_id)

        self.assertEqual(len(partials), 1)
        self.assertTrue(all(not result.is_final for result in partials))
        self.assertTrue(final.is_final)
        self.assertEqual(len(provider.chunks), 2)
        self.assertEqual(len(provider.chunks[0]), 10240)
        self.assertEqual(len(provider.chunks[1]), 5600)


    def test_health_surfaces_active_profile_and_fallback_state(self) -> None:
        metrics = _CpuSequenceMetrics([1.0, 1.0, 1.0])
        service = LocalTranscriptionService(provider=_FixedProvider(), metrics=metrics)
        session_id = service.start()

        for _ in range(3):
            service.stream_chunk(session_id, b"\xe8\x03" * 200)

        health = service.health()
        self.assertEqual(health.active_profile, "balanced")
        self.assertTrue(health.fallback_active)
        self.assertEqual(health.fallback_reason, "sustained_cpu_pressure")

    def test_profile_recovers_after_cpu_pressure_drops(self) -> None:
        metrics = _CpuSequenceMetrics([1.0, 1.0, 1.0, 0.1, 0.1, 0.1])
        service = LocalTranscriptionService(provider=_FixedProvider(), metrics=metrics)
        session_id = service.start()

        for _ in range(6):
            service.stream_chunk(session_id, b"\xe8\x03" * 200)

        health = service.health()
        self.assertEqual(health.active_profile, "accuracy")
        self.assertFalse(health.fallback_active)
        self.assertIsNone(health.fallback_reason)

    def test_metrics_record_errors(self) -> None:
        service = LocalTranscriptionService(provider=_FailingProvider())
        session_id = service.start()

        with self.assertRaises(RuntimeError):
            service.stream_chunk(session_id, b"\xe8\x03" * 160)

        snapshot = service.metrics_snapshot()
        self.assertEqual(snapshot.total_errors, 1)

    def test_safe_event_blocks_transcript_fields(self) -> None:
        metrics = PrivacySafeMetrics()
        safe_payload = metrics.safe_event("health", latency_ms=15)
        self.assertEqual(safe_payload["event"], "health")
        assert_safe_log_fields(safe_payload)

        with self.assertRaises(ValueError):
            metrics.safe_event("bad", transcript="secret")


if __name__ == "__main__":
    unittest.main()
