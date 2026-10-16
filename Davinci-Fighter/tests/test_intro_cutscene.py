import os
import unittest
import pygame

from tests.base_headless import HeadlessTestCase
from intro_cutscene import IntroCutscene
from main import AppState

class TestIntroCutsceneSmoke(HeadlessTestCase):
    """Smoke tests unitarios y de integración para IntroCutscene."""

    def test_01_init_geometry_and_defaults(self):
        """Verifica inicialización y constantes de geometría 4:3."""
        cs = IntroCutscene(self.screen)
        self.assertEqual(cs.CANVAS_WIDTH, 1280)
        self.assertEqual(cs.CANVAS_HEIGHT, 720)
        self.assertEqual(cs.TARGET_WIDTH, 960)
        self.assertEqual(cs.TARGET_HEIGHT, 720)
        self.assertEqual(cs.PILLARBOX_WIDTH, 160)
        self.assertEqual(cs.current_frame_idx, 0)
        self.assertFalse(cs.finished)
        self.assertFalse(cs.skipped)
        self.assertGreater(cs.total_frames, 0)

    def test_02_init_none_screen_safe(self):
        """Verifica que instanciar sin pantalla no arroja excepciones."""
        cs = IntroCutscene(None)
        self.assertIsNone(cs.screen)
        self.assertFalse(cs.finished)

    def test_03_handle_input_space_skip(self):
        """Verifica skip inmediato con la tecla ESPACIO."""
        cs = IntroCutscene(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        res = cs.handle_input(event)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)
        self.assertTrue(cs.skipped)

    def test_04_handle_input_return_skip(self):
        """Verifica skip inmediato con la tecla ENTER."""
        cs = IntroCutscene(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        res = cs.handle_input(event)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)

    def test_05_handle_input_escape_skip(self):
        """Verifica skip inmediato con la tecla ESCAPE."""
        cs = IntroCutscene(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        res = cs.handle_input(event)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)

    def test_06_handle_input_mouse_click_skip(self):
        """Verifica skip inmediato con clic de ratón."""
        cs = IntroCutscene(self.screen)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1)
        res = cs.handle_input(event)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)

    def test_07_handle_input_ignored_keys(self):
        """Verifica que otras teclas no interrumpen la cutscene."""
        cs = IntroCutscene(self.screen)
        for key in [pygame.K_a, pygame.K_w, pygame.K_UP, pygame.K_j]:
            event = pygame.event.Event(pygame.KEYDOWN, key=key)
            res = cs.handle_input(event)
            self.assertIsNone(res)
            self.assertFalse(cs.finished)

    def test_08_callback_executed_on_skip(self):
        """Verifica que el callback on_finish se ejecuta exactamente una vez al saltar."""
        callback_called = []
        def on_finish():
            callback_called.append(True)

        cs = IntroCutscene(self.screen, on_finish=on_finish)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        cs.handle_input(event)
        self.assertEqual(len(callback_called), 1)

        # Skip repetido no vuelve a invocar callback
        cs.handle_input(event)
        self.assertEqual(len(callback_called), 1)

    def test_09_update_frame_progression_60fps(self):
        """Verifica que cada tick de 1/60s avanza exactamente 1 frame."""
        cs = IntroCutscene(self.screen)
        cs.total_frames = 100  # override for testing progression
        self.assertEqual(cs.current_frame_idx, 0)

        res = cs.update(1.0 / 60.0)
        self.assertIsNone(res)
        self.assertEqual(cs.current_frame_idx, 1)

        res = cs.update(1.0 / 60.0)
        self.assertIsNone(res)
        self.assertEqual(cs.current_frame_idx, 2)

    def test_10_update_variable_dt_accumulation(self):
        """Verifica que update acumula dt fraccional sin perder precisión."""
        cs = IntroCutscene(self.screen)
        cs.total_frames = 100
        # Medio frame: no debe avanzar
        res = cs.update(0.5 / 60.0)
        self.assertIsNone(res)
        self.assertEqual(cs.current_frame_idx, 0)
        # Segundo medio frame: debe avanzar a 1
        res = cs.update(0.5 / 60.0)
        self.assertIsNone(res)
        self.assertEqual(cs.current_frame_idx, 1)

    def test_11_natural_completion_triggers_finish(self):
        """Verifica que al alcanzar total_frames se retorna finish automáticamente."""
        callback_called = []
        def on_finish():
            callback_called.append("done")

        cs = IntroCutscene(self.screen, on_finish=on_finish)
        cs.total_frames = 5
        cs.current_frame_idx = 0

        for i in range(4):
            res = cs.update(1.0 / 60.0)
            self.assertIsNone(res)
            self.assertFalse(cs.finished)

        res = cs.update(1.0 / 60.0)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)
        self.assertFalse(cs.skipped)
        self.assertEqual(callback_called, ["done"])

    def test_12_draw_renders_4_3_with_black_pillarboxes(self):
        """Verifica que draw renderiza los pillarboxes negros de 160px a la izquierda y derecha."""
        cs = IntroCutscene(self.screen)
        # Fill screen with bright color to ensure pillarboxes overwrite it
        self.screen.fill((255, 0, 255))
        cs.draw(self.screen)

        # Pillarbox izquierdo: x = 50, y = 360 debe ser negro (0, 0, 0)
        left_pixel = self.screen.get_at((50, 360))[:3]
        self.assertEqual(left_pixel, (0, 0, 0), f"Pillarbox izquierdo no es negro: {left_pixel}")

        # Pillarbox derecho: x = 1200, y = 360 debe ser negro (0, 0, 0)
        right_pixel = self.screen.get_at((1200, 360))[:3]
        self.assertEqual(right_pixel, (0, 0, 0), f"Pillarbox derecho no es negro: {right_pixel}")

    def test_13_app_state_intro_cutscene_wiring(self):
        """Verifica que AppState incluye INTRO_CUTSCENE y su valor es 'intro_cutscene'."""
        self.assertTrue(hasattr(AppState, "INTRO_CUTSCENE"))
        self.assertEqual(AppState.INTRO_CUTSCENE, "intro_cutscene")

if __name__ == "__main__":
    unittest.main()
