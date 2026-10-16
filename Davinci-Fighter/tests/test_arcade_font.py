"""
test_arcade_font.py - Unit tests for the authentic Street Fighter II Large Colour arcade font renderer.
"""

import unittest
import pygame
from arcade_font import ArcadeFont, get_arcade_font
from hud import HUD
from game import Game, GameState
from settings import MODE_PVP, MODE_PVAI

class TestArcadeFont(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1), pygame.HIDDEN)

    def test_arcade_font_singleton(self):
        af1 = get_arcade_font()
        af2 = get_arcade_font()
        self.assertIs(af1, af2)
        self.assertTrue(af1.loaded)
        self.assertIsNotNone(af1.sheet)
        self.assertGreater(len(af1.glyphs), 50)

    def test_arcade_font_render_scores(self):
        af = get_arcade_font()
        surf = af.render("000000", scale=0.6)
        self.assertIsInstance(surf, pygame.Surface)
        self.assertGreater(surf.get_width(), 0)
        self.assertGreater(surf.get_height(), 0)

    def test_arcade_font_render_messages(self):
        af = get_arcade_font()
        messages = [
            "START !",
            "BONUS STAGE",
            "YOU WIN",
            "YOU LOSE",
            "ROUND 1",
            "FIGHT!",
            "K.O.",
            "PERFECT",
            "DRAW",
            "TIME OVER"
        ]
        for msg in messages:
            surf = af.render(msg, scale=1.0)
            self.assertIsInstance(surf, pygame.Surface)
            self.assertGreater(surf.get_width(), 0)
            self.assertGreater(surf.get_height(), 0)

    def test_arcade_font_render_to(self):
        af = get_arcade_font()
        target = pygame.Surface((400, 200), pygame.SRCALPHA)
        rect = af.render_to(target, (200, 100), "YOU WIN", scale=1.2, align="center")
        self.assertEqual(rect.centerx, 200)
        self.assertEqual(rect.centery, 100)

    def test_arcade_font_taunt_quotes(self):
        af = get_arcade_font()
        quotes = [
            "DATABASE MASTER - DROP TABLE ENEMY;",
            "SYSTEM BREACH - ACCESS GRANTED",
            "REUNIÓN DE 10 AM - AGENDA COMPLETA",
            "OBJECT ORIENTED SYSTEM INHERITED",
            "EL CLIENTE CAMBIÓ LOS REQUISITOS"
        ]
        for q in quotes:
            w, h = af.size(q, scale=0.8)
            self.assertGreater(w, 50)
            self.assertGreater(h, 10)
            surf = af.render(q, scale=0.8)
            self.assertIsNotNone(surf)

    def test_hud_draw_with_arcade_font(self):
        hud = HUD()
        screen = pygame.Surface((1280, 720), pygame.SRCALPHA)
        game = Game(screen, p1_char="carloni", p2_char="cavasso", game_mode=MODE_PVAI)
        hud.draw(screen, game.player1, game.player2, timer_seconds=95, p1_wins=1, p2_wins=0, match_banner=("ROUND 1", "START !"))
        self.assertEqual(hud.p1_score, 12000)
        self.assertEqual(hud.top_score, 50000)

    def test_game_victory_screen(self):
        screen = pygame.Surface((1280, 720), pygame.SRCALPHA)
        game = Game(screen, p1_char="carloni", p2_char="cavasso", game_mode=MODE_PVAI)
        game.game_state = GameState.MATCH_OVER
        game.p1_wins = 2
        game.p2_wins = 0
        game.state_timer = 150
        game.draw_victory_screen(screen)
        self.assertIsNotNone(screen)

if __name__ == "__main__":
    unittest.main()
