"""
Adversarial Stress Test Suite: Milestone 1 (Core Physics & Level Collision Fixes R1)
Authored by: Challenger 1 (Empirical Challenger)

Tests:
1. Coordinate Sweep & Dynamic Traversal (all 4154 coordinates, step discontinuities)
2. Edge Clamping Stress Tests (Player & SV-001 Tank under moving/locked camera)
3. Semi-Solid Platform Stress Tests (Jumping, multi-tier dropping, slope drop-through)
4. Riverbed & Waterline Grounding Verification
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import unittest
import pygame
from src.config import VIRTUAL_WIDTH, VIRTUAL_HEIGHT, PLAYER_WALK_SPEED, ACTION_LEFT, ACTION_RIGHT
pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.engine.physics import Platform, PhysicsBody
from src.levels.mission1 import Mission1
from src.entities.player import Player
from src.entities.slug import MetalSlug
from src.core.camera import Camera
from src.game import Game


class TestAdversarialMilestone1(unittest.TestCase):
    def setUp(self):
        self.level = Mission1()

    # =========================================================================
    # 1. COORDINATE SWEEP & CONTINUITY STRESS TESTS
    # =========================================================================
    def test_static_ground_continuity_all_4154_coordinates(self):
        """Adversarial 1.1: Verify every single integer coordinate x in [0..4153] has solid base ground."""
        missing_ground = []
        for x in range(0, 4154):
            solids = [p for p in self.level.platforms if p.x1 <= x <= p.x2 and not p.semi_solid]
            if len(solids) == 0:
                missing_ground.append(x)
        self.assertEqual(len(missing_ground), 0, f"Found {len(missing_ground)} coordinates without solid ground: {missing_ground[:10]}")

    def test_static_ground_continuity_subpixel_floats(self):
        """Adversarial 1.2: Verify float sub-pixel coordinates have solid base ground."""
        missing_subpixels = []
        for i in range(0, 4153):
            x = i + 0.5
            solids = [p for p in self.level.platforms if p.x1 <= x <= p.x2 and not p.semi_solid]
            if len(solids) == 0:
                missing_subpixels.append(x)
        self.assertEqual(len(missing_subpixels), 0, f"Found sub-pixel gaps: {missing_subpixels[:10]}")

    def test_dynamic_traversal_forward_entire_stage(self):
        """Adversarial 1.3: Walk continuously forward from x=0 to x=4150; entity must never fall out of world."""
        body = PhysicsBody(x=0, y=160, width=18, height=34)
        body.is_grounded = True
        body.vx = PLAYER_WALK_SPEED
        
        pit_falls = []
        # Total distance 4150 / 1.8 ≈ 2305 frames
        for f in range(2500):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.y > VIRTUAL_HEIGHT:
                pit_falls.append((f, body.x, body.y))
                break
            if body.x >= 4150:
                break

        self.assertEqual(len(pit_falls), 0, f"Entity fell through world moving forward: {pit_falls}")

    def test_dynamic_traversal_backward_across_step_205(self):
        """Adversarial 1.4: Walking left across step at x=205 (y=176 to y=160).
        Reveals whether vertical step boundary lacks horizontal collision or step climb,
        causing entity to fall into the void.
        """
        body = PhysicsBody(x=210, y=176, width=18, height=34)
        body.is_grounded = True
        body.vx = -PLAYER_WALK_SPEED

        fell_into_void = False
        for f in range(25):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.y > VIRTUAL_HEIGHT:
                fell_into_void = True
                break

        self.assertFalse(
            fell_into_void,
            f"BUG: Entity walking left across step at x=205 fell into void (final y={body.y:.1f})"
        )

    def test_dynamic_traversal_backward_across_step_360(self):
        """Adversarial 1.5: Walking left across step at x=360 (y=198 to y=178).
        Reveals whether step boundary causes entity to fall into the void.
        """
        body = PhysicsBody(x=365, y=198, width=18, height=34)
        body.is_grounded = True
        body.vx = -PLAYER_WALK_SPEED

        fell_into_void = False
        for f in range(25):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.y > VIRTUAL_HEIGHT:
                fell_into_void = True
                break

        self.assertFalse(
            fell_into_void,
            f"BUG: Entity walking left across step at x=360 fell into void (final y={body.y:.1f})"
        )

    # =========================================================================
    # 2. SCREEN-EDGE CLAMPING STRESS TESTS
    # =========================================================================
    def test_player_static_left_and_right_clamps(self):
        """Adversarial 2.1: Player on foot within screen bounds at stationary clamps."""
        game = Game()
        game.start_new_campaign("marco")
        
        # Test stationary left clamp
        game.camera.x = 300.0
        game.player.physics.x = 250.0
        game.update()
        half_w = game.player.physics.width / 2.0
        screen_left = (game.player.physics.x - half_w) - game.camera.x
        self.assertGreaterEqual(screen_left, 0.0)

        # Test stationary right clamp with locked camera
        game.camera.lock_at(300.0)
        game.player.physics.x = 700.0
        game.update()
        screen_right = (game.player.physics.x + half_w) - game.camera.x
        self.assertLessEqual(screen_right, float(VIRTUAL_WIDTH))

    def test_slug_dynamic_left_clamp_while_driving_left(self):
        """Adversarial 2.2: SV-001 tank driving left against left screen bound.
        Reveals whether tank clips past left edge (screen_left < 0) due to unzeroed vx.
        """
        game = Game()
        game.start_new_campaign("marco")
        slug = game.level.slugs[0]
        slug.enter_vehicle(game.player)
        
        game.camera.x = 200.0
        game.camera.max_scrolled_x = 200.0
        half_w = slug.physics.width / 2.0
        slug.physics.x = game.camera.x + half_w
        
        game.input_manager.current_state[ACTION_LEFT] = True
        game.update()
        
        screen_left = (slug.physics.x - half_w) - game.camera.x
        self.assertGreaterEqual(
            screen_left, 0.0,
            f"BUG: Tank clipped off left screen edge by {-screen_left:.2f}px while driving left"
        )

    def test_slug_dynamic_right_clamp_while_driving_right_in_locked_camera(self):
        """Adversarial 2.3: SV-001 tank driving right against right screen bound in locked camera.
        Reveals whether tank clips past right edge (screen_right > 320) due to unzeroed vx.
        """
        game = Game()
        game.start_new_campaign("marco")
        slug = game.level.slugs[0]
        slug.enter_vehicle(game.player)
        
        game.camera.lock_at(200.0)
        game.camera.x = 200.0
        game.camera.max_scrolled_x = 200.0
        half_w = slug.physics.width / 2.0
        slug.physics.x = game.camera.x + VIRTUAL_WIDTH - half_w
        
        game.input_manager.current_state[ACTION_RIGHT] = True
        game.update()
        
        screen_right = (slug.physics.x + half_w) - game.camera.x
        self.assertLessEqual(
            screen_right, float(VIRTUAL_WIDTH),
            f"BUG: Tank clipped past right screen edge by {screen_right - VIRTUAL_WIDTH:.2f}px while driving right"
        )

    def test_camera_boss_arena_lock_latch_resilience(self):
        """Adversarial 2.4: Camera latch remains locked through rapid back-and-forth oscillations."""
        camera = Camera()
        player = Player(x=3265, y=184)
        
        # Trigger latch
        self.level.update(player, camera)
        self.assertTrue(camera.is_locked)
        self.assertEqual(camera.x, 3260.0)

        # Oscillate player backward and forward across trigger line
        for offset in [-100, -200, 50, -50, 100, -300]:
            player.physics.x = 3260.0 + offset
            self.level.update(player, camera)
            self.assertTrue(camera.is_locked, f"Camera unlocked prematurely when player at {player.physics.x}")
            self.assertEqual(camera.x, 3260.0)

        # Defeat boss -> unlock
        self.level.boss.is_defeated = True
        self.level.boss.defeat_timer = 0
        self.level.update(player, camera)
        self.assertFalse(camera.is_locked, "Camera failed to unlock after boss defeat")

    # =========================================================================
    # 3. SEMI-SOLID PLATFORM JUMP & DROP-THROUGH STRESS TESTS
    # =========================================================================
    def test_drop_through_all_semi_solid_platforms(self):
        """Adversarial 3.1: Drop through all elevated semi-solid platforms and verify entity lands safely on ground."""
        semi_solids = [p for p in self.level.platforms if p.semi_solid]
        self.assertGreater(len(semi_solids), 0)

        failed_platforms = []
        for plat in semi_solids:
            mid_x = (plat.x1 + plat.x2) / 2.0
            height = plat.get_height_at(mid_x)
            body = PhysicsBody(x=mid_x, y=height, width=18, height=34)
            body.is_grounded = True
            body.current_platform = plat
            
            body.drop_through_platform()
            
            for _ in range(30):
                body.apply_gravity()
                body.update_movement(self.level.platforms)
                
            if not body.is_grounded or body.y > VIRTUAL_HEIGHT:
                failed_platforms.append((plat, mid_x, height, body.y, body.is_grounded))

        self.assertEqual(
            len(failed_platforms), 0,
            f"Drop-through failed on {len(failed_platforms)} platforms: {failed_platforms}"
        )

    def test_drop_through_wing_slope_boundary_coordinates(self):
        """Adversarial 3.2: Drop through wing slope near bottom (x=3380..3387).
        Reveals whether unconditional self.y += 3.0 pushes entity below solid riverbed (y=184),
        causing fall-through into void.
        """
        wing = [p for p in self.level.platforms if p.x1 <= 3400 <= p.x2 and p.semi_solid and p.y1 != p.y2][0]
        
        failed_xs = []
        for x in range(3380, 3390):
            h = wing.get_height_at(x)
            body = PhysicsBody(x=x, y=h, width=18, height=34)
            body.is_grounded = True
            body.current_platform = wing
            
            body.drop_through_platform()
            for _ in range(25):
                body.apply_gravity()
                body.update_movement(self.level.platforms)
                
            if not body.is_grounded or body.y != 198.0:
                failed_xs.append((x, h, body.y, body.is_grounded))

        self.assertEqual(
            len(failed_xs), 0,
            f"BUG: Entity dropped through wing slope and fell through solid riverbed at coordinates: {failed_xs}"
        )

    def test_drop_through_solid_ground_is_rejected(self):
        """Adversarial 3.3: Attempting drop-through on solid base ground (semi_solid=False) must be rejected."""
        solids = [p for p in self.level.platforms if not p.semi_solid]
        for p in solids:
            mid_x = (p.x1 + p.x2) / 2.0
            h = p.get_height_at(mid_x)
            body = PhysicsBody(x=mid_x, y=h, width=18, height=34)
            body.is_grounded = True
            body.current_platform = p
            
            body.drop_through_platform()
            self.assertTrue(body.is_grounded, f"Drop through should not trigger on solid ground at {mid_x}")
            self.assertEqual(body.ignore_platform_timer, 0)

    def test_multi_tier_scaffolding_sequential_drop(self):
        """Adversarial 3.4: Dropping from mid scaffolding (y=110) lands on lower tier (y=144),
        then dropping again lands on riverbed (y=184).
        """
        mid_scaffold = [p for p in self.level.platforms if p.x1 <= 3150 <= p.x2 and p.y1 == 110][0]
        body = PhysicsBody(x=3150, y=110, width=18, height=34)
        body.is_grounded = True
        body.current_platform = mid_scaffold
        
        # Drop 1: Mid -> Lower
        body.drop_through_platform()
        for _ in range(20):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 144.0, "Entity should land on lower scaffolding (y=144)")

        # Drop 2: Lower -> Riverbed
        body.drop_through_platform()
        for _ in range(20):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0, "Entity should land on riverbed (y=184)")

    def test_high_speed_slope_ascent_retention(self):
        """Adversarial 3.5: Entity ascending wing slope at high velocity (e.g. Kamikaze Slug vx=6.0).
        Tests whether slope gradient exceeds vertical collision tolerance, causing entity to detach and fall off slope.
        """
        wing = [p for p in self.level.platforms if p.x1 == 3380][0]
        slug = MetalSlug(x=3400, y=wing.get_height_at(3400))
        slug.physics.vx = 6.0
        slug.physics.is_grounded = True
        
        detached = False
        for f in range(15):
            slug.physics.apply_gravity()
            slug.physics.update_movement(self.level.platforms)
            if slug.physics.current_platform is not None and slug.physics.current_platform.semi_solid:
                pass
            elif not slug.physics.is_grounded or slug.physics.y == 198.0:
                detached = True
                break

        self.assertFalse(
            detached,
            f"BUG: Fast entity (vx=6.0) detached from slope at x={slug.physics.x:.1f}, y={slug.physics.y:.1f}"
        )

    # =========================================================================
    # 4. RIVERBED & WATERLINE GROUNDING VERIFICATION
    # =========================================================================
    def test_riverbed_grounding_across_all_water_zones(self):
        """Adversarial 4.1: Solid ground in River Village, Valley Path, and Boss Arena is uniformly y=184."""
        for x in [1400, 1800, 2100, 2300, 2600, 2900, 3200, 3400, 3700, 4000]:
            ground = [p for p in self.level.platforms if p.x1 <= x <= p.x2 and not p.semi_solid]
            self.assertEqual(len(ground), 1, f"Expected exactly 1 solid ground at x={x}")
            self.assertEqual(ground[0].get_height_at(x), 198.0, f"Riverbed height mismatch at x={x}")

    def test_no_floating_solid_platforms_over_water(self):
        """Adversarial 4.2: Ensure all elevated structures over water (x >= 1350) are semi-solid."""
        water_platforms = [p for p in self.level.platforms if p.x1 >= 1350]
        elevated_solids = [p for p in water_platforms if not p.semi_solid and (p.y1 < 184 or p.y2 < 184)]
        self.assertEqual(
            len(elevated_solids), 0,
            f"Found floating solid platforms over water: {elevated_solids}"
        )


if __name__ == "__main__":
    unittest.main()
