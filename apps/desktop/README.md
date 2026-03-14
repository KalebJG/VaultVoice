# VaultVoice Desktop App (macOS)

This module hosts the lightweight desktop shell scaffolding for:
- Push-to-talk dictation lifecycle (keydown start, keyup finalize)
- Global shortcut registration with `fn` default and `fn + Space` fallback
- Local-service integration via a dedicated session client adapter
- In-memory transcript state for live partial and final text display
- Tiny floating HUD state model for Idle / Listening / Processing / Error

## Current implementation
- `vaultvoice_desktop.app.ServiceSessionClient` bridges desktop controls to `LocalTranscriptionService`.
- `vaultvoice_desktop.app.DictationSessionController` provides push-to-talk control methods and in-memory transcript state.
- `vaultvoice_desktop.shortcuts.GlobalShortcutManager` handles default shortcut registration, fallback behavior, and user-selected shortcuts.
- `vaultvoice_desktop.hud.FloatingHUDController` manages HUD status, shortcut/mic indicators, drag position, and opacity settings.
- Tests validate desktop-to-service dictation flow and shortcut fallback/customization behavior.

## Running tests
From repo root:

```bash
PYTHONPATH=apps/local-service/src:apps/desktop/src python -m unittest discover -s apps/desktop/tests
```

## Runtime requirements
- Python 3.11+
- Local service import path available via `PYTHONPATH=apps/local-service/src:apps/desktop/src`
- Real provider path expects 16-bit PCM mono audio at 16 kHz and is enabled by default.

## Running with the real provider
`LocalTranscriptionService` uses the concrete local provider by default. You can run the integration test directly:

```bash
VAULTVOICE_USE_REAL_PROVIDER=1 \
PYTHONPATH=apps/local-service/src:apps/desktop/src \
python -m unittest apps.desktop.tests.test_app.DictationSessionControllerTests.test_integration_real_provider_returns_non_empty_final_text
```

To switch back to the stub provider for scaffolding-only behavior:

```bash
VAULTVOICE_USE_REAL_PROVIDER=0 PYTHONPATH=apps/local-service/src:apps/desktop/src python -m unittest discover -s apps/desktop/tests
```
