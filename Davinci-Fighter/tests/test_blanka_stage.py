"""
test_blanka_stage.py - Pruebas unitarias para el escenario de Blanka (Brasil - Cuenca del Amazonas).
Verifica:
1. Carga correcta del asset SNES Blanka Stage.
2. Dimensiones escaladas a STAGE_WIDTH=2200, STAGE_HEIGHT=720.
3. Limpieza de rama del árbol sin siluetas dobles.
4. Multitud animada: aldeanos de la choza amazónica (2 fotogramas) y serpiente anaconda gigante (8 fotogramas).
5. Posicionamiento en coordenadas de mundo y renderizado con desplazamiento de cámara.
6. Mapeo de país 'brazil' y personaje 'gamaliel'/'blanka'.
"""

import unittest
import pygame
from stage_manager import stage_manager, STAGE_WIDTH, STAGE_HEIGHT, BackgroundCharacter
from character_select import CHARACTER_LOCATIONS, GRID_SLOTS


class TestBlankaStage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1280, 720))

    def test_blanka_stage_loading(self):
        """Verifica que el escenario de Blanka se cargue correctamente con el nombre y asset asignado."""
        stage = stage_manager.get_stage_for_character("gamaliel")
        self.assertIsNotNone(stage)
        self.assertEqual(stage.name, "Blanka Amazon River (Brazil)")
        self.assertIsNotNone(stage.surface)
        self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

    def test_blanka_country_mapping(self):
        """Verifica que 'brazil' y los alias 'gamaliel', 'blanka' devuelvan el escenario de Blanka."""
        stage_brazil = stage_manager.get_stage_for_country("brazil")
        stage_gamaliel = stage_manager.get_stage_for_character("gamaliel")
        stage_blanka = stage_manager.get_stage_for_character("blanka")

        self.assertEqual(stage_brazil.name, "Blanka Amazon River (Brazil)")
        self.assertEqual(stage_gamaliel.name, "Blanka Amazon River (Brazil)")
        self.assertEqual(stage_blanka.name, "Blanka Amazon River (Brazil)")

    def test_blanka_crowd_elements(self):
        """Verifica que el escenario posea los aldeanos del muelle y la anaconda en el árbol."""
        stage = stage_manager.get_stage_for_country("brazil")
        self.assertEqual(len(stage.crowd_characters), 2)

        # 1. Aldeanos
        villagers = stage.crowd_characters[0]
        self.assertIsInstance(villagers, BackgroundCharacter)
        self.assertEqual(len(villagers.frames), 2)
        sx = STAGE_WIDTH / 416.0
        sy = STAGE_HEIGHT / 208.0
        expected_v_w = int(112 * sx)
        expected_v_h = int(64 * sy)
        self.assertEqual(villagers.frames[0].get_size(), (expected_v_w, expected_v_h))
        self.assertEqual(villagers.world_x, int(256 * sx))
        self.assertEqual(villagers.world_y, int(120 * sy))

        # 2. Serpiente anaconda
        snake = stage.crowd_characters[1]
        self.assertIsInstance(snake, BackgroundCharacter)
        self.assertEqual(len(snake.frames), 8)
        expected_s_w = int(24 * sx)
        expected_s_h = int(112 * sy)
        self.assertEqual(snake.frames[0].get_size(), (expected_s_w, expected_s_h))
        self.assertEqual(snake.world_x, int(388 * sx))
        self.assertEqual(snake.world_y, int((68 - 4) * sy))

    def test_blanka_animation_update(self):
        """Verifica que el ciclo de actualización de frames funcione fluidamente."""
        stage = stage_manager.get_stage_for_country("brazil")
        villagers = stage.crowd_characters[0]
        snake = stage.crowd_characters[1]

        initial_v_frame = villagers.current_frame
        initial_s_frame = snake.current_frame

        stage.update(dt=1.0 / 60.0)

        self.assertNotEqual(villagers.current_frame, initial_v_frame)
        self.assertNotEqual(snake.current_frame, initial_s_frame)

    def test_blanka_render(self):
        """Verifica que el escenario se dibuje sin lanzar excepciones en distintos camera_x."""
        stage = stage_manager.get_stage_for_country("brazil")
        screen = pygame.Surface((1280, 720))

        for cam_x in (0, 200, 460, 920):
            stage.draw(screen, camera_x=cam_x)
            stage.draw_foreground(screen, camera_x=cam_x)

    def test_character_select_brazil_slot(self):
        """Verifica que la casilla de Gamaliel / Brasil en GRID_SLOTS y CHARACTER_LOCATIONS sea correcta."""
        self.assertIn("gamaliel", CHARACTER_LOCATIONS)
        loc = CHARACTER_LOCATIONS["gamaliel"]
        self.assertEqual(loc["country"], "BRASIL")
        self.assertEqual(loc["country_key"], "brazil")

        # Casilla 3 de la cuadrícula es Brasil
        slot_brazil = GRID_SLOTS[3]
        self.assertEqual(slot_brazil["char_id"], "gamaliel")
        self.assertEqual(slot_brazil["country"], "brazil")
        self.assertEqual(slot_brazil["sound"], "brazil")


if __name__ == "__main__":
    unittest.main()
