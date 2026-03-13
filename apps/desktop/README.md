# VaultVoice Desktop App (macOS)

This module hosts the lightweight desktop shell for:
- Push-to-talk control
- Global hotkey settings (`fn` default with fallback)
- Tiny floating HUD states (Idle, Listening, Processing, Error)
- In-memory transcript display only

## T3.1 Scaffold status

The MVP desktop shell now includes an application controller scaffold that wires push-to-talk lifecycle events to the local-service interface:
- `push_to_talk_down()` starts a transcription session.
- `ingest_microphone_frame()` streams microphone frames and updates live partial transcript text in memory.
- `push_to_talk_up()` finalizes the session and stores final transcript text in memory.
- Error paths transition controller state to `error` with user-safe messages.

Current implementation files:
- `apps/desktop/src/vaultvoice_desktop/app_controller.py`
- `apps/desktop/tests/test_app_controller.py`

## Local test command (repo root)

```bash
PYTHONPATH=apps/local-service/src:apps/desktop/src \
  python -m unittest discover -s apps/desktop/tests
```
