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
