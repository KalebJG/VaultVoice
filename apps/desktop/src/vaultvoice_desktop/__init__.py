"""Desktop shell scaffolding for VaultVoice MVP."""

from .app import DictationSessionController, ServiceSessionClient, TranscriptState
from .hud import FloatingHUDController, HUDSettings, HUDState, HUDStatus
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
    "FloatingHUDController",
    "GlobalShortcutManager",
    "HUDSettings",
    "HUDState",
    "HUDStatus",
    "ServiceSessionClient",
    "Shortcut",
    "ShortcutSettings",
    "TranscriptState",
]
