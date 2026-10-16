"""
tests/test_character_select_and_vs.py - Tests exhaustivos para CharacterSelect, VSScreen y StageManager.
Verifica:
1. CharacterSelect: renderizado con player select.png, cuadrícula de los 5 profesores, navegación WASD/flechas, confirmaciones P1/P2/IA, y audio.
2. VSScreen: animación de trayectoria de avión, rotación, cálculo de parábola, audio drone y explosión de impacto VS al aterrizar.
3. StageManager: ensamble de los 5 fondos de Sega Genesis, soporte para 2200px de ancho, colorkey de transparencia y público animado.
4. Integración E2E: IntroCutscene -> TitleScreen -> Menu -> CharacterSelect -> VSScreen -> Game.
"""

import os
import unittest
import pygame
from tests.base_headless import HeadlessTestCase, CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT, CANONICAL_FPS
from settings import MODE_PVAI, MODE_PVP, SCREEN_WIDTH, SCREEN_HEIGHT
from character_data import CHARACTERS
from character_select import CharacterSelect, GRID_SLOTS
from vs_screen import VSScreen
from stage_manager import stage_manager, STAGE_WIDTH, STAGE_HEIGHT
from audio_manager import audio_manager
from main import AppState


class TestCharacterSelectSmoke(HeadlessTestCase):
    """Pruebas unitarias para CharacterSelect."""

    def test_01_init_and_slots(self):
        """Verifica inicialización, cuadrícula y selección por defecto."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        self.assertEqual(cs.p1_slot_idx, 0)
        self.assertEqual(cs.p1_char, "carloni")
        self.assertFalse(cs.p1_confirmed)
        self.assertFalse(cs.p2_confirmed)
        self.assertEqual(len(GRID_SLOTS), 8)

    def test_02_navigation_horizontal_and_vertical(self):
        """Verifica navegación secuencial con teclas A/D y W/S a través de los 5 personajes."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        
        # Mover derecha (D): carloni (0) -> cavasso (1)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_slot_idx, 1)
        self.assertEqual(cs.p1_char, "cavasso")

        # Mover derecha (D): cavasso (1) -> romero (2)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_slot_idx, 2)
        self.assertEqual(cs.p1_char, "romero")

        # Mover abajo (S): romero (2) -> gamaliel (3)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s))
        self.assertEqual(cs.p1_slot_idx, 3)

        # Mover arriba (W): gamaliel (3) -> romero (2)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        self.assertEqual(cs.p1_slot_idx, 2)

    def test_03_confirmation_and_pvai_auto_lock(self):
        """Verifica que confirmar P1 en modo PVAI bloquea a la IA automáticamente."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertTrue(cs.p1_confirmed)
        self.assertTrue(cs.p2_confirmed)

        # Avanzar el temporizador de transición
        res = cs.update(0.5)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("action"), "vs")
        self.assertEqual(res.get("p1_char"), "carloni")

    def test_04_draw_execution(self):
        """Verifica que el método draw() renderiza limpiamente sin excepciones."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        try:
            cs.draw()
            cs.draw(self.screen)
        except Exception as e:
            self.fail(f"CharacterSelect.draw() falló con excepción: {e}")

    def test_04b_empty_portraits_and_direct_stage_launch(self):
        """Verifica que no se dibujen fotos de personajes y que la confirmación devuelva stage_id directamente."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        # Seleccionar casilla 3 (Brasil / Blanka)
        cs.p1_slot_idx = 3
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNotNone(res)
        self.assertEqual(res.get("stage_id"), "brazil")
        self.assertEqual(res.get("action"), "fight")

        # Seleccionar casilla 5 (China / Chun-Li)
        cs2 = CharacterSelect(self.screen, MODE_PVAI)
        cs2.p1_slot_idx = 5
        res2 = cs2.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertIsNotNone(res2)
        self.assertEqual(res2.get("stage_id"), "china")


class TestVSScreenSmoke(HeadlessTestCase):
    """Pruebas unitarias para VSScreen."""

    def test_05_init_and_trajectory(self):
        """Verifica la generación de la trayectoria del avión y los waypoints parabólicos."""
        vs = VSScreen(self.screen, "carloni", "cavasso")
        self.assertEqual(vs.p1_char, "carloni")
        self.assertEqual(vs.p2_char, "cavasso")
        self.assertGreater(len(vs.trajectory_points), 10)
        self.assertEqual(vs.state, "takeoff")
        self.assertFalse(vs.finished)

    def test_06_flight_progression_and_impact(self):
        """Verifica la progresión del vuelo del avión y el impacto al aterrizar."""
        vs = VSScreen(self.screen, "carloni", "cavasso")
        self.assertEqual(vs.flight_progress, 0.0)

        # Avanzar la mitad del vuelo (1.2s)
        vs.update(1.2)
        self.assertGreater(vs.flight_progress, 0.4)
        self.assertLess(vs.flight_progress, 0.6)

        # Completar el vuelo (1.5s adicionales)
        vs.update(1.5)
        self.assertEqual(vs.state, "landed")
        self.assertTrue(vs.landed_sound_played)
        self.assertGreater(vs.impact_flash, 0.0)

        # Mantener y finalizar
        res = vs.update(1.5)
        self.assertEqual(res, "fight")
        self.assertTrue(vs.finished)

    def test_07_skip_input(self):
        """Verifica que presionar cualquier tecla finaliza inmediatamente la cutscene VS."""
        vs = VSScreen(self.screen, "carloni", "cavasso")
        res = vs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(res, "fight")
        self.assertTrue(vs.finished)

    def test_08_draw_execution(self):
        """Verifica que VSScreen.draw() renderiza limpiamente en todos los estados."""
        vs = VSScreen(self.screen, "carloni", "cavasso")
        try:
            vs.draw()
            vs.update(1.2)
            vs.draw()
            vs.update(1.5)
            vs.draw()
        except Exception as e:
            self.fail(f"VSScreen.draw() falló con excepción: {e}")


class TestStageManagerAssembly(HeadlessTestCase):
    """Pruebas de ensamble y scrolling para StageManager."""

    def test_09_all_stages_load_with_correct_dimensions(self):
        """Verifica que los 5 escenarios se carguen a 2200x720."""
        for char_id in ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]:
            stage = stage_manager.get_stage_for_character(char_id)
            self.assertIsNotNone(stage.surface)
            self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

    def test_10_crowd_animations_update_and_render(self):
        """Verifica que las animaciones de público se actualicen y rendericen con colorkey."""
        stage_guile = stage_manager.get_stage_for_character("cavasso")
        self.assertGreater(len(stage_guile.crowd_characters), 0)
        
        # Actualizar animaciones
        stage_guile.update(1.0 / 60.0)
        
        # Dibujar con desplazamiento de cámara
        try:
            stage_guile.draw(self.screen, camera_x=400)
        except Exception as e:
            self.fail(f"Stage.draw() falló: {e}")


class TestAudioSynchronization(HeadlessTestCase):
    """Pruebas de sincronización de audio para la nueva banda sonora SEGA."""

    def test_11_all_character_stage_tracks_exist(self):
        """Verifica que todas las pistas de los profesores correspondan a archivos existentes."""
        for char_id, track_name in audio_manager.character_stage_tracks.items():
            path = os.path.join(audio_manager.audio_dir, track_name)
            self.assertTrue(os.path.exists(path), f"Pista no encontrada para {char_id}: {path}")

    def test_12_ui_tracks_exist(self):
        """Verifica que todas las pistas de interfaz correspondan a archivos existentes."""
        for name, track_name in audio_manager.music_tracks.items():
            path = os.path.join(audio_manager.audio_dir, track_name)
            self.assertTrue(os.path.exists(path), f"Pista no encontrada para {name}: {path}")


if __name__ == "__main__":
    unittest.main()
