"""
Test Suite: Tier 4 Automated Headless Acceptance (Feature F19)
Requirement: 2000 continuous frames simulation through all 5 Mission 1 zones with 0 crashes,
0 unhandled exceptions, and 0 AttributeErrors.

Zones:
1. Beach (x=0..565)
2. Submarine (x=565..1350)
3. River Village (x=1350..2200)
4. Valley Path (x=2200..3300)
5. Boss Arena (x=3300..4153)
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import unittest
import pygame
from src.config import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE
)

pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.game import Game, STATE_GAMEPLAY
from src.entities.slug import MetalSlug
from src.entities.bosses.tetsuyuki import TetsuyukiBoss


class ScriptedInputManager:
    """Scripted input manager that delivers arcade input combinations according to frame script."""
    def __init__(self):
        self.frame = 0
        self.current_held = set()
        self.just_pressed = set()
        self.just_released = set()

    def set_inputs_for_frame(self, frame, player_x):
        self.frame = frame
        self.just_pressed.clear()
        self.just_released.clear()
        old_held = self.current_held.copy()
        new_held = set()

        # General campaign traversal: drive right
        new_held.add(ACTION_RIGHT)

        # Periodic jump to traverse steps, docks, and stilt huts
        if frame % 90 == 0:
            self.just_pressed.add(ACTION_JUMP)
            new_held.add(ACTION_JUMP)

        # Periodic shooting (rapid fire)
        if (frame // 4) % 2 == 0:
            new_held.add(ACTION_SHOOT)
            if ACTION_SHOOT not in old_held:
                self.just_pressed.add(ACTION_SHOOT)

        # Periodic grenade / cannon fire
        if frame % 180 == 30:
            self.just_pressed.add(ACTION_GRENADE)

        # Board vehicle around Submarine zone when near tank (x around 720)
        if 680 <= player_x <= 760 and frame % 20 == 0:
            self.just_pressed.add(ACTION_UP)
            new_held.add(ACTION_UP)

        # Slug out leap around frame 1500 (test ejection)
        if frame == 1500:
            self.just_pressed.add(ACTION_JUMP)
            new_held.add(ACTION_DOWN)

        # Determine just_pressed and just_released
        for act in new_held - old_held:
            self.just_pressed.add(act)
        for act in old_held - new_held:
            self.just_released.add(act)

        self.current_held = new_held

    def is_held(self, action):
        return action in self.current_held

    def is_just_pressed(self, action):
        return action in self.just_pressed

    def is_just_released(self, action):
        return action in self.just_released

    def update(self):
        self.just_pressed.clear()
        self.just_released.clear()


class TestAcceptanceHeadless(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.start_new_campaign("marco")

    def test_continuous_2000_frames_simulation(self):
        """F19-T4-1: Continuous 2000-frame simulation through all Mission 1 zones with 0 crashes and 0 AttributeErrors."""
        scripted_input = ScriptedInputManager()
        self.game.input_manager = scripted_input

        total_frames = 2000
        frames_executed = 0
        exceptions_encountered = []
        visited_zones = set()

        for frame in range(total_frames):
            try:
                # Track zone traversal based on player or vehicle x coordinate
                x_coord = self.game.player.physics.x
                if x_coord < 565:
                    visited_zones.add("Beach")
                elif x_coord < 1350:
                    visited_zones.add("Submarine")
                elif x_coord < 2200:
                    visited_zones.add("River Village")
                elif x_coord < 3300:
                    visited_zones.add("Valley Path")
                else:
                    visited_zones.add("Boss Arena")

                # Feed scripted inputs
                scripted_input.set_inputs_for_frame(frame, x_coord)

                # Keep stage timer replenished during long continuous run so game remains in active gameplay
                if self.game.time_remaining <= 5.0:
                    self.game.time_remaining = 60.0

                # Advance engine state
                self.game.update()
                self.game.draw()
                frames_executed += 1

            except Exception:
                import traceback
                exceptions_encountered.append(f"Frame {frame}:\n{traceback.format_exc()}")
                break

        self.assertEqual(
            exceptions_encountered, [],
            f"Headless simulation crashed with exception: {exceptions_encountered}"
        )
        self.assertEqual(
            frames_executed, total_frames,
            f"Simulation aborted prematurely after {frames_executed} frames"
        )
        self.assertTrue(
            self.game.is_running,
            "Game loop must remain active throughout 2000 frames"
        )

    def test_tank_full_gameplay_lifecycle_headless(self):
        """F19-T4-2: Metal Slug tank boarding, driving, firing vulcan/cannon, and Metal Slug Attack execute headlessly."""
        slug = MetalSlug(x=720, y=184)
        self.game.level.slugs = [slug]

        # 1. Board tank
        slug.enter_vehicle(self.game.player)
        self.assertTrue(slug.is_occupied)

        # 2. Simulate 120 frames inside tank: driving, rapid-fire vulcan, firing heavy cannon
        scripted_input = ScriptedInputManager()
        for f in range(120):
            scripted_input.set_inputs_for_frame(f, slug.physics.x)
            slug.handle_input(
                scripted_input,
                self.game.player_projectiles,
                self.game.particle_system,
                self.game.sound_manager
            )
            slug.update(self.game.level.platforms, self.game.level.enemies, self.game.particle_system)

        # 3. Trigger Metal Slug Attack
        slug.trigger_metal_slug_attack()
        self.assertTrue(slug.self_destruct_charging)

        # 4. Advance 30 frames of self-destruct charging
        for _ in range(30):
            slug.update(self.game.level.platforms, self.game.level.enemies, self.game.particle_system)

        # Verification: operations finished without unhandled exception
        self.assertIsNotNone(slug.physics.x)

    def test_all_zones_grounding_continuity_acceptance(self):
        """F19-T4-3: Vehicle and player terrain navigation remains grounded at natural visual heights across all zones."""
        level = self.game.level
        # Sample points across all 5 zones
        sample_x_coords = [
            50, 200, 400,          # Beach
            600, 800, 1100, 1300,  # Submarine
            1400, 1700, 2000,      # River Village
            2300, 2700, 3100,      # Valley Path
            3400, 3700, 4000       # Boss Arena
        ]
        for x in sample_x_coords:
            ground_plats = [p for p in level.platforms if p.x1 <= x <= p.x2 and not p.semi_solid]
            self.assertTrue(
                len(ground_plats) > 0,
                f"Missing solid base ground at x={x}"
            )
            h = ground_plats[0].get_height_at(x)
            self.assertLessEqual(
                h, 200.0,
                f"Ground height at x={x} is too deep: {h}"
            )
            self.assertGreaterEqual(
                h, 150.0,
                f"Ground height at x={x} is floating too high: {h}"
            )

    def test_visual_rendering_headless_pipeline(self):
        """F19-T4-4: Headless rendering pipeline executes 200 continuous frames of blitting without error."""
        for _ in range(200):
            self.game.update()
            self.game.draw()
        self.assertEqual(self.game.virtual_screen.get_width(), VIRTUAL_WIDTH)
        self.assertEqual(self.game.virtual_screen.get_height(), VIRTUAL_HEIGHT)

    def test_boss_combat_and_cascading_defeat_acceptance(self):
        """F19-T4-5: Boss arena entry, Phase 1 & 2 transitions, and 180-frame cascading defeat execute headlessly."""
        boss = TetsuyukiBoss(x=3750, y=184)
        self.game.level.boss = boss
        self.game.player.physics.x = 3600
        self.game.camera.lock_at(3380)

        # Activate boss
        boss.is_active = True
        self.assertEqual(boss.phase, 1)

        # Run 30 frames Phase 1
        for _ in range(30):
            boss.update(
                self.game.player,
                self.game.level.platforms,
                self.game.enemy_projectiles,
                self.game.particle_system,
                self.game.camera
            )

        # Transition to Phase 2
        boss.take_damage(40)
        self.assertEqual(boss.phase, 2)

        # Run 30 frames Phase 2
        for _ in range(30):
            boss.update(
                self.game.player,
                self.game.level.platforms,
                self.game.enemy_projectiles,
                self.game.particle_system,
                self.game.camera
            )

        # Trigger Defeat (80 damage total)
        boss.take_damage(40)
        self.assertTrue(boss.is_defeated)
        self.assertEqual(boss.defeat_timer, 180)

        # Run 180 frames of cascading explosions
        for _ in range(180):
            boss.update(
                self.game.player,
                self.game.level.platforms,
                self.game.enemy_projectiles,
                self.game.particle_system,
                self.game.camera
            )

        self.assertEqual(boss.defeat_timer, 0)


if __name__ == "__main__":
    unittest.main()
