# Onboarding: macOS Microphone Permissions

VaultVoice requires microphone access to capture dictation audio.

## First launch behavior
1. On first dictation attempt, macOS prompts for microphone access.
2. Choose **Allow** to continue with live dictation.
3. If denied, VaultVoice should display recovery guidance instead of silently failing.

## If access is denied
1. Open **System Settings**.
2. Go to **Privacy & Security** -> **Microphone**.
3. Enable microphone access for VaultVoice.
4. Restart VaultVoice if macOS does not immediately apply permission changes.

## UX requirements to validate
- Permission prompt appears at first point of capture.
- Denial state communicates why dictation cannot proceed.
- Recovery path to System Settings is clear and actionable.
- Granting access restores normal push-to-talk flow and HUD states.
