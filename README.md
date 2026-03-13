# VaultVoice

VaultVoice is a macOS-first, CPU-oriented dictation app focused on high-quality short-form speech-to-text with strict privacy defaults.

## MVP Constraints
- macOS first
- CPU-only baseline (no GPU required)
- Accuracy-first transcription profile
- Push-to-talk default flow
- Default shortcut target: `fn` (fallback if unsupported)
- Tiny floating HUD
- No transcript/audio persistence
- No export features

## Repository Layout
- `apps/desktop`: Lightweight desktop shell and HUD
- `apps/local-service`: Local transcription service and privacy guardrails
- `docs`: Product and engineering documentation

## Build Order
Implementation sequencing is documented in:
- `docs/MVP_IMPLEMENTATION_TICKETS.md`

## Local Development (initial scaffold)
1. Create a Python 3.11+ virtual environment.
2. Install local service dependencies from `apps/local-service/pyproject.toml`.
3. Run tests from repository root:
   - `PYTHONPATH=apps/local-service/src python -m unittest discover -s apps/local-service/tests`

> Note: This commit scaffolds architecture and guardrails, not full dictation/audio capture yet.
