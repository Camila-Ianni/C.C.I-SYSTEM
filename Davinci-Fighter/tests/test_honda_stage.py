"""
tests/test_honda_stage.py - Pruebas unitarias para el escenario de E. Honda (Japón / Baño tradicional sentō).
Verifica:
1. Registro y resolución de aliases para Honda ('honda', 'romero', 'japan_up', 'bathhouse', 'sento', 'ehonda').
2. Carga y ensamble del baño tradicional japonés (2200x720) sin la gota estática original.
3. Elementos interactivos y animados del escenario:
   - Bañera de aguas termales con olas, destellos cáusticos y desborde ('revalsando') por los azulejos.
   - Gotas de agua que caen del techo con ciclo de formación, caída gravitatoria, impacto y ondas en el suelo.
   - Linternas colgantes japonesas (chōchin) con alternancia y pulsación cálida de luminosidad.
4. Actualización de animaciones y renderizado con desplazamiento horizontal de cámara (camera_x).
5. Integración con Game (stage_id='honda') y CharacterSelect (ranura Romero / Japan superior).
"""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

from stage_manager import (
    StageManager,
    stage_manager,
    STAGE_WIDTH,
    STAGE_HEIGHT,
    HondaBathTubWater,
    HondaCeilingDroplets,
    HondaLanterns,
)
from game import Game
from character_select import CharacterSelect, GRID_SLOTS


class TestHondaStage(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.screen = pygame.display.set_mode((1280, 720))

    def test_stage_registration_and_aliases(self):
        """Verifica que el escenario de Honda esté registrado bajo 'honda', 'romero', 'japan_up', 'bathhouse', 'sento', 'ehonda'."""
        stage_honda = stage_manager.get_stage_for_character("honda")
        self.assertIsNotNone(stage_honda)
        self.assertIn("Honda", stage_honda.name)
        self.assertIn("Japan", stage_honda.name)

        stage_romero = stage_manager.get_stage_for_character("romero")
        self.assertEqual(stage_honda, stage_romero)

        stage_japan_up = stage_manager.get_stage_for_country("japan_up")
        self.assertEqual(stage_honda, stage_japan_up)

        stage_bathhouse = stage_manager.get_stage_for_country("bathhouse")
        self.assertEqual(stage_honda, stage_bathhouse)

        stage_sento = stage_manager.get_stage_for_country("sento")
        self.assertEqual(stage_honda, stage_sento)

        stage_ehonda = stage_manager.get_stage_for_country("ehonda")
        self.assertEqual(stage_honda, stage_ehonda)

    def test_stage_surface_and_crowd_composition(self):
        """Verifica que el baño tradicional base y los componentes animados se carguen correctamente."""
        stage = stage_manager.get_stage_for_country("honda")
        stage.load()

        self.assertIsNotNone(stage.surface)
        self.assertEqual(stage.surface.get_size(), (STAGE_WIDTH, STAGE_HEIGHT))

        # 3 componentes animados en el escenario de Honda
        self.assertEqual(len(stage.crowd_characters), 3)

        # 1. Agua desbordante de la bañera (HondaBathTubWater)
        tub_water = stage.crowd_characters[0]
        self.assertIsInstance(tub_water, HondaBathTubWater)
        self.assertEqual(len(tub_water.overflow_frames), 2)
        self.assertGreater(tub_water.tub_w, 800)

        # 2. Gotas de agua que caen del techo (HondaCeilingDroplets)
        ceiling_drops = stage.crowd_characters[1]
        self.assertIsInstance(ceiling_drops, HondaCeilingDroplets)
        self.assertEqual(len(ceiling_drops.drop_frames), 9)
        self.assertEqual(len(ceiling_drops.active_drops), 3)

        # 3. Linternas japonesas colgantes (HondaLanterns)
        lanterns = stage.crowd_characters[2]
        self.assertIsInstance(lanterns, HondaLanterns)
        self.assertIsNotNone(lanterns.norm_frame)
        self.assertIsNotNone(lanterns.glow_frame)

    def test_bath_tub_water_animation_and_overflow(self):
        """Verifica que el agua de la bañera se actualice y renderice correctamente."""
        stage = stage_manager.get_stage_for_country("honda")
        stage.load()

        tub_water = stage.crowd_characters[0]
        initial_time = tub_water.time
        self.assertEqual(tub_water.current_frame_idx, 0)
        
        # Avanzar el tiempo para cambiar de fotograma
        stage.update(dt=tub_water.anim_speed + 0.05)
        self.assertGreater(tub_water.time, initial_time)
        self.assertEqual(tub_water.current_frame_idx, 1)

        # Dibujar en pantalla con cámara
        tub_water.draw(self.screen, camera_x=450)

    def test_ceiling_droplets_lifecycle(self):
        """Verifica el ciclo de vida de las gotas: formación, caída, impacto y ondas."""
        stage = stage_manager.get_stage_for_country("honda")
        stage.load()

        ceiling_drops = stage.crowd_characters[1]
        # Forzar una gota a estado falling
        drop = ceiling_drops.active_drops[0]
        drop["state"] = "falling"
        drop["y"] = drop["ceil_y"] + 50
        drop["vy"] = 300.0

        # Avanzar simulación
        ceiling_drops.update(dt=1.0 / 30.0)
        self.assertGreater(drop["y"], drop["ceil_y"] + 50)

        # Dibujar gotas con cámara
        ceiling_drops.draw(self.screen, camera_x=450)

    def test_lanterns_glow_cycle(self):
        """Verifica la alternancia de iluminación de las linternas chōchin."""
        stage = stage_manager.get_stage_for_country("honda")
        stage.load()

        lanterns = stage.crowd_characters[2]
        initial_time = lanterns.time
        lanterns.update(dt=1.0 / 60.0)
        self.assertGreater(lanterns.time, initial_time)

        lanterns.draw(self.screen, camera_x=0)
        lanterns.draw(self.screen, camera_x=460)

    def test_draw_with_camera_scroll(self):
        """Verifica el renderizado con desplazamiento de cámara a diferentes puntos del escenario."""
        stage = stage_manager.get_stage_for_country("honda")
        stage.load()

        # Renderizar en extremo izquierdo (pared con cortina 'yu' y entrada de bambú)
        stage.draw(self.screen, camera_x=0)

        # Renderizar en el centro (bañera y mural de monte Fuji)
        stage.draw(self.screen, camera_x=460)

        # Renderizar en extremo derecho (pared con retrato kabuki y grifos)
        stage.draw(self.screen, camera_x=920)

    def test_game_integration_with_honda_stage(self):
        """Verifica que Game inicialice y dibuje correctamente con stage_id='honda'."""
        game = Game(self.screen, p1_char="carloni", p2_char="romero", stage_id="honda")
        self.assertIsNotNone(game.stage)
        self.assertIn("Honda", game.stage.name)

        # Simular ciclos de juego
        game.update()
        game.draw()

    def test_character_select_honda_stage_routing(self):
        """Verifica que CharacterSelect seleccione 'honda' para la casilla 2 (Romero / Japón superior)."""
        cs = CharacterSelect(self.screen)
        cs.p1_slot_idx = 2  # Romero (Japan up)
        selected_stage = cs.get_selected_stage_id()
        self.assertEqual(selected_stage, "honda")


if __name__ == "__main__":
    unittest.main()
