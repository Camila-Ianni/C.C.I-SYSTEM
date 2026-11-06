"""
test_phase8_evolution.py - Suite de pruebas unitarias para la Fase 8 (Adaptación iOS).

Verifica:
1. Cálculo de Safe Area para Notch, Dynamic Island e iPad.
2. Desplazamiento preventivo de controles táctiles fuera de zonas ciegas en iOS.
3. Despacho de retroalimentación háptica (UIImpactFeedbackGenerator).
4. Ciclo de vida y suspensión de audio en iOS.
5. Validación estructural de `ios/Info.plist` y `ios/Entitlements.plist`.
6. Ejecución del preflight check de iOS.
"""
from pathlib import Path
import plistlib
import unittest
import pygame

# Initialize pygame headless
pygame.init()
if not pygame.display.get_init() or not pygame.display.get_surface():
    pygame.display.set_mode((1, 1), pygame.NOFRAME)

from mobile.ios_adapter import IOSAdapter
from ios.build_ios import validate_info_plist, run_ios_preflight


class TestPhase8Evolution(unittest.TestCase):

    def setUp(self):
        self.adapter = IOSAdapter(1280, 720, device_type="dynamic_island")

    def test_ios_safe_area_presets(self):
        """Verifica el cálculo de márgenes para diferentes factores de forma iOS."""
        # Dynamic Island (iPhone 14 Pro, 15, 16)
        sa_island = IOSAdapter.calculate_safe_area("dynamic_island", 1280, 720)
        self.assertGreater(sa_island[0], 0, "Margen izquierdo no debe ser cero en Dynamic Island")
        self.assertGreater(sa_island[2], 0, "Margen derecho no debe ser cero en Dynamic Island")
        self.assertGreater(sa_island[3], 0, "Margen inferior no debe ser cero (Home Bar)")

        # Notch (iPhone X/11/12/13/14)
        sa_notch = IOSAdapter.calculate_safe_area("notch", 1280, 720)
        self.assertGreater(sa_notch[0], 0)
        self.assertGreater(sa_notch[2], 0)

        # Classic (iPhone SE con botón home)
        sa_classic = IOSAdapter.calculate_safe_area("classic", 1280, 720)
        self.assertEqual(sa_classic, (0, 0, 0, 0))

    def test_touch_gamepad_offset_under_safe_area(self):
        """Comprueba que el mando virtual no se superpone con la Dynamic Island o el Home Bar."""
        left_inset, _, right_inset, bottom_inset = self.adapter.safe_area

        # D-pad debe estar desplazado a la derecha por el margen izquierdo
        expected_dpad_x = 130 + left_inset
        self.assertEqual(self.adapter.touch_gamepad.dpad_center[0], expected_dpad_x)

        # Botón A o Punch debe estar desplazado hacia la izquierda por el margen derecho
        punch_heavy_x = self.adapter.touch_gamepad.buttons["punch_heavy"][0]
        # Con sw=1280, bx = 1280 - 140 - right_inset = 1140 - right_inset. punch_heavy_x = bx + 68
        self.assertLess(punch_heavy_x, 1280 - right_inset)

    def test_ios_haptic_feedback(self):
        """Verifica la invocación de estilos de háptica válidos."""
        self.assertTrue(self.adapter.trigger_haptic("light"))
        self.assertTrue(self.adapter.trigger_haptic("medium"))
        self.assertTrue(self.adapter.trigger_haptic("heavy"))
        self.assertTrue(self.adapter.trigger_haptic("selection"))
        self.assertFalse(self.adapter.trigger_haptic("invalid_style"))

    def test_ios_lifecycle_event_handling(self):
        """Verifica la gestión del ciclo de vida de suspensión y reanudación."""
        self.assertFalse(self.adapter.is_backgrounded)

        # Suspender app
        ev_bg = getattr(pygame, "APP_WILLENTERBACKGROUND", 0x101)
        handled = self.adapter.handle_lifecycle_event(ev_bg)
        self.assertTrue(handled)
        self.assertTrue(self.adapter.is_backgrounded)

        # Reanudar app
        ev_fg = getattr(pygame, "APP_DIDENTERFOREGROUND", 0x102)
        handled = self.adapter.handle_lifecycle_event(ev_fg)
        self.assertTrue(handled)
        self.assertFalse(self.adapter.is_backgrounded)

    def test_info_plist_validity(self):
        """Verifica que ios/Info.plist cumpla con las directivas de Apple."""
        root_dir = Path(__file__).resolve().parent
        plist_path = root_dir / "ios" / "Info.plist"
        self.assertTrue(plist_path.is_file(), "ios/Info.plist debe existir")

        data = validate_info_plist(plist_path)
        self.assertEqual(data["CFBundleIdentifier"], "org.ccisystem.arcade")
        self.assertEqual(data["CFBundleDisplayName"], "C.C.I. SYSTEM")
        self.assertEqual(data["CFBundleShortVersionString"], "2.1.0")

        # Comprobar obligatoriedad del permiso de micrófono para WebRTC
        self.assertIn("NSMicrophoneUsageDescription", data)
        self.assertTrue(len(data["NSMicrophoneUsageDescription"]) > 10)

        # Comprobar modo audio en background
        self.assertIn("audio", data.get("UIBackgroundModes", []))

    def test_entitlements_plist_validity(self):
        """Verifica que ios/Entitlements.plist contenga los privilegios de red y audio."""
        root_dir = Path(__file__).resolve().parent
        ent_path = root_dir / "ios" / "Entitlements.plist"
        self.assertTrue(ent_path.is_file(), "ios/Entitlements.plist debe existir")

        with open(ent_path, "rb") as fp:
            data = plistlib.load(fp)

        self.assertTrue(data.get("com.apple.security.network.client"))
        self.assertTrue(data.get("com.apple.security.device.audio-input"))

    def test_ios_preflight_check(self):
        """Ejecuta el chequeo previo de la toolchain iOS."""
        root_dir = Path(__file__).resolve().parent
        ok = run_ios_preflight(root_dir)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
