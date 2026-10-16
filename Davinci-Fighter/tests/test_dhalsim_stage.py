"""
tests/test_dhalsim_stage.py - Pruebas unitarias para el escenario de Dhalsim (India) en Da Vinci Fighters.
Verifica:
1. Carga fiel del escenario de Dhalsim a partir del sprite sheet oficial de SNES.
2. Composición y animación de los 4 elefantes (2 interiores y 2 exteriores) y las vasijas ceremoniales.
3. Desplazamiento horizontal de cámara y renderizado en pantalla 1280x720.
4. Integración con StageManager, Game y CharacterSelect para el país de India.
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

from stage_manager import StageManager, stage_manager, STAGE_WIDTH, STAGE_HEIGHT
from game import Game
from character_select import CharacterSelect


class TestDhalsimStage(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.screen = pygame.display.set_mode((1280, 720))

    def test_stage_registration_and_aliases(self):
        """Verifica que el escenario de Dhalsim esté registrado bajo 'dhalsim' e 'india'."""
        stage_dhalsim = stage_manager.get_stage_for_character("dhalsim")
        self.assertIsNotNone(stage_dhalsim)
        self.assertIn("Dhalsim", stage_dhalsim.name)
        self.assertIn("India", stage_dhalsim.name)

        stage_india = stage_manager.get_stage_for_country("india")
        self.assertEqual(stage_dhalsim, stage_india)

        stage_ind = stage_manager.get_stage_for_country("ind")
        self.assertEqual(stage_dhalsim, stage_ind)

    def test_dhalsim_stage_surface_and_crowd_composition(self):
        """Verifica que la base del palacio y los 4 elefantes + 2 urnas se carguen correctamente."""
        stage = stage_manager.get_stage_for_country("india")
        stage.load()

        self.assertIsNotNone(stage.surface)
        self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

        # 6 elefantes (2 interiores, 2 medios, 2 exteriores) + 2 vasijas = 8
        self.assertEqual(len(stage.crowd_characters), 8)

        # Elefantes interiores
        ele_in_left = stage.crowd_characters[0]
        ele_in_right = stage.crowd_characters[1]
        self.assertGreater(len(ele_in_left.frames), 0)
        self.assertEqual(ele_in_left.anim_speed, 0.20)
        self.assertGreater(len(ele_in_right.frames), 0)

        # Elefantes medios
        ele_mid_left = stage.crowd_characters[2]
        ele_mid_right = stage.crowd_characters[3]
        self.assertGreater(len(ele_mid_left.frames), 0)
        self.assertGreater(len(ele_mid_right.frames), 0)

        # Elefantes exteriores
        ele_out_left = stage.crowd_characters[4]
        ele_out_right = stage.crowd_characters[5]
        self.assertGreater(len(ele_out_left.frames), 0)
        self.assertGreater(len(ele_out_right.frames), 0)

        # Vasijas ceremoniales
        urn_gold = stage.crowd_characters[6]
        urn_clay = stage.crowd_characters[7]
        self.assertEqual(urn_gold.anim_speed, 0.0)
        self.assertEqual(urn_clay.anim_speed, 0.0)

    def test_elephant_animation_cycle(self):
        """Verifica que los elefantes avancen sus fotogramas y se mantengan en ciclo rítmico."""
        stage = stage_manager.get_stage_for_country("india")
        stage.load()

        ele_in_left = stage.crowd_characters[0]
        initial_frame = ele_in_left.current_frame

        # Actualizar 10 veces
        for _ in range(10):
            stage.update(dt=1.0 / 60.0)

        self.assertNotEqual(ele_in_left.current_frame, initial_frame)

    def test_rendering_across_camera_angles(self):
        """Verifica que el renderizado no lance excepciones en los extremos y centro de la cámara."""
        stage = stage_manager.get_stage_for_country("india")
        stage.load()

        for cam_x in [0, 460, 920]:
            self.screen.fill((0, 0, 0))
            stage.draw(self.screen, camera_x=cam_x)
            # Verificar que el búfer contenga píxeles no negros
            arr = pygame.surfarray.array2d(self.screen)
            self.assertTrue((arr != 0).any())

    def test_six_elephants_composition_and_visibility(self):
        """Verifica que se encuentren los 6 elefantes (3 a la izquierda y 3 a la derecha)."""
        stage = stage_manager.get_stage_for_country("india")
        stage.load()

        # 1. Cámara izquierda (cam_x = 0): los 3 elefantes del ala izquierda (exterior, medio, interior)
        self.screen.fill((0, 0, 0))
        stage.draw(self.screen, camera_x=0)
        # Comprobar que en las regiones x in [50, 300], [350, 600] y [650, 850] existan los cascos dorados de los 3 elefantes
        has_left_outer = any(self.screen.get_at((x, y))[0] > 180 and self.screen.get_at((x, y))[1] > 140 and self.screen.get_at((x, y))[2] < 50 for x in range(50, 300) for y in range(150, 450))
        has_left_mid = any(self.screen.get_at((x, y))[0] > 180 and self.screen.get_at((x, y))[1] > 140 and self.screen.get_at((x, y))[2] < 50 for x in range(350, 600) for y in range(150, 450))
        has_left_inner = any(self.screen.get_at((x, y))[0] > 180 and self.screen.get_at((x, y))[1] > 140 and self.screen.get_at((x, y))[2] < 50 for x in range(650, 850) for y in range(150, 450))
        self.assertTrue(has_left_outer, "Debe verse el elefante exterior izquierdo")
        self.assertTrue(has_left_mid, "Debe verse el elefante medio izquierdo")
        self.assertTrue(has_left_inner, "Debe verse el elefante interior izquierdo")

        # 2. Cámara derecha (cam_x = 920): los 3 elefantes del ala derecha (interior, medio, exterior)
        self.screen.fill((0, 0, 0))
        stage.draw(self.screen, camera_x=920)
        has_right_inner = any(self.screen.get_at((x, y))[0] > 180 and self.screen.get_at((x, y))[1] > 140 and self.screen.get_at((x, y))[2] < 50 for x in range(400, 600) for y in range(150, 450))
        has_right_mid = any(self.screen.get_at((x, y))[0] > 180 and self.screen.get_at((x, y))[1] > 140 and self.screen.get_at((x, y))[2] < 50 for x in range(650, 900) for y in range(150, 450))
        has_right_outer = any(self.screen.get_at((x, y))[0] > 180 and self.screen.get_at((x, y))[1] > 140 and self.screen.get_at((x, y))[2] < 50 for x in range(950, 1250) for y in range(150, 450))
        self.assertTrue(has_right_inner, "Debe verse el elefante interior derecho")
        self.assertTrue(has_right_mid, "Debe verse el elefante medio derecho")
        self.assertTrue(has_right_outer, "Debe verse el elefante exterior derecho")

    def test_game_initialization_with_india_stage(self):
        """Verifica que Game(..., stage_id='india') inicialice con el escenario de Dhalsim."""
        game = Game(self.screen, p1_char="carloni", p2_char="cavasso", stage_id="india")
        self.assertIn("Dhalsim", game.stage.name)
        self.assertIn("India", game.stage.name)

    def test_character_select_resolves_india_stage(self):
        """Verifica que CharacterSelect resuelva stage_id='india' al seleccionar dicho país."""
        cs = CharacterSelect(self.screen)
        # Asignar slot de India
        slot_india = cs.country_to_slot.get("india")
        self.assertIsNotNone(slot_india)
        cs.p1_slot_idx = slot_india
        self.assertEqual(cs.get_p1_country(), "india")
        self.assertEqual(cs.get_selected_stage_id(), "india")


if __name__ == "__main__":
    unittest.main()
