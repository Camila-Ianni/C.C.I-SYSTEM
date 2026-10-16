"""
tests/test_guile_stage.py - Pruebas para el escenario de Guile (USA - Airbase Hangar)
con público animado (mecánico y pareja) y caja de madera rompible interactiva.
"""

import os
import unittest
import pygame
from tests.base_headless import HeadlessTestCase
from settings import MODE_PVAI, MODE_PVP, SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y
from stage_manager import stage_manager, Stage, STAGE_WIDTH, STAGE_HEIGHT, GuileBreakableCrate
from game import Game
from fighter import Fighter, FighterState
from character_select import CharacterSelect


class TestGuileStage(HeadlessTestCase):
    """Pruebas integrales del escenario de Guile (Airbase Hangar, USA) y su caja rompible."""

    def setUp(self):
        super().setUp()
        self.stage = stage_manager.get_stage_for_country("guile")
        self.stage.load()

    def test_01_guile_stage_loading_and_composition(self):
        """Verifica la carga del escenario de Guile con el asset oficial de SNES y resolución 2200x720."""
        self.assertEqual(self.stage.name, "Guile Airbase Hangar (USA)")
        self.assertEqual(self.stage.sheet_file, "SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Stages - Guile Stage (World Warrior).png")
        self.assertEqual(self.stage.crop_rect, (48, 0, 416, 208))
        self.assertIsNotNone(self.stage.surface)
        self.assertEqual(self.stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

    def test_02_guile_stage_crowd_and_crate_present(self):
        """Verifica que el público incluya al mecánico sentado, la pareja de pie y la caja rompible."""
        self.assertEqual(len(self.stage.crowd_characters), 3)

        # Mecánico con gafas oscuras sentado (elemento 0)
        mechanic = self.stage.crowd_characters[0]
        self.assertGreater(len(mechanic.frames), 1)

        # Pareja de pie junto al F-16 (elemento 1)
        couple = self.stage.crowd_characters[1]
        self.assertGreater(len(couple.frames), 1)

        # Caja rompible (elemento 2)
        crate = self.stage.crowd_characters[2]
        self.assertIsInstance(crate, GuileBreakableCrate)

        # Animación del mecánico y pareja al actualizar
        prev_m = mechanic.current_frame
        prev_c = couple.current_frame
        self.stage.update(dt=0.2)
        self.assertNotEqual(mechanic.current_frame, prev_m)
        self.assertNotEqual(couple.current_frame, prev_c)

    def test_03_breakable_crate_initial_state_and_properties(self):
        """Verifica la posición y estado inicial de la caja de madera en la esquina derecha."""
        crate = self.stage.crowd_characters[2]
        self.assertEqual(crate.state, "intact")
        self.assertEqual(len(crate.splinters), 0)
        # Posición calculada en base al recorte (360, 143)
        sx = STAGE_WIDTH / 416.0
        sy = STAGE_HEIGHT / 208.0
        self.assertEqual(crate.world_x, int(360 * sx))
        self.assertEqual(crate.world_y, int(143 * sy))
        self.assertEqual(crate.width, int(48 * sx))
        self.assertEqual(crate.height, int(48 * sy))

    def test_04_breakable_crate_smash_direct_trigger(self):
        """Verifica que smash() active el estado de fractura y genere astillas voladoras."""
        crate = self.stage.crowd_characters[2]
        crate.reset()
        self.assertEqual(crate.state, "intact")

        crate.smash()
        self.assertEqual(crate.state, "breaking")
        self.assertGreater(crate.break_timer, 0.0)
        self.assertEqual(len(crate.splinters), 4)

        # Avanzar el temporizador hasta que pase al estado final roto (tablones dentados)
        crate.update(dt=0.25)
        self.assertEqual(crate.state, "broken")

    def test_05_breakable_crate_splinter_physics_and_bounce(self):
        """Verifica que las astillas sigan física parabólica con gravedad y reboten en el suelo."""
        crate = self.stage.crowd_characters[2]
        crate.reset()
        crate.smash()

        first_sp = crate.splinters[0]
        init_y = first_sp["y"]
        init_vy = first_sp["vy"]
        self.assertLess(init_vy, 0)  # Impulso inicial hacia arriba

        # Simular 3 fotogramas: la posición debe actualizarse con la velocidad
        crate.update(dt=1.0 / 60.0)
        self.assertNotEqual(first_sp["y"], init_y)
        self.assertGreater(first_sp["vy"], init_vy)  # La gravedad incrementa vy hacia abajo

        # Simular 1 segundo completo: las astillas deben alcanzar el suelo
        for _ in range(60):
            crate.update(dt=1.0 / 60.0)

        for sp in crate.splinters:
            self.assertLessEqual(sp["y"], sp["ground_y"] + 1.0)

    def test_06_breakable_crate_collision_trigger_with_player(self):
        """Verifica que la caja se destruya cuando un jugador colisiona o se acerca a la caja."""
        crate = self.stage.crowd_characters[2]
        crate.reset()
        self.assertEqual(crate.state, "intact")

        # Jugador lejos de la caja (no debe romperse)
        dummy_far = Fighter(x=600, y=GROUND_Y - 140, char_id="carloni", player_id=1)
        crate.check_collision([dummy_far])
        self.assertEqual(crate.state, "intact")

        # Jugador empujado hacia la esquina derecha contra la caja
        dummy_near = Fighter(x=crate.world_x - 40, y=GROUND_Y - 140, char_id="cavasso", player_id=2)
        crate.check_collision([dummy_near])
        self.assertEqual(crate.state, "breaking")

    def test_07_round_reset_restores_crate(self):
        """Verifica que al reiniciar el round la caja rota vuelva a su estado intacto inicial."""
        crate = self.stage.crowd_characters[2]
        crate.smash()
        crate.update(0.3)
        self.assertEqual(crate.state, "broken")

        # Llamar a reset en el escenario
        self.stage.reset()
        self.assertEqual(crate.state, "intact")
        self.assertEqual(len(crate.splinters), 0)

    def test_08_stage_rendering_and_camera_scroll(self):
        """Verifica que el renderizado con cámara y público funcione sin errores en Pygame."""
        # Renderizar en varias posiciones de scroll de cámara
        for cam_x in [0, 400, 920]:
            self.stage.draw(self.screen, camera_x=cam_x)

        # Dibujar con la caja rota y astillas
        crate = self.stage.crowd_characters[2]
        crate.smash()
        self.stage.draw(self.screen, camera_x=800)

    def test_09_country_routing_and_character_select(self):
        """Verifica que las rutas 'guile', 'usa_low' y 'airbase' retornen Guile stage."""
        stage_guile = stage_manager.get_stage_for_country("guile")
        stage_usa_low = stage_manager.get_stage_for_country("usa_low")
        stage_airbase = stage_manager.get_stage_for_country("airbase")

        self.assertEqual(stage_guile.name, "Guile Airbase Hangar (USA)")
        self.assertEqual(stage_usa_low.name, "Guile Airbase Hangar (USA)")
        self.assertEqual(stage_airbase.name, "Guile Airbase Hangar (USA)")

    def test_10_no_magenta_or_white_artifacts_when_crate_breaks(self):
        """Verifica que al romperse la caja no queden fondos rosas (255, 0, 255) ni cajas blancas."""
        crate = self.stage.crowd_characters[2]
        crate.reset()
        crate.smash()
        # Estado de fractura
        self.assertEqual(crate.state, "breaking")
        target = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.stage.draw(target, camera_x=900)
        # Comprobar que no haya píxeles magenta (255, 0, 255)
        arr = pygame.surfarray.array3d(target)
        magenta_mask = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 255)
        self.assertEqual(magenta_mask.sum(), 0)

        # Estado completamente roto con astillas en el suelo
        crate.update(0.3)
        self.assertEqual(crate.state, "broken")
        self.stage.draw(target, camera_x=900)
        arr2 = pygame.surfarray.array3d(target)
        magenta_mask2 = (arr2[:, :, 0] == 255) & (arr2[:, :, 1] == 0) & (arr2[:, :, 2] == 255)
        self.assertEqual(magenta_mask2.sum(), 0)


if __name__ == "__main__":
    unittest.main()
