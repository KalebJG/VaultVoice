from __future__ import annotations


FORBIDDEN_LOG_FIELDS = {"transcript", "audio", "audio_chunk", "raw_text"}


def assert_safe_log_fields(payload: dict[str, object]) -> None:
    forbidden = FORBIDDEN_LOG_FIELDS.intersection(payload.keys())
    if forbidden:
        raise ValueError(f"Forbidden log fields present: {sorted(forbidden)}")
