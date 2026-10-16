"""
tests/test_chunli_stage.py - Pruebas unitarias para el escenario de Chun-Li (China) en Da Vinci Fighters.
Verifica:
1. Carga fiel del escenario de Chun-Li a partir del sprite sheet oficial de SNES.
2. Composición y animación de:
   - Puesto de carnicería con público animado, carnicero y gallinas (en manos y enjaulada).
   - Cilindro giratorio de la peluquería (Barber pole).
   - Muchacha lavando ropa en la tina bajo el caño de agua.
   - Tráfico continuo de ciclistas (mujer con pantalón rojo y hombre con gafas oscuras).
3. Desplazamiento horizontal de cámara y renderizado en pantalla 1280x720.
4. Integración con StageManager, Game y CharacterSelect para el país de China.
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

from stage_manager import StageManager, stage_manager, STAGE_WIDTH, STAGE_HEIGHT, CyclistCharacter
from game import Game
from character_select import CharacterSelect


class TestChunLiStage(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.screen = pygame.display.set_mode((1280, 720))

    def test_stage_registration_and_aliases(self):
        """Verifica que el escenario de Chun-Li esté registrado bajo 'chunli', 'chun_li' y 'china'."""
        stage_chunli = stage_manager.get_stage_for_character("chunli")
        self.assertIsNotNone(stage_chunli)
        self.assertIn("Chun-Li", stage_chunli.name)
        self.assertIn("China", stage_chunli.name)

        stage_china = stage_manager.get_stage_for_country("china")
        self.assertEqual(stage_chunli, stage_china)

        stage_chn = stage_manager.get_stage_for_country("chn")
        self.assertEqual(stage_chunli, stage_chn)

    def test_stage_surface_and_crowd_composition(self):
        """Verifica que la calle de mercado y todos los elementos animados se carguen correctamente."""
        stage = stage_manager.get_stage_for_country("china")
        stage.load()

        self.assertIsNotNone(stage.surface)
        self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

        # 4 elementos: Carnicería/Gallinas, Barber Pole, Lavandera y Ciclistas
        self.assertEqual(len(stage.crowd_characters), 4)

        # 1. Puesto de carnicería y gallinas
        stall = stage.crowd_characters[0]
        self.assertEqual(len(stall.frames), 2)
        self.assertEqual(stall.anim_speed, 0.08)

        # 2. Barber Pole (3 fotogramas de giro)
        pole = stage.crowd_characters[1]
        self.assertEqual(len(pole.frames), 3)
        self.assertEqual(pole.anim_speed, 0.15)

        # 3. Muchacha lavando ropa en la tina (2 fotogramas)
        girl = stage.crowd_characters[2]
        self.assertEqual(len(girl.frames), 2)
        self.assertEqual(girl.anim_speed, 0.10)

        # 4. Tráfico de ciclistas
        cyclist = stage.crowd_characters[3]
        self.assertIsInstance(cyclist, CyclistCharacter)
        self.assertEqual(len(cyclist.female_frames), 3)
        self.assertEqual(len(cyclist.male_frames), 3)

    def test_cyclist_movement_and_pedal_cycle(self):
        """Verifica que el ciclista avance horizontalmente y actualice sus fotogramas de pedaleo."""
        stage = stage_manager.get_stage_for_country("china")
        stage.load()

        cyclist = stage.crowd_characters[3]
        initial_x = cyclist.world_x
        initial_frame = cyclist.frame_index

        for _ in range(30):
            stage.update(dt=1.0 / 60.0)

        self.assertGreater(cyclist.world_x, initial_x)
        self.assertNotEqual(cyclist.frame_index, initial_frame)

    def test_rendering_across_camera_angles(self):
        """Verifica que el renderizado se ejecute sin errores en los ángulos 0, 460 y 920 de cámara."""
        stage = stage_manager.get_stage_for_country("china")
        stage.load()

        for cam_x in [0, 460, 920]:
            self.screen.fill((0, 0, 0))
            stage.draw(self.screen, camera_x=cam_x)
            arr = pygame.surfarray.array2d(self.screen)
            self.assertTrue((arr != 0).any())

    def test_game_initialization_with_china_stage(self):
        """Verifica que Game(..., stage_id='china') inicialice con el escenario de Chun-Li."""
        game = Game(self.screen, p1_char="carloni", p2_char="cavasso", stage_id="china")
        self.assertIn("Chun-Li", game.stage.name)
        self.assertIn("China", game.stage.name)

    def test_character_select_resolves_china_stage(self):
        """Verifica que CharacterSelect resuelva stage_id='china' al seleccionar dicho país."""
        cs = CharacterSelect(self.screen)
        slot_china = cs.country_to_slot.get("china")
        self.assertIsNotNone(slot_china)
        cs.p1_slot_idx = slot_china
        self.assertEqual(cs.get_p1_country(), "china")
        self.assertEqual(cs.get_selected_stage_id(), "china")


if __name__ == "__main__":
    unittest.main()
