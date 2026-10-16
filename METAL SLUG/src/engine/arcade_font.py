"""
Authentic Neo-Geo Arcade Pixel Font Renderer for Metal Slug 1.
Extracts and renders character glyphs directly from the official arcade HUD font sheet.
"""
import os
import pygame

class ArcadeFont:
    _initialized = False
    _glyphs = {}

    @classmethod
    def init(cls):
        if cls._initialized:
            return
        
        path = "Assets/Intro_Assets/arcade_font_sheet.png"
        if not os.path.exists(path):
            path = "test_output/official_alphabet.png"
            
        if os.path.exists(path):
            try:
                sheet = pygame.image.load(path).convert()
                sheet.set_colorkey((195, 195, 195))

                # Standard Arcade HUD letters A-Z (Row 0 at y=3..11)
                letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                s0 = [3, 12, 21, 30, 39, 48, 57, 66, 75, 84, 93, 102, 111, 120, 129,
                      138, 147, 156, 165, 174, 183, 192, 201, 210, 219, 228]
                e0 = [10, 19, 28, 37, 46, 55, 64, 73, 82, 91, 100, 109, 118, 127, 136,
                      145, 154, 163, 172, 181, 190, 199, 208, 217, 226, 235]
                for char, s, e in zip(letters, s0, e0):
                    cls._glyphs[char] = sheet.subsurface((s, 3, e - s, 8))

                # Standard Arcade HUD digits 1-9, 0 (Row 1 at y=13..21)
                digits = "1234567890"
                s1 = [4, 10, 19, 28, 37, 46, 55, 64, 73, 82]
                e1 = [8, 17, 26, 35, 44, 53, 62, 71, 80, 89]
                for char, s, e in zip(digits, s1, e1):
                    cls._glyphs[char] = sheet.subsurface((s, 13, e - s, 8))

                cls._glyphs["-"] = sheet.subsurface((96, 13, 7, 8))
                cls._glyphs["."] = sheet.subsurface((91, 13, 3, 8))
                cls._initialized = True
            except Exception as e:
                print(f"[ArcadeFont] Error loading font glyphs: {e}")
                cls._initialized = False

    @classmethod
    def render(cls, text, spacing=1):
        """Renders string into a crisp arcade pixel surface."""
        if not cls._initialized:
            cls.init()
            
        if not cls._initialized:
            font = pygame.font.Font(None, 14)
            return font.render(text, False, (220, 220, 220))

        text_upper = str(text).upper()
        total_w = sum(cls._glyphs[c].get_width() + spacing if c in cls._glyphs else 5 for c in text_upper)
        if total_w <= 0:
            total_w = 1
        surf = pygame.Surface((total_w, 8), pygame.SRCALPHA)
        cur_x = 0
        for c in text_upper:
            if c in cls._glyphs:
                g = cls._glyphs[c]
                surf.blit(g, (cur_x, 0))
                cur_x += g.get_width() + spacing
            else:
                cur_x += 5
        return surf
