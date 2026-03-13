import unittest

from vaultvoice_desktop.shortcuts import (
    DEFAULT_SHORTCUT,
    FALLBACK_SHORTCUT,
    GlobalShortcutManager,
    Shortcut,
)


class _FakeHotkeyBackend:
    def __init__(self, supported: set[Shortcut]) -> None:
        self._supported = supported
        self.registered_shortcut: Shortcut | None = None
        self._down = None
        self._up = None

    def supports(self, shortcut: Shortcut) -> bool:
        return shortcut in self._supported

    def register(self, shortcut, on_key_down, on_key_up) -> None:
        self.registered_shortcut = shortcut
        self._down = on_key_down
        self._up = on_key_up

    def trigger_down(self) -> None:
        if self._down is not None:
            self._down()

    def trigger_up(self) -> None:
        if self._up is not None:
            self._up()


class ShortcutManagerTests(unittest.TestCase):
    def test_uses_fn_shortcut_when_supported(self) -> None:
        events: list[str] = []
        backend = _FakeHotkeyBackend(supported={DEFAULT_SHORTCUT})
        manager = GlobalShortcutManager(backend=backend, on_key_down=lambda: events.append("down"), on_key_up=lambda: events.append("up"))

        manager.initialize()
        backend.trigger_down()
        backend.trigger_up()

        self.assertEqual(backend.registered_shortcut, DEFAULT_SHORTCUT)
        self.assertEqual(manager.settings.active_shortcut, DEFAULT_SHORTCUT)
        self.assertIsNone(manager.settings.guidance_message)
        self.assertEqual(events, ["down", "up"])

    def test_falls_back_to_fn_space_when_fn_only_not_supported(self) -> None:
        backend = _FakeHotkeyBackend(supported={FALLBACK_SHORTCUT})
        manager = GlobalShortcutManager(backend=backend, on_key_down=lambda: None, on_key_up=lambda: None)

        manager.initialize()

        self.assertEqual(backend.registered_shortcut, FALLBACK_SHORTCUT)
        self.assertEqual(manager.settings.active_shortcut, FALLBACK_SHORTCUT)
        self.assertIsNotNone(manager.settings.guidance_message)

    def test_user_shortcut_picker_applies_supported_shortcut(self) -> None:
        custom = Shortcut(key="D", modifiers=("cmd", "shift"))
        backend = _FakeHotkeyBackend(supported={DEFAULT_SHORTCUT, custom})
        manager = GlobalShortcutManager(backend=backend, on_key_down=lambda: None, on_key_up=lambda: None)

        manager.initialize()
        manager.apply_shortcut(custom)

        self.assertEqual(manager.settings.requested_shortcut, custom)
        self.assertEqual(manager.settings.active_shortcut, custom)
        self.assertEqual(backend.registered_shortcut, custom)

    def test_unsupported_user_shortcut_raises(self) -> None:
        unsupported = Shortcut(key="K", modifiers=("ctrl",))
        backend = _FakeHotkeyBackend(supported={DEFAULT_SHORTCUT})
        manager = GlobalShortcutManager(backend=backend, on_key_down=lambda: None, on_key_up=lambda: None)

        manager.initialize()

        with self.assertRaises(ValueError):
            manager.apply_shortcut(unsupported)


if __name__ == "__main__":
    unittest.main()
