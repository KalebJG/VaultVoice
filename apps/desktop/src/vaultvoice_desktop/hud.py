from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from vaultvoice_service.models import ServiceHealth

from .shortcuts import Shortcut


class HUDStatus(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass(slots=True)
class HUDSettings:
    x: int = 24
    y: int = 24
    opacity: float = 0.85


@dataclass(slots=True)
class HUDState:
    status: HUDStatus = HUDStatus.IDLE
    shortcut_label: str = "fn"
    mic_available: bool = True
    mic_status: str = "available"
    service_status: str = "connected"
    settings: HUDSettings = field(default_factory=HUDSettings)
    error_message: str | None = None
    error_category: str | None = None
    recovery_message: str | None = None


@dataclass
class FloatingHUDController:
    state: HUDState = field(default_factory=HUDState)

    def set_shortcut(self, shortcut: Shortcut) -> None:
        self.state.shortcut_label = shortcut.label()

    def set_mic_available(self, available: bool) -> None:
        self.state.mic_available = available

    def set_health(self, health: ServiceHealth) -> None:
        self.state.mic_status = health.microphone_status
        self.state.service_status = health.provider_status
        self.state.mic_available = health.microphone_status == "available"

    def on_key_down(self) -> None:
        self.state.status = HUDStatus.LISTENING
        self.state.error_message = None
        self.state.error_category = None
        self.state.recovery_message = None

    def on_key_up(self) -> None:
        self.state.status = HUDStatus.PROCESSING

    def on_transcription_complete(self) -> None:
        self.state.status = HUDStatus.IDLE

    def on_error(self, message: str, category: str | None = None, recovery_message: str | None = None) -> None:
        self.state.status = HUDStatus.ERROR
        self.state.error_message = message
        self.state.error_category = category
        self.state.recovery_message = recovery_message

    def drag_to(self, x: int, y: int) -> None:
        self.state.settings.x = x
        self.state.settings.y = y

    def set_opacity(self, opacity: float) -> None:
        self.state.settings.opacity = min(1.0, max(0.3, opacity))
