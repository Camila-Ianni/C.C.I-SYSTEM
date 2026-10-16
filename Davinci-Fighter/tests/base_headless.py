import os
import sys
import math
import unittest

# Configure SDL dummy drivers for headless CI execution before importing pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import numpy as np

# Canonical arcade coordinates and constants derived from specs and assets
CANONICAL_SCREEN_WIDTH = 1280
CANONICAL_SCREEN_HEIGHT = 720
CANONICAL_FPS = 60

# World Map Waypoints for 5 Professors (China, USA, Spain, Brazil, Japan)
WORLD_MAP_WAYPOINTS = {
    "carloni": {"country": "China", "x": 544, "y": 159},
    "cavasso": {"country": "USA", "x": 967, "y": 147},
    "romero": {"country": "Spain", "x": 201, "y": 140},
    "gamaliel": {"country": "Brazil", "x": 978, "y": 318},
    "sellanes": {"country": "Japan", "x": 683, "y": 184},
}

# 16-slot grid slots in 1280x720 canvas
GRID_ROW_0_Y = 463
GRID_ROW_1_Y = 555
GRID_SLOT_HEIGHT = 92

GRID_SLOTS = [
    {"slot": 0, "row": 0, "col": 0, "rect": (269, 463, 90, 92), "char": "carloni"},
    {"slot": 1, "row": 0, "col": 1, "rect": (359, 463, 95, 92), "char": "cavasso"},
    {"slot": 2, "row": 0, "col": 2, "rect": (454, 463, 92, 92), "char": "romero"},
    {"slot": 3, "row": 0, "col": 3, "rect": (546, 463, 94, 92), "char": "gamaliel"},
    {"slot": 4, "row": 0, "col": 4, "rect": (639, 463, 92, 92), "char": "sellanes"},
    {"slot": 5, "row": 0, "col": 5, "rect": (731, 463, 94, 92), "char": None},
    {"slot": 6, "row": 0, "col": 6, "rect": (825, 463, 92, 92), "char": None},
    {"slot": 7, "row": 0, "col": 7, "rect": (917, 463, 93, 92), "char": None},
] + [
    {"slot": 8 + col, "row": 1, "col": col, "rect": (269 + col * 92, 555, 92, 92), "char": None}
    for col in range(8)
]

# Dedicated Stage Music mapping
STAGE_MUSIC_MAP = {
    "carloni": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
    "cavasso": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
    "romero": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
    "gamaliel": "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3",
    "sellanes": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
}

# Dedicated Stage Background mapping
STAGE_SHEET_MAP = {
    "carloni": "Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Ryu Stage.png",
    "cavasso": "Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Guile Stage.png",
    "romero": "Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Sagat Stage.png",
    "gamaliel": "Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Blanka Stage.png",
    "sellanes": "Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - M. Bison Stage.png",
}


def calculate_flight_position(p1_coord, p2_coord, t):
    """
    Computes vector interpolation P(t) = (1 - t) * P1 + t * P2 with clamped t in [0.0, 1.0].
    """
    t_clamped = max(0.0, min(1.0, float(t)))
    x = p1_coord[0] + (p2_coord[0] - p1_coord[0]) * t_clamped
    y = p1_coord[1] + (p2_coord[1] - p1_coord[1]) * t_clamped
    return (x, y)


def calculate_heading_angle(p1_coord, p2_coord):
    """
    Computes heading angle in degrees from p1 to p2.
    """
    dx = p2_coord[0] - p1_coord[0]
    dy = p2_coord[1] - p1_coord[1]
    if dx == 0 and dy == 0:
        return 0.0
    return math.degrees(math.atan2(dy, dx))


def generate_procedural_tone(frequency=440.0, duration=0.1, sample_rate=44100, volume=0.5):
    """
    Synthesizes a 16-bit PCM stereo tone in-memory using numpy and sndarray.
    """
    if duration <= 0:
        duration = 0.01
    sample_count = int(sample_rate * duration)
    t = np.linspace(0, duration, sample_count, False)
    wave = volume * np.sin(2 * np.pi * frequency * t)
    audio_pcm = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((audio_pcm, audio_pcm))
    return pygame.sndarray.make_sound(stereo)


class HeadlessTestCase(unittest.TestCase):
    """
    Base test fixture for all headless E2E pre-combat sequence tests.
    Provides standard display surface, clock, event injection, and virtual time stepping.
    """
    screen = None
    clock = None

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.init()
        pygame.font.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except Exception:
            pass

        cls.screen = pygame.display.set_mode((CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT))
        cls.clock = pygame.time.Clock()

    @classmethod
    def tearDownClass(cls):
        if pygame.mixer.get_init():
            try:
                pygame.mixer.stop()
                pygame.mixer.quit()
            except Exception:
                pass
        pygame.font.quit()
        pygame.display.quit()
        pygame.quit()

    def setUp(self):
        """Purge any remaining SDL lifecycle events before each test run."""
        self.clear_events()

    def tearDown(self):
        """Clean up audio playback and pending events after each test run."""
        self.clear_events()
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def clear_events(self):
        """Flushes all queued Pygame events."""
        pygame.event.pump()
        pygame.event.clear()

    def post_key(self, key, event_type=pygame.KEYDOWN, mod=0, unicode=""):
        """Posts a synthetic keyboard event to the Pygame event queue."""
        event = pygame.event.Event(event_type, key=key, mod=mod, unicode=unicode)
        pygame.event.post(event)

    def post_keys(self, keys, event_type=pygame.KEYDOWN):
        """Posts multiple synthetic keyboard events in order."""
        for k in keys:
            self.post_key(k, event_type=event_type)

    def advance_frames(self, scene_or_app, frame_count=1, dt=1.0 / 60.0):
        """
        Advances virtual time across a scene or callback for frame_count frames.
        Returns the last non-None result returned by update.
        """
        last_result = None
        for _ in range(frame_count):
            if hasattr(scene_or_app, "update"):
                try:
                    res = scene_or_app.update(dt)
                except TypeError:
                    res = scene_or_app.update()
                if res is not None:
                    last_result = res
            elif callable(scene_or_app):
                try:
                    res = scene_or_app(dt)
                except TypeError:
                    res = scene_or_app()
                if res is not None:
                    last_result = res
        return last_result

    def assert_valid_surface(self, surf, expected_size=None):
        """Validates that a given object is a valid Pygame Surface with non-zero dimensions."""
        self.assertIsInstance(surf, pygame.Surface)
        self.assertGreater(surf.get_width(), 0)
        self.assertGreater(surf.get_height(), 0)
        if expected_size is not None:
            self.assertEqual(surf.get_size(), expected_size)

    def assert_point_within_screen(self, x, y, width=CANONICAL_SCREEN_WIDTH, height=CANONICAL_SCREEN_HEIGHT):
        """Validates that a point (x, y) resides inside the 1280x720 display canvas."""
        self.assertGreaterEqual(x, 0, f"X coordinate {x} is negative")
        self.assertLessEqual(x, width, f"X coordinate {x} exceeds screen width {width}")
        self.assertGreaterEqual(y, 0, f"Y coordinate {y} is negative")
        self.assertLessEqual(y, height, f"Y coordinate {y} exceeds screen height {height}")
