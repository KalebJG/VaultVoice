import unittest
from os import environ

from vaultvoice_service.logging_utils import assert_safe_log_fields
from vaultvoice_service.models import TranscriptResult
from vaultvoice_service.observability import PrivacySafeMetrics
from vaultvoice_service.provider import TranscriptionProvider
from vaultvoice_service.service import LocalTranscriptionService


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


class _StartPermissionProvider(_FixedProvider):
    def start_session(self) -> str:
        raise PermissionError("permission denied")


class _StartDeviceProvider(_FixedProvider):
    def start_session(self) -> str:
        raise OSError("device missing")


class _FinalizeFailingProvider(_FixedProvider):
    def finalize_session(self, session_id: str) -> TranscriptResult:
        _ = session_id
        raise ConnectionError("provider offline")


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
    def test_service_uses_stub_provider_when_flag_disabled(self) -> None:
        original = environ.get("VAULTVOICE_USE_REAL_PROVIDER")
        environ["VAULTVOICE_USE_REAL_PROVIDER"] = "0"
        try:
            service = LocalTranscriptionService()
            session_id = service.start()
            partial = service.stream_chunk(session_id, b"\xe8\x03" * 160)
            final = service.finalize(session_id)
        finally:
            if original is None:
                environ.pop("VAULTVOICE_USE_REAL_PROVIDER", None)
            else:
                environ["VAULTVOICE_USE_REAL_PROVIDER"] = original

        self.assertEqual(partial.text, "")
        self.assertFalse(partial.is_final)
        self.assertEqual(final.text, "")
        self.assertTrue(final.is_final)

    def test_health_includes_mic_and_provider_status(self) -> None:
        service = LocalTranscriptionService(provider=_FixedProvider())
        health = service.health()

        self.assertEqual(health.microphone_status, "available")
        self.assertEqual(health.provider_status, "connected")

    def test_health_updates_when_mic_permission_missing(self) -> None:
        service = LocalTranscriptionService(provider=_StartPermissionProvider())

        with self.assertRaises(PermissionError):
            service.start()

        health = service.health()
        self.assertEqual(health.status, "degraded")
        self.assertEqual(health.microphone_status, "permission_required")
        self.assertEqual(health.provider_status, "degraded")

    def test_health_updates_when_mic_device_unavailable(self) -> None:
        service = LocalTranscriptionService(provider=_StartDeviceProvider())

        with self.assertRaises(OSError):
            service.start()

        health = service.health()
        self.assertEqual(health.status, "degraded")
        self.assertEqual(health.microphone_status, "device_unavailable")
        self.assertEqual(health.provider_status, "degraded")

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

    def test_finalize_failure_marks_provider_degraded(self) -> None:
        service = LocalTranscriptionService(provider=_FinalizeFailingProvider())
        session_id = service.start()

        with self.assertRaises(ConnectionError):
            service.finalize(session_id)

        health = service.health()
        self.assertEqual(health.provider_status, "degraded")

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
