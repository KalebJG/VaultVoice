import unittest

from vaultvoice_desktop.hud import FloatingHUDController, HUDStatus
from vaultvoice_desktop.shortcuts import Shortcut


class FloatingHUDControllerTests(unittest.TestCase):
    def test_tracks_lifecycle_states(self) -> None:
        hud = FloatingHUDController()

        self.assertEqual(hud.state.status, HUDStatus.IDLE)
        hud.on_key_down()
        self.assertEqual(hud.state.status, HUDStatus.LISTENING)
        hud.on_key_up()
        self.assertEqual(hud.state.status, HUDStatus.PROCESSING)
        hud.on_transcription_complete()
        self.assertEqual(hud.state.status, HUDStatus.IDLE)

    def test_records_error_state(self) -> None:
        hud = FloatingHUDController()

        hud.on_error("provider timeout")

        self.assertEqual(hud.state.status, HUDStatus.ERROR)
        self.assertEqual(hud.state.error_message, "provider timeout")

    def test_updates_shortcut_and_settings(self) -> None:
        hud = FloatingHUDController()

        hud.set_shortcut(Shortcut(key="Space", modifiers=("fn",)))
        hud.set_mic_available(False)
        hud.drag_to(120, 88)
        hud.set_opacity(1.5)

        self.assertEqual(hud.state.shortcut_label, "fn + Space")
        self.assertFalse(hud.state.mic_available)
        self.assertEqual(hud.state.settings.x, 120)
        self.assertEqual(hud.state.settings.y, 88)
        self.assertEqual(hud.state.settings.opacity, 1.0)


if __name__ == "__main__":
    unittest.main()
