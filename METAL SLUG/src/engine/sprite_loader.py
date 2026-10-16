"""
High-performance Sprite and Sheet Loader for Metal Slug 1.
Features:
- Chroma-key transparency caching (#99D9EA, #00F800, #FF00FF).
- Subsurface clipping and caching.
- Horizontal flipping with zero runtime recalculation.
"""
import os
import pygame
from src.config import CHROMA_CYAN, CHROMA_GREEN, CHROMA_MAGENTA

class SpriteLoader:
    _instance = None
    _sheet_cache = {}

    @classmethod
    def load_sheet(cls, filepath, colorkey=CHROMA_CYAN):
        """Loads a spritesheet from disk and converts with specified colorkey transparency."""
        if filepath in cls._sheet_cache:
            return cls._sheet_cache[filepath]
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Sprite sheet not found at path: {filepath}")
            
        raw_surface = pygame.image.load(filepath)
        
        # If colorkey is explicitly requested, strip alpha and set colorkey
        if colorkey is not None:
            converted = raw_surface.convert()
            converted.set_colorkey(colorkey)
        elif raw_surface.get_masks()[3] != 0:
            converted = raw_surface.convert_alpha()
        else:
            converted = raw_surface.convert()
                
        cls._sheet_cache[filepath] = converted
        return converted

    @classmethod
    def get_subsurface(cls, sheet, x, y, w, h, flip_x=False, colorkey=None):
        """Extracts a bounding rect from a loaded sheet with optional horizontal flipping."""
        rect = pygame.Rect(x, y, w, h)
        sub = sheet.subsurface(rect).copy()
        
        # Propagate parent colorkey or custom colorkey
        effective_colorkey = colorkey if colorkey is not None else sheet.get_colorkey()
        if effective_colorkey is not None:
            sub.set_colorkey(effective_colorkey)
            
        if flip_x:
            sub = pygame.transform.flip(sub, True, False)
            if effective_colorkey is not None:
                sub.set_colorkey(effective_colorkey)
        return sub

    @classmethod
    def extract_frames(cls, sheet, rects, flip_x=False):
        """Extracts an array of frames given a list of (x, y, w, h) bounding tuples."""
        frames = []
        for r in rects:
            if isinstance(r, (list, tuple)) and len(r) == 4:
                frames.append(cls.get_subsurface(sheet, r[0], r[1], r[2], r[3], flip_x=flip_x))
            elif isinstance(r, pygame.Rect):
                frames.append(cls.get_subsurface(sheet, r.x, r.y, r.width, r.height, flip_x=flip_x))
        return frames
