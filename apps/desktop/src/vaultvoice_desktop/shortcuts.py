from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass(frozen=True, slots=True)
class Shortcut:
    key: str
    modifiers: tuple[str, ...] = ()

    def label(self) -> str:
        if not self.modifiers:
            return self.key
        return " + ".join([*self.modifiers, self.key])


DEFAULT_SHORTCUT = Shortcut(key="fn")
FALLBACK_SHORTCUT = Shortcut(key="Space", modifiers=("fn",))


class GlobalHotkeyBackend(Protocol):
    def supports(self, shortcut: Shortcut) -> bool: ...

    def register(
        self,
        shortcut: Shortcut,
        on_key_down: Callable[[], None],
        on_key_up: Callable[[], None],
    ) -> None: ...


@dataclass(slots=True)
class ShortcutSettings:
    requested_shortcut: Shortcut = DEFAULT_SHORTCUT
    active_shortcut: Shortcut = DEFAULT_SHORTCUT
    guidance_message: str | None = None


@dataclass
class GlobalShortcutManager:
    backend: GlobalHotkeyBackend
    on_key_down: Callable[[], None]
    on_key_up: Callable[[], None]
    settings: ShortcutSettings = field(default_factory=ShortcutSettings)

    def initialize(self) -> None:
        self.apply_shortcut(self.settings.requested_shortcut)

    def apply_shortcut(self, requested_shortcut: Shortcut) -> None:
        self.settings.requested_shortcut = requested_shortcut
        if self.backend.supports(requested_shortcut):
            self.backend.register(requested_shortcut, self.on_key_down, self.on_key_up)
            self.settings.active_shortcut = requested_shortcut
            self.settings.guidance_message = None
            return

        if requested_shortcut == DEFAULT_SHORTCUT and self.backend.supports(FALLBACK_SHORTCUT):
            self.backend.register(FALLBACK_SHORTCUT, self.on_key_down, self.on_key_up)
            self.settings.active_shortcut = FALLBACK_SHORTCUT
            self.settings.guidance_message = (
                "The fn-only shortcut is not supported on this macOS configuration. "
                "VaultVoice has switched to fn + Space."
            )
            return

        raise ValueError(f"Unsupported shortcut: {requested_shortcut.label()}")
