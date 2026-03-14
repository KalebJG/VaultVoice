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

## Onboarding Guides
- Shortcut setup and fallback behavior: `docs/onboarding-shortcuts.md`
- macOS microphone permission setup: `docs/onboarding-macos-mic-permissions.md`

## Release Operations
- Desktop packaging/distribution pipeline: `docs/desktop-distribution.md`
- Release gate checklist: `docs/release-checklist.md`

## Local Development
1. Create a Python 3.11+ virtual environment.
2. Install local service dependencies from `apps/local-service/pyproject.toml`.
3. Runtime requirement for the real local provider: 16-bit PCM mono audio at 16 kHz (the desktop app already streams this format).
4. Provider selection is controlled with `VAULTVOICE_USE_REAL_PROVIDER`:
   - `1` / `true` / `yes` / `on` (default): use `LocalEnergyTranscriptionProvider`.
   - `0` / `false` / `no` / `off`: force `LocalStubProvider` for scaffolding/tests.
5. Run tests from repository root:
   - `PYTHONPATH=apps/local-service/src python -m unittest discover -s apps/local-service/tests`
   - `PYTHONPATH=apps/local-service/src:apps/desktop/src python -m unittest discover -s apps/desktop/tests`

### Quick run benchmark
From repo root, run:

```bash
./scripts/run-benchmark.sh --output results.json
```

The benchmark defaults to `apps/local-service/benchmarks/dataset_manifest.json` when `--manifest` is not specified.

If you prefer direct Python execution, use:

```bash
python apps/local-service/benchmarks/run_benchmark.py --output results.json
```

### Running with the real local provider
From repo root:

```bash
export VAULTVOICE_USE_REAL_PROVIDER=1
PYTHONPATH=apps/local-service/src:apps/desktop/src python -m unittest apps.desktop.tests.test_app.DictationSessionControllerTests.test_integration_real_provider_returns_non_empty_final_text
```
