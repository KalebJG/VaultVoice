"""Desktop shell scaffolding for VaultVoice MVP."""

from .app import (
    AudioCapturePolicy,
    DictationLifecycleState,
    DictationLifecycleStateMachine,
    DictationSessionController,
    ServiceSessionClient,
    TranscriptState,
)
from .shortcuts import (
    DEFAULT_SHORTCUT,
    FALLBACK_SHORTCUT,
    GlobalShortcutManager,
    Shortcut,
    ShortcutSettings,
)

__all__ = [
    "DEFAULT_SHORTCUT",
    "FALLBACK_SHORTCUT",
    "AudioCapturePolicy",
    "DictationLifecycleState",
    "DictationLifecycleStateMachine",
    "DictationSessionController",
    "GlobalShortcutManager",
    "ServiceSessionClient",
    "Shortcut",
    "ShortcutSettings",
    "TranscriptState",
]
