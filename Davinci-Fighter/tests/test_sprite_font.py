"""
test_sprite_font.py - Unit tests for SpriteFont and BootFont.
"""

import unittest
import os
import pygame
from sprite_font import SpriteFont, BootFont, get_boot_font, BOOT_GLYPHS
from intro_cutscene import IntroCutscene

class TestSpriteFont(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1), pygame.HIDDEN)

    def test_boot_font_singleton(self):
        bf1 = get_boot_font()
        bf2 = get_boot_font()
        self.assertIs(bf1, bf2)
        self.assertTrue(isinstance(bf1, BootFont))
        self.assertTrue(isinstance(bf1, SpriteFont))
        self.assertIsNotNone(bf1.sheet)

    def test_boot_font_glyphs_presence(self):
        bf = get_boot_font()
        expected_chars = ['S', 'C', 'R', '1', '2', '3', 'A', 'M', 'O', 'K', 'B', 'J', 'E', 'T', 'W']
        for ch in expected_chars:
            self.assertIn(ch, bf.glyphs, f"Glyph {ch} should be loaded in BootFont")
            self.assertIsInstance(bf.glyphs[ch], pygame.Surface)
            self.assertEqual(bf.glyphs[ch].get_width(), 52)
            self.assertEqual(bf.glyphs[ch].get_height(), 66)

    def test_draw_text_advancement_and_spaces(self):
        bf = get_boot_font()
        surface = pygame.Surface((1280, 720))
        surface.fill((0, 0, 0))

        # Single word without spaces
        rect_word = bf.draw_text(surface, "SCR", 100, 100, scale=1.0)
        self.assertEqual(rect_word.width, 52 * 3)

        # Word with spaces
        rect_with_space = bf.draw_text(surface, "SCR 1   RAM OK", 100, 200, scale=1.0)
        expected_len = len("SCR 1   RAM OK")
        self.assertEqual(rect_with_space.width, 52 * expected_len)

    def test_missing_glyph_no_crash(self):
        bf = get_boot_font()
        surface = pygame.Surface((800, 600))
        # '9' and 'Z' are missing from boot font; should not raise exception
        try:
            rect = bf.draw_text(surface, "SCR 9   RAM OK Z", 50, 50, scale=0.5)
            self.assertGreater(rect.width, 0)
        except Exception as e:
            self.fail(f"draw_text raised an unexpected exception for missing glyph: {e}")

    def test_scaling_and_dimensions(self):
        bf = get_boot_font()
        w1, h1 = bf.get_text_size("SCR 1", scale=1.0)
        w2, h2 = bf.get_text_size("SCR 1", scale=0.5)
        self.assertEqual(w1, 52 * 5)
        self.assertEqual(h1, 66)
        self.assertEqual(w2, int(52 * 0.5) * 5)
        self.assertEqual(h2, int(66 * 0.5))

    def test_render_surface_generation(self):
        bf = get_boot_font()
        surf = bf.render("SCR 1   RAM OK", scale=0.7)
        self.assertIsInstance(surf, pygame.Surface)
        self.assertGreater(surf.get_width(), 0)
        self.assertGreater(surf.get_height(), 0)

    def test_warning_font_singleton_and_glyphs(self):
        from sprite_font import get_warning_font, WarningFont
        wf = get_warning_font()
        self.assertIsNotNone(wf)
        self.assertTrue(isinstance(wf, WarningFont))
        self.assertTrue(isinstance(wf, SpriteFont))
        self.assertIsNotNone(wf.sheet)
        self.assertGreaterEqual(len(wf.glyphs), 80)
        
        # Check presence of uppercase, lowercase, numbers, and symbols
        self.assertIn('A', wf.glyphs)
        self.assertIn('a', wf.glyphs)
        self.assertIn('0', wf.glyphs)
        self.assertIn('!', wf.glyphs)
        self.assertIn('.', wf.glyphs)
        self.assertIn(',', wf.glyphs)

    def test_warning_font_draw_text(self):
        from sprite_font import get_warning_font
        wf = get_warning_font()
        surface = pygame.Surface((1280, 720))
        surface.fill((0, 0, 0))

        rect = wf.draw_text(surface, "WARNING", 100, 100, scale=0.7, letter_spacing=2)
        self.assertGreater(rect.width, 0)
        self.assertGreater(rect.height, 0)

        # Test lowercase sentence with punctuation
        sentence = "This game is for use in all countries,"
        rect2 = wf.draw_text(surface, sentence, 100, 200, scale=0.35, letter_spacing=1)
        self.assertGreater(rect2.width, 0)

    def test_intro_cutscene_phase_title_code_and_warning(self):
        screen = pygame.Surface((1280, 720))
        cutscene = IntroCutscene(screen)
        
        # Test Phase 2 Title Code (streetfighter davinci fade) at t=5.0s (in range 3.5s .. 7.5s)
        cutscene.elapsed_time = 5.0
        self.assertEqual(cutscene.phase, IntroCutscene.PHASE_TITLE_CODE)
        cutscene.draw(screen)
        self.assertIsNotNone(screen)

        # Test Phase 3 Warning typewriter animation at t=10.0s (in range 7.5s .. 17.5s)
        cutscene.elapsed_time = 10.0
        self.assertEqual(cutscene.phase, IntroCutscene.PHASE_WARNING)
        cutscene.draw(screen)
        self.assertIsNotNone(screen)

if __name__ == "__main__":
    unittest.main()

