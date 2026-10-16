"""
tests/test_arcade_pillarbox_43.py - Verificación del formato arcade clásico 4:3 (Pillarbox).
Asegura que:
1. Las dimensiones arcade estén configuradas (960x720) con margen de 160px a cada lado.
2. CharacterSelect renderice con franjas negras opacas laterales (0..160 y 1120..1280).
3. VSScreen renderice con franjas negras opacas laterales.
4. Game (combate en vivo) renderice el combate centrado dentro de 960x720 con franjas laterales de 160px.
"""

import unittest
import pygame
from tests.base_headless import HeadlessTestCase
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ARCADE_WIDTH, ARCADE_HEIGHT, PILLARBOX_OFFSET_X,
    MODE_PVAI
)
from character_select import CharacterSelect
from vs_screen import VSScreen
from game import Game


class TestArcadePillarbox43(HeadlessTestCase):
    """Pruebas de visualización y límites del formato arcade 4:3."""

    def test_01_constants_configuration(self):
        """Verifica que las constantes arcade 4:3 estén calculadas con exactitud."""
        self.assertEqual(ARCADE_WIDTH, 960)
        self.assertEqual(ARCADE_HEIGHT, 720)
        self.assertEqual(PILLARBOX_OFFSET_X, 160)
        self.assertEqual(SCREEN_WIDTH, 1280)
        self.assertEqual(SCREEN_HEIGHT, 720)
        self.assertEqual(PILLARBOX_OFFSET_X * 2 + ARCADE_WIDTH, SCREEN_WIDTH)

    def test_02_character_select_lateral_black_bars(self):
        """Verifica que la pantalla de selección de personajes tenga barras negras de 160px a los lados."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        cs.draw(self.screen)

        left_bar = self.screen.subsurface((0, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
        right_bar = self.screen.subsurface((PILLARBOX_OFFSET_X + ARCADE_WIDTH, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
        content = self.screen.subsurface((PILLARBOX_OFFSET_X, 0, ARCADE_WIDTH, SCREEN_HEIGHT))

        arr_l = pygame.surfarray.array3d(left_bar)
        arr_r = pygame.surfarray.array3d(right_bar)
        arr_c = pygame.surfarray.array3d(content)

        self.assertEqual(arr_l.max(), 0, "La barra lateral izquierda no es negra pura")
        self.assertEqual(arr_r.max(), 0, "La barra lateral derecha no es negra pura")
        self.assertGreater(arr_c.max(), 100, "El área central 4:3 no contiene contenido")

    def test_03_vs_screen_lateral_black_bars(self):
        """Verifica que la pantalla VS y trayectoria del avión tenga barras laterales negras."""
        vs = VSScreen(self.screen, "carloni", "cavasso")
        vs.update(0.5)
        vs.draw(self.screen)

        left_bar = self.screen.subsurface((0, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
        right_bar = self.screen.subsurface((PILLARBOX_OFFSET_X + ARCADE_WIDTH, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))

        arr_l = pygame.surfarray.array3d(left_bar)
        arr_r = pygame.surfarray.array3d(right_bar)

        self.assertEqual(arr_l.max(), 0, "La barra izquierda de VS no es negra pura")
        self.assertEqual(arr_r.max(), 0, "La barra derecha de VS no es negra pura")

    def test_04_game_fight_viewport_and_pillarbox(self):
        """Verifica que el combate se renderice en viewport 960x720 y presente franjas negras."""
        game = Game(self.screen, p1_char="carloni", p2_char="cavasso", stage_id="guile")
        self.assertEqual(game.viewport_w, ARCADE_WIDTH)
        self.assertEqual(game.viewport_h, ARCADE_HEIGHT)
        self.assertEqual(game.offset_x, PILLARBOX_OFFSET_X)

        game.update()
        game.draw()

        left_bar = self.screen.subsurface((0, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
        right_bar = self.screen.subsurface((PILLARBOX_OFFSET_X + ARCADE_WIDTH, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
        content = self.screen.subsurface((PILLARBOX_OFFSET_X, 0, ARCADE_WIDTH, SCREEN_HEIGHT))

        arr_l = pygame.surfarray.array3d(left_bar)
        arr_r = pygame.surfarray.array3d(right_bar)
        arr_c = pygame.surfarray.array3d(content)

        self.assertEqual(arr_l.max(), 0, "La barra izquierda del combate no es negra pura")
        self.assertEqual(arr_r.max(), 0, "La barra derecha del combate no es negra pura")
        self.assertGreater(arr_c.max(), 100, "El área central de combate no contiene contenido")


if __name__ == "__main__":
    unittest.main()
