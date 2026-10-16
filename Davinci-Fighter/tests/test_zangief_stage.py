"""
tests/test_zangief_stage.py - Pruebas unitarias para el escenario de Zangief (U.S.S.R. / Industrial Furnace).
Verifica:
1. Registro y resolución de aliases para Zangief ('zangief', 'ussr', 'urss', 'russia', 'soviet').
2. Carga y ensamble de la fábrica soviética (2200x720) sin bordes externos.
3. Composición y animación de:
   - Obrero del balcón superior (balanceo de piernas suspendido de la baranda).
   - Multitud de obreros en la plataforma inferior (festejo, brindis y puños en alto).
   - Alambrado de rombos en primer plano (en frente de los luchadores en la esquina izquierda).
4. Actualización de animaciones y renderizado con desplazamiento de cámara (camera_x).
5. Integración con Game (stage_id='ussr') y CharacterSelect (país U.S.S.R.).
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

from stage_manager import StageManager, stage_manager, STAGE_WIDTH, STAGE_HEIGHT
from game import Game
from character_select import CharacterSelect, GRID_SLOTS


class TestZangiefStage(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.screen = pygame.display.set_mode((1280, 720))

    def test_stage_registration_and_aliases(self):
        """Verifica que el escenario de Zangief esté registrado bajo 'zangief', 'ussr', 'urss', 'russia'."""
        stage_zangief = stage_manager.get_stage_for_character("zangief")
        self.assertIsNotNone(stage_zangief)
        self.assertIn("Zangief", stage_zangief.name)
        self.assertIn("U.S.S.R.", stage_zangief.name)

        stage_ussr = stage_manager.get_stage_for_country("ussr")
        self.assertEqual(stage_zangief, stage_ussr)

        stage_urss = stage_manager.get_stage_for_country("urss")
        self.assertEqual(stage_zangief, stage_urss)

        stage_russia = stage_manager.get_stage_for_country("russia")
        self.assertEqual(stage_zangief, stage_russia)

        stage_soviet = stage_manager.get_stage_for_country("soviet")
        self.assertEqual(stage_zangief, stage_soviet)

    def test_stage_surface_and_crowd_composition(self):
        """Verifica que la base de la fábrica y todos los personajes animados se carguen correctamente."""
        stage = stage_manager.get_stage_for_country("ussr")
        stage.load()

        self.assertIsNotNone(stage.surface)
        self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

        # 2 elementos animados de fondo: Obrero en balcón superior y multitud de obreros
        self.assertEqual(len(stage.crowd_characters), 2)

        # 1. Obrero colgado del balcón superior
        balcony_worker = stage.crowd_characters[0]
        self.assertEqual(len(balcony_worker.frames), 2)
        self.assertEqual(balcony_worker.anim_speed, 0.08)

        # 2. Multitud de obreros en la plataforma inferior
        deck_crowd = stage.crowd_characters[1]
        self.assertEqual(len(deck_crowd.frames), 2)
        self.assertEqual(deck_crowd.anim_speed, 0.08)

        # 1 elemento en primer plano: Alambrado frontal
        self.assertEqual(len(stage.foreground_characters), 1)
        fence = stage.foreground_characters[0]
        self.assertEqual(len(fence.frames), 1)
        self.assertEqual(fence.world_x, 0)
        self.assertEqual(fence.world_y, int(141 * (720 / 216.0)))

    def test_stage_animation_update(self):
        """Verifica el ciclo de animación del obrero del balcón y de la multitud."""
        stage = stage_manager.get_stage_for_country("ussr")
        stage.load()

        balcony_worker = stage.crowd_characters[0]
        initial_frame = balcony_worker.current_frame
        stage.update(dt=1.0 / 60.0)
        self.assertGreater(balcony_worker.current_frame, initial_frame)

    def test_draw_background_and_foreground(self):
        """Verifica que el renderizado del escenario y del alambrado frontal funcione con scrolling de cámara."""
        stage = stage_manager.get_stage_for_country("ussr")
        stage.load()

        # Renderizar en el extremo izquierdo
        stage.draw(self.screen, camera_x=0)
        stage.draw_foreground(self.screen, camera_x=0)

        # Renderizar desplazado hacia la derecha
        stage.draw(self.screen, camera_x=450)
        stage.draw_foreground(self.screen, camera_x=450)

    def test_game_integration_with_ussr_stage(self):
        """Verifica que el juego principal inicialice y dibuje correctamente con el escenario de la URSS."""
        game = Game(self.screen, p1_char="carloni", p2_char="cavasso", stage_id="ussr")
        self.assertIsNotNone(game.stage)
        self.assertIn("Zangief", game.stage.name)

        # Simular ciclo de actualización y renderizado
        game.update()
        game.draw()

    def test_character_select_ussr_stage_id(self):
        """Verifica que seleccionar la casilla de la U.S.S.R. en el mapa seleccione el escenario 'ussr'."""
        cs = CharacterSelect(self.screen)
        # Buscar la casilla de la URSS en la cuadrícula
        ussr_idx = None
        for idx, slot in enumerate(GRID_SLOTS):
            if slot["country"] == "ussr":
                ussr_idx = idx
                break
        self.assertIsNotNone(ussr_idx)

        cs.p1_slot_idx = ussr_idx
        selected_stage = cs.get_selected_stage_id()
        self.assertEqual(selected_stage, "ussr")


if __name__ == "__main__":
    unittest.main()
