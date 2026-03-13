"""Desktop shell scaffolding for VaultVoice MVP."""

from .app import DictationSessionController, ServiceSessionClient, TranscriptState
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
    "DictationSessionController",
    "GlobalShortcutManager",
    "ServiceSessionClient",
    "Shortcut",
    "ShortcutSettings",
    "TranscriptState",
]
