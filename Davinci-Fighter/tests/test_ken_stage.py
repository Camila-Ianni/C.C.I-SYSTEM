"""
tests/test_ken_stage.py - Pruebas unitarias para el escenario de Ken (USA / Battle Harbor).
Verifica:
1. Registro y resolución de aliases para Ken ('ken', 'usa_ken', 'harbor', 'port').
2. Carga y ensamble del muelle y puerto americano (2200x720) sin bordes externos.
3. Composición y animación de:
   - Pasajeros de la cubierta superior (hombre en bata brindando y hombre apoyado en baranda).
   - Pasajeros de la cubierta inferior (hombre calvo alzando el puño, hombre de gabardina, mujer saludando, hombre de suéter azul y hombre de abrigo y sombrero azul).
4. Actualización de animaciones y renderizado con desplazamiento horizontal de cámara (camera_x).
5. Integración con Game (stage_id='ken') y CharacterSelect (8 casillas y países originales de SF2).
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

from stage_manager import StageManager, stage_manager, STAGE_WIDTH, STAGE_HEIGHT
from game import Game
from character_select import CharacterSelect, GRID_SLOTS


class TestKenStage(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.screen = pygame.display.set_mode((1280, 720))

    def test_stage_registration_and_aliases(self):
        """Verifica que el escenario de Ken esté registrado bajo 'ken', 'usa_ken', 'harbor', 'port'."""
        stage_ken = stage_manager.get_stage_for_character("ken")
        self.assertIsNotNone(stage_ken)
        self.assertIn("Ken", stage_ken.name)
        self.assertIn("USA", stage_ken.name)

        stage_usa_ken = stage_manager.get_stage_for_country("usa_ken")
        self.assertEqual(stage_ken, stage_usa_ken)

        stage_harbor = stage_manager.get_stage_for_country("harbor")
        self.assertEqual(stage_ken, stage_harbor)

        stage_port = stage_manager.get_stage_for_country("port")
        self.assertEqual(stage_ken, stage_port)

    def test_stage_surface_and_crowd_composition(self):
        """Verifica que el puerto base y los pasajeros animados se carguen correctamente."""
        stage = stage_manager.get_stage_for_country("ken")
        stage.load()

        self.assertIsNotNone(stage.surface)
        self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

        # 2 grupos de pasajeros animados en el barco
        self.assertEqual(len(stage.crowd_characters), 2)

        # 1. Pasajeros de la cubierta superior (2 fotogramas)
        upper = stage.crowd_characters[0]
        self.assertEqual(len(upper.frames), 2)
        self.assertEqual(upper.anim_speed, 0.08)

        # 2. Pasajeros de la cubierta inferior (2 fotogramas)
        lower = stage.crowd_characters[1]
        self.assertEqual(len(lower.frames), 2)
        self.assertEqual(lower.anim_speed, 0.08)

    def test_stage_animation_update(self):
        """Verifica el ciclo de animación de los pasajeros del barco."""
        stage = stage_manager.get_stage_for_country("ken")
        stage.load()

        upper = stage.crowd_characters[0]
        initial_frame = upper.current_frame
        stage.update(dt=1.0 / 60.0)
        self.assertGreater(upper.current_frame, initial_frame)

    def test_draw_with_camera_scroll(self):
        """Verifica el renderizado con desplazamiento de cámara a la izquierda y derecha."""
        stage = stage_manager.get_stage_for_country("ken")
        stage.load()

        # Renderizar en el extremo izquierdo
        stage.draw(self.screen, camera_x=0)

        # Renderizar desplazado hacia la derecha
        stage.draw(self.screen, camera_x=450)

    def test_game_integration_with_ken_stage(self):
        """Verifica que el juego principal inicialice y dibuje correctamente con el escenario de Ken."""
        game = Game(self.screen, p1_char="carloni", p2_char="cavasso", stage_id="ken")
        self.assertIsNotNone(game.stage)
        self.assertIn("Ken", game.stage.name)

        # Simular ciclo de actualización y renderizado
        game.update()
        game.draw()

    def test_character_select_ken_stage_and_countries_distribution(self):
        """Verifica la distribución de los 8 países originales de SF2 y la selección del escenario de Ken."""
        cs = CharacterSelect(self.screen)

        # Verificar que la casilla 1 (USA de arriba) devuelva 'ken' y la casilla 4 (USA de abajo) devuelva 'guile'
        cs.p1_slot_idx = 1
        self.assertEqual(cs.get_selected_stage_id(), "ken")
        cs.p1_slot_idx = 4
        self.assertEqual(cs.get_selected_stage_id(), "guile")

        # Verificar que la cuadrícula 2x4 contenga exactamente:
        # 2 Japón, 2 USA, 1 Brasil, 1 China, 1 URSS, 1 India
        country_counts = {}
        for slot in GRID_SLOTS:
            c = slot["country"]
            country_counts[c] = country_counts.get(c, 0) + 1

        self.assertEqual(country_counts.get("japan"), 2)
        self.assertEqual(country_counts.get("usa"), 2)
        self.assertEqual(country_counts.get("brazil"), 1)
        self.assertEqual(country_counts.get("china"), 1)
        self.assertEqual(country_counts.get("ussr"), 1)
        self.assertEqual(country_counts.get("india"), 1)


if __name__ == "__main__":
    unittest.main()
