"""
test_phase7_evolution.py - Suite de pruebas unitarias para la Fase 7 (Adaptación Android).

Verifica:
1. Geometría y escalado de VirtualTouchGamepad.
2. D-pad multitáctil, deadzone y botones de acción en diferentes layouts.
3. Multitouch concurrente (dos dedos al mismo tiempo).
4. Auto-ocultación al conectar gamepad físico Bluetooth/USB.
5. MobileAdapter: ciclo de vida de la app (pausa/reanudación de audio y callbacks).
6. Botón físico Volver (K_AC_BACK / Escape).
7. Integridad de buildozer.spec y script build_apk.
"""
from pathlib import Path
import unittest
import pygame

# Initialize pygame headless for tests
pygame.init()
if not pygame.display.get_init() or not pygame.display.get_surface():
    pygame.display.set_mode((1, 1), pygame.NOFRAME)

from mobile.touch_controls import VirtualTouchGamepad
from mobile.mobile_adapter import MobileAdapter
from mobile.build_apk import validate_spec, run_preflight_checks


class TestPhase7Evolution(unittest.TestCase):

    def setUp(self):
        self.gamepad = VirtualTouchGamepad(1280, 720, layout="arcade")
        self.adapter = MobileAdapter(1280, 720)

    def test_virtual_gamepad_init_and_scaling(self):
        """Verifica inicialización y escalado de los controles táctiles."""
        self.assertEqual(self.gamepad.screen_w, 1280)
        self.assertEqual(self.gamepad.screen_h, 720)
        self.assertEqual(self.gamepad.layout, "arcade")
        self.assertTrue(self.gamepad.enabled)
        self.assertTrue(self.gamepad.visible)

        # 6 botones arcade en layout arcade
        self.assertIn("punch_light", self.gamepad.buttons)
        self.assertIn("kick_heavy", self.gamepad.buttons)

        # Probar layout standard (4 botones)
        standard_pad = VirtualTouchGamepad(1280, 720, layout="standard")
        self.assertIn("btn_a", standard_pad.buttons)
        self.assertIn("btn_b", standard_pad.buttons)
        self.assertIn("btn_x", standard_pad.buttons)
        self.assertIn("btn_y", standard_pad.buttons)

    def test_virtual_gamepad_dpad_touch(self):
        """Verifica detección de direcciones en el D-Pad mediante toques simulados."""
        cx, cy = self.gamepad.dpad_center
        # Toque a la derecha del centro del D-Pad
        touch_x = (cx + 50) / 1280.0
        touch_y = cy / 720.0

        ev = pygame.event.Event(pygame.FINGERDOWN, {"finger_id": 1, "x": touch_x, "y": touch_y})
        self.gamepad.handle_event(ev)

        self.assertIn("right", self.gamepad.active_controls)
        self.assertTrue(self.gamepad.is_pressed("dpad_right"))
        self.assertTrue(self.gamepad.is_pressed("right"))

        # Liberar dedo
        ev_up = pygame.event.Event(pygame.FINGERUP, {"finger_id": 1})
        self.gamepad.handle_event(ev_up)
        self.assertNotIn("right", self.gamepad.active_controls)
        self.assertFalse(self.gamepad.is_pressed("right"))

    def test_virtual_gamepad_button_touch(self):
        """Verifica detección de toques en botones de acción."""
        bx, by = self.gamepad.buttons["punch_light"]
        touch_x = bx / 1280.0
        touch_y = by / 720.0

        ev = pygame.event.Event(pygame.FINGERDOWN, {"finger_id": 2, "x": touch_x, "y": touch_y})
        self.gamepad.handle_event(ev)

        self.assertIn("punch_light", self.gamepad.active_controls)
        self.assertTrue(self.gamepad.is_pressed("punch_light"))

        ev_up = pygame.event.Event(pygame.FINGERUP, {"finger_id": 2})
        self.gamepad.handle_event(ev_up)
        self.assertNotIn("punch_light", self.gamepad.active_controls)

    def test_virtual_gamepad_multitouch_concurrency(self):
        """Verifica manejo concurrente de múltiples dedos simultáneos."""
        cx, cy = self.gamepad.dpad_center
        bx, by = self.gamepad.buttons["kick_heavy"]

        # Dedo 1: D-pad abajo
        ev1 = pygame.event.Event(pygame.FINGERDOWN, {"finger_id": 10, "x": cx / 1280.0, "y": (cy + 50) / 720.0})
        # Dedo 2: Patada fuerte
        ev2 = pygame.event.Event(pygame.FINGERDOWN, {"finger_id": 11, "x": bx / 1280.0, "y": by / 720.0})

        self.gamepad.handle_event(ev1)
        self.gamepad.handle_event(ev2)

        self.assertTrue(self.gamepad.is_pressed("dpad_down"))
        self.assertTrue(self.gamepad.is_pressed("kick_heavy"))

        # Levantar solo dedo 10
        self.gamepad.handle_event(pygame.event.Event(pygame.FINGERUP, {"finger_id": 10}))
        self.assertFalse(self.gamepad.is_pressed("dpad_down"))
        self.assertTrue(self.gamepad.is_pressed("kick_heavy"))

        # Levantar dedo 11
        self.gamepad.handle_event(pygame.event.Event(pygame.FINGERUP, {"finger_id": 11}))
        self.assertFalse(self.gamepad.is_pressed("kick_heavy"))

    def test_virtual_gamepad_hardware_gamepad_toggle(self):
        """Verifica auto-ocultación del mando táctil al conectar gamepad físico."""
        self.assertTrue(self.gamepad.visible)

        # Conectar gamepad físico
        self.gamepad.set_hardware_gamepad_connected(True)
        self.assertFalse(self.gamepad.visible)

        # Desconectar gamepad físico
        self.gamepad.set_hardware_gamepad_connected(False)
        self.assertTrue(self.gamepad.visible)

    def test_mobile_adapter_lifecycle(self):
        """Verifica pausa y reanudación de ciclo de vida en MobileAdapter."""
        pause_called = []
        resume_called = []
        self.adapter.on_pause_requested = lambda: pause_called.append(True)
        self.adapter.on_resume_requested = lambda: resume_called.append(True)

        self.assertFalse(self.adapter.is_paused)
        self.adapter.pause_app()
        self.assertTrue(self.adapter.is_paused)
        self.assertEqual(len(pause_called), 1)

        self.adapter.resume_app()
        self.assertFalse(self.adapter.is_paused)
        self.assertEqual(len(resume_called), 1)

    def test_mobile_adapter_back_button(self):
        """Verifica captura de botón Atrás de Android."""
        back_called = []
        self.adapter.on_back_pressed = lambda: back_called.append(True)

        ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
        consumed = self.adapter.handle_event(ev)
        self.assertTrue(consumed)
        self.assertEqual(len(back_called), 1)

    def test_buildozer_spec_and_preflight(self):
        """Verifica la configuración y chequeo previo de buildozer.spec."""
        root_dir = Path(__file__).resolve().parent
        spec_path = root_dir / "buildozer.spec"
        self.assertTrue(spec_path.is_file(), "buildozer.spec debe existir")

        spec_data = validate_spec(spec_path)
        self.assertEqual(spec_data["package.name"], "ccisystem")
        self.assertEqual(spec_data["package.domain"], "org.ccisystem.arcade")
        self.assertEqual(spec_data["orientation"], "sensorLandscape")
        self.assertIn("pygame-ce", spec_data["requirements"])
        self.assertIn("INTERNET", spec_data["android.permissions"])

        # Ejecutar pre-flight check completo
        ok = run_preflight_checks(root_dir)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
