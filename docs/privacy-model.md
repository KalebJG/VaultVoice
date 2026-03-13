# VaultVoice Privacy Model (MVP)

## Principle
VaultVoice MVP is **memory-only** for speech data.

## Data Lifecycle
1. Audio enters process memory during push-to-talk capture.
2. Audio chunks are processed and discarded in memory.
3. Transcript text exists in memory for active session display/use.
4. Session state is cleared when dictation finalizes or resets.

## Explicitly Disallowed in MVP
- Writing transcript text to disk
- Writing raw/encoded audio to disk
- Exporting transcript files
- Logging transcript or audio payloads

## Allowed Telemetry
- Timing metrics (start latency, finalize latency)
- Error codes
- CPU load summaries
- Session counts

## Enforcement Approach
- Runtime retention mode defaults to `memory_only`.
- Guard utility blocks persistence targets in service code paths.
- Unit tests verify retention and logging guard behavior.
