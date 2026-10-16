"""
Unit and Integration Tests for Modern Python Game Architecture:
- pygame.sprite.LayeredUpdates and RenderLayer Z-ordering.
- pygame.FRect floating-point precision bounding boxes.
- Pymunk 2D physics space, static platforms, and raycast line-of-sight.
"""
import unittest
import os
import pygame
import pymunk

# Headless setup
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from src.engine.layers import LayeredRenderer, RenderLayer
from src.engine.pymunk_physics import PymunkPhysicsWorld
from src.engine.physics import PhysicsBody, Platform

class TestModernArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((320, 224))

    def test_pygame_frect_integration(self):
        """Verifies that PhysicsBody and Platform provide high-precision FRect bounding."""
        body = PhysicsBody(x=100.5, y=198.25, width=24, height=40)
        frect = body.frect
        self.assertIsInstance(frect, getattr(pygame, 'FRect', pygame.Rect))
        self.assertAlmostEqual(frect.x, 88.5, places=2)
        self.assertAlmostEqual(frect.bottom, 198.25, places=2)
        self.assertAlmostEqual(frect.width, 24.0, places=2)
        self.assertAlmostEqual(frect.height, 40.0, places=2)

        platform = Platform(10.2, 198.0, 500.8, 198.0, semi_solid=False)
        plat_frect = platform.frect
        self.assertIsInstance(plat_frect, getattr(pygame, 'FRect', pygame.Rect))
        self.assertAlmostEqual(plat_frect.x, 10.2, places=2)

    def test_layered_updates_z_ordering(self):
        """Verifies that LayeredRenderer correctly sorts sprites based on RenderLayer constants."""
        renderer = LayeredRenderer()

        # Create dummy sprites with different layers
        bg_sprite = pygame.sprite.Sprite()
        bg_sprite.image = pygame.Surface((32, 32))
        bg_sprite.rect = pygame.Rect(0, 0, 32, 32)

        player_sprite = pygame.sprite.Sprite()
        player_sprite.image = pygame.Surface((32, 32))
        player_sprite.rect = pygame.Rect(0, 0, 32, 32)

        hud_sprite = pygame.sprite.Sprite()
        hud_sprite.image = pygame.Surface((32, 32))
        hud_sprite.rect = pygame.Rect(0, 0, 32, 32)

        renderer.add(hud_sprite, layer=RenderLayer.HUD)
        renderer.add(bg_sprite, layer=RenderLayer.BACKGROUND)
        renderer.add(player_sprite, layer=RenderLayer.PLAYER)

        # Verification of layer ordering: BACKGROUND (0) < PLAYER (40) < HUD (80)
        sprites_in_order = renderer.sprites()
        self.assertEqual(sprites_in_order[0], bg_sprite)
        self.assertEqual(sprites_in_order[1], player_sprite)
        self.assertEqual(sprites_in_order[2], hud_sprite)

        self.assertEqual(renderer.get_layer_of_sprite(bg_sprite), RenderLayer.BACKGROUND)
        self.assertEqual(renderer.get_layer_of_sprite(player_sprite), RenderLayer.PLAYER)
        self.assertEqual(renderer.get_layer_of_sprite(hud_sprite), RenderLayer.HUD)

    def test_pymunk_physics_world_simulation(self):
        """Verifies that PymunkPhysicsWorld simulates gravity, platforms, and rigid bodies."""
        world = PymunkPhysicsWorld(gravity=(0, 900))

        # Add ground platform at y=200
        plat = Platform(0, 200, 500, 200, semi_solid=False)
        segment = world.add_platform(plat)
        self.assertIsNotNone(segment)

        # Add falling box at y=50
        body, shape = world.add_rigid_box(x=100, y=50, width=20, height=20, mass=10.0)
        initial_y = body.position.y

        # Step simulation for 30 frames (0.5 seconds)
        for _ in range(30):
            world.step(1.0 / 60.0)

        # Body should fall downward due to gravity
        self.assertGreater(body.position.y, initial_y)

    def test_pymunk_raycast_line_of_sight(self):
        """Verifies that Pymunk line-of-sight raycasting detects obstacles correctly."""
        world = PymunkPhysicsWorld()

        # Add a vertical wall at x=150 between y=50 and y=250
        wall_body = world.space.static_body
        wall_segment = pymunk.Segment(wall_body, (150, 50), (150, 250), radius=2.0)
        world.space.add(wall_segment)

        # Raycast across the wall from (50, 100) to (250, 100) -> Must hit
        hit = world.raycast((50, 100), (250, 100))
        self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit["point"].x, 150.0, delta=3.0)

        # Raycast above the wall from (50, 30) to (250, 30) -> Must not hit
        clear = world.raycast((50, 30), (250, 30))
        self.assertIsNone(clear)

if __name__ == "__main__":
    unittest.main()
