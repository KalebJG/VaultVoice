# VaultVoice Engineering Standards

## Privacy Rules (Non-Negotiable)
1. Never persist raw audio or transcript text in MVP.
2. Never log transcript content or raw audio bytes.
3. Keep user speech data in memory only.
4. Any future persistence/export feature requires explicit product approval and security review.

## Logging Rules
- Allowed: counters, durations, CPU/memory usage, error codes, state transitions.
- Forbidden: transcript strings, chunk payload bytes, prompt text derived from user speech.

## Service Design Rules
- Build behind interfaces (provider abstraction).
- Keep retention policy enforced in code, not docs only.
- Favor deterministic behavior and graceful fallback.

## Testing Rules
- Add unit tests for privacy guardrails and redaction.
- Include no-retention assertions in CI gates.
- Avoid tests requiring network or external APIs for baseline checks.
