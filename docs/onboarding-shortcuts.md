# Onboarding: Shortcut Configuration

VaultVoice starts with a push-to-talk shortcut optimized for fast dictation:

- Default: `fn`
- Automatic fallback: `fn + Space`

## First-run expectations
1. App attempts to register `fn` as global shortcut.
2. If unsupported by the environment, app falls back to `fn + Space`.
3. HUD should show the active shortcut and allow users to verify what is currently bound.

## Changing the shortcut
1. Open VaultVoice shortcut settings.
2. Select a new key combination that does not conflict with system-wide shortcuts.
3. Save and confirm HUD now displays the updated shortcut.
4. Test push-to-talk start (keydown) and finalize (keyup).

## Validation checklist
- Shortcut starts listening on key down.
- Releasing shortcut finalizes dictation.
- Updated shortcut remains active after app restart.
- If chosen shortcut becomes unavailable, fallback behavior remains functional.
