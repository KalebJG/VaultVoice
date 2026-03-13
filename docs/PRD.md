# VaultVoice Product Requirements Document (MVP)

## Product Summary
VaultVoice is a lightweight macOS desktop dictation app for short-form voice-to-text, optimized for CPU-only hardware and strict privacy.

## Locked MVP Decisions
- Platform: macOS first
- Input style: Short-form dictation
- Quality objective: Accuracy first
- Connectivity: Internet allowed (offline not required)
- Retention: No transcript/audio persistence
- Export: No export options in MVP
- Controls: Push-to-talk, default `fn` shortcut with fallback support
- UI: Tiny floating HUD showing dictation state

## Goals
1. Deliver excellent short-form transcription quality on CPU hardware.
2. Keep latency acceptable for push-to-talk interactions.
3. Guarantee memory-only handling of transcript/audio data.

## Non-Goals
- Chrome extension in MVP
- Transcript history or search
- Domain-specific vocabulary tuning
- Enterprise compliance features

## Success Metrics
- WER (clean speech): <= 12%
- WER (moderate noise): <= 20%
- Press-to-first-text latency: <= 1.5s on reference CPU hardware
- Stop-to-final-text latency: <= 2.0s for short utterances
- Default retention compliance: 0 transcript/audio persistence artifacts

## Core User Flow
1. User presses and holds push-to-talk hotkey.
2. Service captures audio and streams partial transcription.
3. User releases key to finalize transcript.
4. HUD reflects Idle -> Listening -> Processing -> Idle.
5. Transcript remains in memory only.

## Risks
- `fn` key may be unreliable as standalone global hotkey on all macOS setups.
- CPU constraints may increase latency on lower-end machines.

## Risk Mitigations
- Provide fallback shortcut (`fn + Space`) with settings-based override.
- Implement model/profile fallback when sustained CPU pressure is detected.
