"""
Adversarial Stress Test Suite: Milestone 1 (Core Physics & Level Collision Fixes R1)
Authored by: Challenger 2 (Empirical Challenger)

Empirical Challenge Dimensions:
1. Multi-tier scaffolding traversal (mid y=110 -> lower y=144 -> riverbed y=184).
2. Fuselage incline traversal uphill and downhill under varying velocities.
3. Boss arena camera latch by crossing trigger x=3260 and retreating to x=2500.
4. 2000 continuous frames headless simulation under randomized input actions.
"""
import os
import sys
import random
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from src.config import (
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE,
    PLAYER_WALK_SPEED, SLUG_SPEED, GRAVITY
)

pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.engine.physics import Platform, PhysicsBody
from src.levels.mission1 import Mission1
from src.entities.player import Player
from src.entities.slug import MetalSlug
from src.core.camera import Camera
from src.game import Game, STATE_GAMEPLAY


class TestAdversarialMilestone1Challenger2(unittest.TestCase):

    def setUp(self):
        self.level = Mission1()

    # =========================================================================
    # 1. MULTI-TIER SCAFFOLDING TRAVERSAL STRESS TESTS
    # =========================================================================
    def test_adv_scaffolding_mid_to_lower_to_riverbed_clean_drop(self):
        """Stress Test 1.1: Drop from Mid (110) lands on Lower (144), then drop to Riverbed (184)."""
        body = PhysicsBody(x=3150, y=110, width=18, height=36)
        body.is_grounded = True
        mid_plat = [p for p in self.level.platforms if p.x1 <= 3150 <= p.x2 and p.y1 == 110][0]
        body.current_platform = mid_plat

        # Drop 1: Mid to Lower
        body.drop_through_platform()
        self.assertFalse(body.is_grounded)
        self.assertIs(body.ignored_platform, mid_plat)

        landed_lower = False
        for frame in range(30):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.is_grounded:
                landed_lower = True
                self.assertEqual(body.y, 144.0, f"Expected landing on Lower (144.0), got {body.y} at frame {frame}")
                self.assertEqual(body.current_platform.y1, 144.0)
                break

        self.assertTrue(landed_lower, "Failed to land on Lower platform after dropping from Mid")

        # Drop 2: Lower to Riverbed
        lower_plat = body.current_platform
        body.drop_through_platform()
        self.assertFalse(body.is_grounded)
        self.assertIs(body.ignored_platform, lower_plat)

        landed_riverbed = False
        for frame in range(30):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.is_grounded:
                landed_riverbed = True
                self.assertEqual(body.y, 198.0, f"Expected landing on Riverbed (198.0), got {body.y} at frame {frame}")
                self.assertEqual(body.current_platform.y1, 198.0)
                break

        self.assertTrue(landed_riverbed, "Failed to land on Riverbed after dropping from Lower")

    def test_adv_scaffolding_traversal_with_horizontal_velocities(self):
        """Stress Test 1.2: Drop through scaffolding tiers with varying horizontal velocities."""
        test_velocities = [-3.0, -1.75, -0.5, 0.0, 0.5, 1.75, 3.0]
        for vx in test_velocities:
            with self.subTest(vx=vx):
                body = PhysicsBody(x=3160, y=110, width=18, height=36)
                body.is_grounded = True
                body.vx = vx
                mid_plat = [p for p in self.level.platforms if p.x1 <= 3160 <= p.x2 and p.y1 == 110][0]
                body.current_platform = mid_plat

                body.drop_through_platform()
                body.vx = vx

                landed = False
                for _ in range(40):
                    body.apply_gravity()
                    body.update_movement(self.level.platforms)
                    if body.is_grounded:
                        landed = True
                        if 3100 <= body.x <= 3220 and body.y == 144.0:
                            # Landed on lower platform
                            pass
                        elif body.y == 198.0:
                            # Landed on riverbed
                            pass
                        else:
                            self.fail(f"Landed at unexpected y={body.y} at x={body.x} with vx={vx}")
                        break
                self.assertTrue(landed, f"Body never landed with vx={vx}")

    def test_adv_scaffolding_edge_boundary_drops(self):
        """Stress Test 1.3: Dropping at exact boundaries of Mid platform (x=3120, x=3200)."""
        mid_plat = [p for p in self.level.platforms if p.y1 == 110][0]

        for x in [3120.0, 3121.0, 3199.0, 3200.0]:
            with self.subTest(x=x):
                body = PhysicsBody(x=x, y=110, width=18, height=36)
                body.is_grounded = True
                body.current_platform = mid_plat
                body.drop_through_platform()

                landed = False
                for _ in range(30):
                    body.apply_gravity()
                    body.update_movement(self.level.platforms)
                    if body.is_grounded:
                        landed = True
                        self.assertEqual(body.y, 144.0, f"At x={x}, expected lower platform landing at y=144.0, got {body.y}")
                        break
                self.assertTrue(landed, f"Failed to land at boundary x={x}")

    def test_adv_scaffolding_jump_ascent_through_tiers(self):
        """Stress Test 1.4: Entity jumps upward from riverbed through Lower (144) and Mid (110)."""
        body = PhysicsBody(x=3150, y=184, width=18, height=36)
        body.is_grounded = False
        body.vy = -6.2  # Player jump impulse

        # Upward motion must not be blocked by semi-solid platforms
        for _ in range(15):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.vy < 0:
                self.assertFalse(body.is_grounded, "Semi-solid platform blocked upward jump trajectory")

    # =========================================================================
    # 2. FUSELAGE INCLINE TRAVERSAL (UPHILL AND DOWNHILL) STRESS TESTS
    # =========================================================================
    def test_adv_fuselage_empirical_ramp_step_on_defect(self):
        """Stress Test 2.1: Demonstrates that walking forward from riverbed (x=3370) into wing ramp (x=3380)
        FAILS to step onto the wing slope because riverbed Platform 18 precedes wing Platform 19 in platform order.
        """
        body = PhysicsBody(x=3370, y=184, width=18, height=36)
        body.is_grounded = True
        body.vx = PLAYER_WALK_SPEED  # 1.75

        for frame in range(30):
            body.apply_gravity()
            body.update_movement(self.level.platforms)

        # After 30 frames at vx=1.75, x = 3370 + 52.5 = 3422.5 (deep into wing slope x=3380..3540)
        # Expected authentic arcade behavior: entity climbs wing slope (at x=3422.5, wing y is ~172.8).
        # Actual buggy behavior: entity stays at y=198.0 on riverbed under the plane.
        wing_plat = [p for p in self.level.platforms if p.x1 == 3380 and p.y2 == 142][0]
        expected_wing_y = wing_plat.get_height_at(body.x)

        # Document exact observed defect
        self.assertEqual(body.y, 198.0, "Entity remained on riverbed under the plane")
        self.assertNotEqual(body.y, expected_wing_y, "Entity failed to climb wing slope")

    def test_adv_fuselage_downhill_walking_on_wing(self):
        """Stress Test 2.2: Walking downhill along wing slope towards riverbed."""
        wing = [p for p in self.level.platforms if p.x1 == 3380 and p.y2 == 142][0]
        body = PhysicsBody(x=3450, y=wing.get_height_at(3450), width=18, height=36)
        body.is_grounded = True
        body.current_platform = wing
        body.vx = -PLAYER_WALK_SPEED

        # Walk downhill until reaching riverbed
        for _ in range(50):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            self.assertTrue(body.is_grounded, f"Entity detached on downhill walk at x={body.x}, y={body.y}")

        self.assertLess(body.x, 3380.0)
        self.assertEqual(body.y, 198.0, "Entity should transition onto riverbed at y=184")

    def test_adv_fuselage_drop_through_wing_and_cockpit(self):
        """Stress Test 2.3: Dropping through wing slope and cockpit slope reaches riverbed at y=184."""
        # Wing slope midpoint: x = 3460
        body = PhysicsBody(x=3460, y=163.0, width=18, height=36)
        body.is_grounded = True
        wing = [p for p in self.level.platforms if p.x1 <= 3460 <= p.x2 and p.semi_solid][0]
        body.current_platform = wing
        body.drop_through_platform()

        for _ in range(30):
            body.apply_gravity()
            body.update_movement(self.level.platforms)
            if body.is_grounded:
                break
        self.assertTrue(body.is_grounded)
        self.assertEqual(body.y, 198.0, f"Expected riverbed at 198.0, got {body.y}")

        # Cockpit slope midpoint: x = 3620
        body2 = PhysicsBody(x=3620, y=127.0, width=18, height=36)
        body2.is_grounded = True
        cockpit = [p for p in self.level.platforms if p.x1 <= 3620 <= p.x2 and p.semi_solid][0]
        body2.current_platform = cockpit
        body2.drop_through_platform()

        for _ in range(40):
            body2.apply_gravity()
            body2.update_movement(self.level.platforms)
            if body2.is_grounded:
                break
        self.assertTrue(body2.is_grounded)
        self.assertEqual(body2.y, 198.0, f"Expected riverbed at 198.0, got {body2.y}")

    def test_adv_fuselage_high_velocity_ascent_detachment(self):
        """Stress Test 2.4: Entity ascending wing slope at high velocity (e.g. Kamikaze Slug vx=6.0).
        Demonstrates that when vx * slope > 1.0 (vx > 3.81), old_y <= plat_y + 1 fails,
        causing fast entities to detach from the slope and become airborne.
        """
        wing = [p for p in self.level.platforms if p.x1 == 3380 and p.y2 == 142][0]
        # Test speeds
        body_normal = PhysicsBody(x=3400, y=wing.get_height_at(3400), width=18, height=36)
        body_normal.is_grounded = True
        body_normal.vx = 2.0  # normal speed
        body_normal.apply_gravity()
        body_normal.update_movement([wing])
        self.assertTrue(body_normal.is_grounded, "Normal speed should remain grounded")

        body_fast = PhysicsBody(x=3400, y=wing.get_height_at(3400), width=18, height=36)
        body_fast.is_grounded = True
        body_fast.vx = 6.0  # Kamikaze speed
        body_fast.apply_gravity()
        body_fast.update_movement([wing])
        # Delta plat_y = 6.0 * (42/160) = 1.575 > 1.0, so old_y <= plat_y + 1 fails
        self.assertFalse(body_fast.is_grounded, "Fast entity (vx=6.0) detaches from slope due to 1.0px tolerance limit")

    # =========================================================================
    # 3. BOSS ARENA CAMERA LATCH STRESS TESTS
    # =========================================================================
    def test_adv_boss_camera_latch_retreat_to_x2500_level_isolation(self):
        """Stress Test 3.1: Cross trigger x=3260, retreat to x=2500, verify lock persists until boss defeat."""
        camera = Camera()
        player = Player(x=3200, y=184)
        enemy_projectiles = []

        # 1. Approach trigger: x = 3250
        player.physics.x = 3250
        self.level.update(player, camera, enemy_projectiles=enemy_projectiles)
        self.assertFalse(self.level._boss_locked, "Boss should not be locked before x=3260")
        self.assertFalse(camera.is_locked, "Camera should not be locked before x=3260")

        # 2. Cross trigger: x = 3260
        player.physics.x = 3260
        self.level.update(player, camera, enemy_projectiles=enemy_projectiles)
        self.assertTrue(self.level._boss_locked, "Boss lock latch must engage at x=3260")
        self.assertTrue(camera.is_locked, "Camera must lock at x=3260")
        self.assertEqual(camera.x, 3260.0, f"Camera x should be 3260.0, got {camera.x}")
        self.assertEqual(camera.lock_x, 3260.0)

        # 3. Advance further into arena: x = 3450
        player.physics.x = 3450
        self.level.update(player, camera, enemy_projectiles=enemy_projectiles)
        self.assertTrue(camera.is_locked)
        self.assertEqual(camera.x, 3260.0)

        # 4. Retreat backward to x = 2500 (deep into Valley Path)
        player.physics.x = 2500.0
        for retreat_frame in range(50):
            self.level.update(player, camera, enemy_projectiles=enemy_projectiles)
            self.assertTrue(
                self.level._boss_locked,
                f"Boss lock disengaged at retreat frame {retreat_frame} when player at x=2500"
            )
            self.assertTrue(
                camera.is_locked,
                f"Camera unlocked at retreat frame {retreat_frame} when player at x=2500"
            )
            self.assertEqual(camera.x, 3260.0)
            self.assertEqual(camera.lock_x, 3260.0)

        # 5. Defeat boss -> Camera must unlock
        self.level.boss.is_defeated = True
        self.level.boss.defeat_timer = 0
        self.level.update(player, camera, enemy_projectiles=enemy_projectiles)
        self.assertFalse(self.level._boss_locked, "Boss lock must disengage when boss is defeated")
        self.assertFalse(camera.is_locked, "Camera must unlock when boss is defeated")
        self.assertTrue(self.level.is_encounter_cleared, "Encounter must be marked cleared")

    def test_adv_boss_missing_enemy_projectiles_attribute_error(self):
        """Stress Test 3.2: Calling level.update(player, camera) with default enemy_projectiles=None
        triggers AttributeError when boss fires projectiles (attack cooldown 90 frames).
        """
        camera = Camera()
        player = Player(x=3300, y=184)
        crashed = False
        for _ in range(100):
            try:
                self.level.update(player, camera)  # enemy_projectiles defaulted to None
            except AttributeError as e:
                crashed = True
                self.assertIn("'NoneType' object has no attribute 'append'", str(e))
                break
        self.assertTrue(crashed, "Expected AttributeError when updating level without enemy_projectiles")

    def test_adv_game_loop_camera_scroll_retreat_clamp(self):
        """Stress Test 3.3: In full Game loop, when player reaches x=3380 (so camera reaches 3260),
        attempting to retreat backward holding ACTION_LEFT clamps player at x=3269.0 (camera.x + 9).
        """
        game = Game()
        game.start_new_campaign("marco")

        game.player.physics.x = 3370
        game.camera.x = 3250
        game.camera.max_scrolled_x = 3250
        game.input_manager.current_state[ACTION_RIGHT] = True

        # Reach arena
        for _ in range(20):
            game.update()
            if game.player.physics.x >= 3380:
                break

        self.assertEqual(game.camera.x, 3260.0)
        self.assertTrue(game.camera.is_locked)

        # Retreat
        game.input_manager.current_state[ACTION_RIGHT] = False
        game.input_manager.current_state[ACTION_LEFT] = True

        for _ in range(100):
            game.update()

        # Clamped at 3269.0
        self.assertEqual(game.camera.x, 3260.0)
        self.assertEqual(game.player.physics.x, 3269.0)

    # =========================================================================
    # 4. 2000-FRAME CONTINUOUS HEADLESS SIMULATION
    # =========================================================================
    def test_adv_2000_frames_randomized_movement_simulation(self):
        """Stress Test 4.1: 2000 continuous frames headless simulation under randomized movement inputs (no shooting).
        Verifies physics stability, ground adherence, camera bounds, and zero unhandled exceptions.
        """
        game = Game()
        game.start_new_campaign("marco")

        movement_actions = [ACTION_RIGHT, ACTION_LEFT, ACTION_UP, ACTION_DOWN, ACTION_JUMP]

        random.seed(42)
        crashes = []
        bounds_violations = []

        for frame in range(2000):
            if frame % 4 == 0:
                for act in movement_actions:
                    game.input_manager.current_state[act] = (random.random() < 0.35)
                # Ensure forward campaign progression
                if random.random() < 0.7:
                    game.input_manager.current_state[ACTION_RIGHT] = True

            try:
                game.update()
            except Exception as e:
                import traceback
                crashes.append((frame, str(e), traceback.format_exc()))
                break

            px = game.player.physics.x
            py = game.player.physics.y
            cx = game.camera.x

            if py > 230:
                bounds_violations.append((frame, f"Player fell through world: y={py} at x={px}"))
                break
            if py < -50:
                bounds_violations.append((frame, f"Player launched into sky: y={py} at x={px}"))
                break
            if cx < 0 or cx > 4153:
                bounds_violations.append((frame, f"Camera out of bounds: cx={cx}"))
                break

        self.assertEqual(crashes, [], f"Movement simulation crashed: {crashes}")
        self.assertEqual(bounds_violations, [], f"Bounds violations: {bounds_violations}")

    def test_adv_2000_frames_combat_flameshot_crash_defect(self):
        """Stress Test 4.2: Demonstrates the combat simulation crash in game.py:306 when firing FlameShot.
        FlameShotBall.update expects (platforms, camera) while game.py:306 calls b.update(self.camera),
        causing TypeError: 'Camera' object is not iterable.
        """
        from src.weapons.special_weapons import FlameShotBall
        game = Game()
        game.start_new_campaign("marco")

        # Simulate player picking up and firing FlameShot
        flame = FlameShotBall(x=game.player.physics.x + 20, y=game.player.physics.y - 16, facing_right=True)
        game.player_projectiles.append(flame)

        # Calling game.update() executes lines 300-306 in game.py
        crashed = False
        try:
            game.update()
        except TypeError as e:
            crashed = True
            self.assertIn("'Camera' object is not iterable", str(e))

        self.assertTrue(crashed, "Expected TypeError: 'Camera' object is not iterable when updating FlameShot")



if __name__ == "__main__":
    unittest.main(verbosity=2)
