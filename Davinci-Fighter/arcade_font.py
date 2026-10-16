"""
arcade_font.py - Street Fighter II (Large) (Colour) Authentic Arcade Font Renderer
================================================================================
Faithful Capcom Street Fighter II pixel font renderer using the authentic
character set recreation by Patrick H. Lauke (redux).

Used for:
- HUD scores (1P / 2P score, high score)
- Battle announcements: "YOU WIN", "YOU LOSE", "START !", "BONUS STAGE", "K.O.", "ROUND 1", "FIGHT!"
- Post-fight victory quotes / after-fight taunts
- Character selection & VS screen labels
"""

import os
import json
import pygame

class ArcadeFont:
    """Arcade-accurate font renderer for Street Fighter II Large Colour font."""
    _instance = None

    def __init__(self, sheet_path=None, meta_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if sheet_path is None:
            sheet_path = os.path.join(base_dir, "assets", "fonts", "sf2_font_sheet.png")
        if meta_path is None:
            meta_path = os.path.join(base_dir, "assets", "fonts", "sf2_font_sheet.json")

        self.sheet = None
        self.glyphs = {}
        self.char_meta = {}
        self.cache = {}
        self.loaded = False

        if os.path.exists(sheet_path) and os.path.exists(meta_path):
            try:
                try:
                    self.sheet = pygame.image.load(sheet_path).convert_alpha()
                except Exception:
                    self.sheet = pygame.image.load(sheet_path)
                with open(meta_path, "r") as f:
                    self.char_meta = json.load(f)

                # Pre-extract glyph subsurfaces
                for ch, m in self.char_meta.items():
                    w, h = m["w"], m["h"]
                    if w > 0 and h > 0:
                        rect = pygame.Rect(m["x"], m["y"], w, h)
                        self.glyphs[ch] = self.sheet.subsurface(rect)
                    else:
                        self.glyphs[ch] = None
                self.loaded = True
            except Exception as e:
                print(f"[ArcadeFont] Error loading font assets: {e}")
                self.loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ArcadeFont()
        return cls._instance

    def size(self, text: str, scale: float = 1.0, tracking: int = 0) -> tuple:
        """Calculate total (width, height) of a rendered string."""
        if not text:
            return (0, 0)
        
        total_w = 0
        max_h = 30
        for ch in text:
            if ch in self.char_meta:
                adv = self.char_meta[ch]["advance"]
                h = self.char_meta[ch]["h"]
            else:
                adv = 16
                h = 30
            total_w += adv + tracking
            if h > max_h:
                max_h = h
        
        # Remove trailing tracking
        if total_w > 0:
            total_w -= tracking

        return (int(total_w * scale), int(max_h * scale))

    def render(self, text: str, antialias: bool = True, color: tuple = None, scale: float = 1.0, tracking: int = 0) -> pygame.Surface:
        """
        Render text to a pygame.Surface with authentic Capcom SF2 styling.
        Compatible with Pygame Font.render(text, antialias, color) signature.
        """
        if not text:
            return pygame.Surface((1, 1), pygame.SRCALPHA)

        cache_key = (text, scale, tracking, color)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Calculate unscaled bounding box
        unscaled_w, unscaled_h = self.size(text, scale=1.0, tracking=tracking)
        unscaled_w = max(unscaled_w, 1)
        unscaled_h = max(unscaled_h, 1)

        surf = pygame.Surface((unscaled_w, unscaled_h), pygame.SRCALPHA)

        curr_x = 0
        for ch in text:
            m = self.char_meta.get(ch)
            glyph = self.glyphs.get(ch)
            
            if glyph is not None and m is not None:
                # Vertical alignment: characters are top-aligned to baseline
                surf.blit(glyph, (curr_x, 0))
                adv = m["advance"]
            else:
                adv = 16 if ch == ' ' else 14
            
            curr_x += adv + tracking

        # Scale if requested
        if abs(scale - 1.0) > 0.01:
            target_w = max(1, int(unscaled_w * scale))
            target_h = max(1, int(unscaled_h * scale))
            # Use smoothscale or scale (scale preserves pixel sharpness)
            if scale >= 1.0:
                surf = pygame.transform.scale(surf, (target_w, target_h))
            else:
                surf = pygame.transform.smoothscale(surf, (target_w, target_h))

        # Color tinting if specified and not standard yellow
        if color is not None and color != (255, 255, 255):
            # Optional color tint: multiply RGB while preserving alpha
            # If standard SF2 colors (original has yellow/gold gradient), we only tint when needed
            pass

        # Store in cache (limit cache size)
        if len(self.cache) > 200:
            self.cache.clear()
        self.cache[cache_key] = surf
        return surf

    def render_to(self, target_surf: pygame.Surface, pos: tuple, text: str,
                  scale: float = 1.0, tracking: int = 0, align: str = "left", color: tuple = None):
        """Render directly onto target surface at pos with alignment ('left', 'center', 'right')."""
        txt_surf = self.render(text, scale=scale, tracking=tracking, color=color)
        w, h = txt_surf.get_size()
        x, y = pos
        if align == "center":
            x -= w // 2
            y -= h // 2
        elif align == "right":
            x -= w
        target_surf.blit(txt_surf, (x, y))
        return pygame.Rect(x, y, w, h)


# Global singleton helper
_arcade_font = None

def get_arcade_font() -> ArcadeFont:
    global _arcade_font
    if _arcade_font is None:
        _arcade_font = ArcadeFont()
    return _arcade_font
