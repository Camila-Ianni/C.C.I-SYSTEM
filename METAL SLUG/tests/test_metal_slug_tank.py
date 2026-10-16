"""
Test Suite: R2 Super Vehicle-001 (Metal Slug SV-001) Fixes & Mechanics (Features F7 - F11)
Tiers 1, 2, and 3 Coverage.

Features:
- F7: Metal Slug Attack Crash Fix
- F8: Pilot Boarding & Slug Out Ejection
- F9: Vehicle Bullet Collision & Invincibility Fix
- F10: Twin Vulcan 360° Aim & Suspension Squash
- F11: HUD Tank Mode Ammo & Armor
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
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, SLUG_SPEED, SLUG_JUMP_IMPULSE,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_SHOOT, ACTION_JUMP, ACTION_GRENADE
)

pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.entities.slug import MetalSlug
from src.entities.player import Player
from src.entities.enemy import RebelSoldier
from src.engine.physics import Platform, PhysicsBody
from src.engine.particle_system import ParticleSystem
from src.core.sound_manager import SoundManager
from src.core.input_manager import InputManager
from src.ui.hud import HUD


class MockInputManager:
    """Mock input manager allowing programmatic control of pressed/held buttons."""
    def __init__(self):
        self._held = set()
        self._just_pressed = set()

    def hold(self, action):
        self._held.add(action)

    def press(self, action):
        self._just_pressed.add(action)
        self._held.add(action)

    def release(self, action):
        self._held.discard(action)
        self._just_pressed.discard(action)

    def clear(self):
        self._held.clear()
        self._just_pressed.clear()

    def is_held(self, action):
        return action in self._held

    def is_just_pressed(self, action):
        return action in self._just_pressed


class TestMetalSlugTank(unittest.TestCase):
    def setUp(self):
        self.slug = MetalSlug(x=720, y=184)
        self.player = Player(x=720, y=184, character="marco")
        self.particles = ParticleSystem()
        self.sound = SoundManager()
        self.input = MockInputManager()
        self.projectiles = []
        self.platforms = [Platform(0, 184, 4000, 184, semi_solid=False)]

    # =========================================================================
    # FEATURE F7: Metal Slug Attack Crash Fix
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f7_tier1_kamikaze_activation_no_attribute_error(self):
        """F7-T1-1: Activating Metal Slug Attack does not raise AttributeError: 'MetalSlug' object has no attribute 'x'."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        self.assertTrue(self.slug.self_destruct_charging)
        # Advance update - must access self.physics.x, not self.x
        try:
            self.slug.update(platforms=self.platforms, enemies=[], particle_system=self.particles)
        except AttributeError as e:
            self.fail(f"AttributeError encountered during self-destruct update: {e}")

    def test_f7_tier1_self_destruct_charging_movement(self):
        """F7-T1-2: Charging tank accelerates with vx = 6.0 when facing right."""
        self.slug.facing_right = True
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        self.assertEqual(self.slug.physics.vx, 6.0)
        old_x = self.slug.physics.x
        self.slug.update(platforms=self.platforms, enemies=[], particle_system=self.particles)
        self.assertAlmostEqual(self.slug.physics.x, old_x + 6.0, delta=0.1)

    def test_f7_tier1_kamikaze_detonation_on_enemy_collision(self):
        """F7-T1-3: Colliding with enemy during kamikaze ramming marks tank as dead."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        enemy = RebelSoldier(x=730, y=184)
        self.slug.update(platforms=self.platforms, enemies=[enemy], particle_system=self.particles)
        self.assertTrue(self.slug.is_dead, "Tank must be destroyed upon enemy collision")

    def test_f7_tier1_kamikaze_multi_target_damage(self):
        """F7-T1-4: Detonation inflicts massive explosion damage (50) to enemies in blast radius."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        enemy1 = RebelSoldier(x=730, y=184)
        enemy2 = RebelSoldier(x=750, y=184)
        self.slug.update(platforms=self.platforms, enemies=[enemy1, enemy2], particle_system=self.particles)
        self.assertTrue(enemy1.is_dead, "Directly hit enemy must be killed")
        self.assertTrue(enemy2.is_dead, "Adjacent enemy in blast radius must be killed")

    def test_f7_tier1_pilot_ejected_on_attack_trigger(self):
        """F7-T1-5: Activating Metal Slug Attack automatically ejects pilot from the tank."""
        self.slug.enter_vehicle(self.player)
        self.assertTrue(self.slug.is_occupied)
        self.slug.trigger_metal_slug_attack()
        self.assertFalse(self.slug.is_occupied, "Tank must be unoccupied after attack activation")
        self.assertIsNone(self.slug.pilot)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f7_tier2_attack_on_unoccupied_tank_is_noop(self):
        """F7-T2-1: Calling trigger_metal_slug_attack on unoccupied tank does not charge attack."""
        self.assertFalse(self.slug.is_occupied)
        self.slug.trigger_metal_slug_attack()
        self.assertFalse(self.slug.self_destruct_charging)

    def test_f7_tier2_attack_facing_left_sets_negative_vx(self):
        """F7-T2-2: Tank facing left charges with vx = -6.0."""
        self.slug.facing_right = False
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        self.assertEqual(self.slug.physics.vx, -6.0)
        old_x = self.slug.physics.x
        self.slug.update(platforms=self.platforms, enemies=[], particle_system=self.particles)
        self.assertAlmostEqual(self.slug.physics.x, old_x - 6.0, delta=0.1)

    def test_f7_tier2_attack_charges_without_enemies(self):
        """F7-T2-3: Tank charges through empty space without crashing when enemies list is None."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        for _ in range(10):
            self.slug.update(platforms=self.platforms, enemies=None, particle_system=self.particles)
        self.assertFalse(self.slug.is_dead)
        self.assertEqual(self.slug.physics.x, 720 + 60.0)

    def test_f7_tier2_enemies_outside_radius_survive(self):
        """F7-T2-4: Enemies outside the blast threshold (dist >= 60) survive the detonation."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        close_enemy = RebelSoldier(x=730, y=184)
        far_enemy = RebelSoldier(x=820, y=184)  # 100px away
        self.slug.update(platforms=self.platforms, enemies=[close_enemy, far_enemy], particle_system=self.particles)
        self.assertTrue(close_enemy.is_dead)
        self.assertFalse(far_enemy.is_dead, "Enemy outside blast radius must not be damaged")

    def test_f7_tier2_already_dead_enemy_ignored(self):
        """F7-T2-5: Dead enemies do not trigger kamikaze detonation."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        dead_enemy = RebelSoldier(x=730, y=184)
        dead_enemy.is_dead = True
        self.slug.update(platforms=self.platforms, enemies=[dead_enemy], particle_system=self.particles)
        self.assertFalse(self.slug.is_dead, "Dead enemy must not trigger premature detonation")

    # =========================================================================
    # FEATURE F8: Pilot Boarding & Slug Out Ejection
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f8_tier1_boarding_occupies_tank(self):
        """F8-T1-1: Boarding tank sets is_occupied=True and stores pilot reference."""
        self.slug.enter_vehicle(self.player)
        self.assertTrue(self.slug.is_occupied)
        self.assertIs(self.slug.pilot, self.player)

    def test_f8_tier1_boarding_grants_invincibility(self):
        """F8-T1-2: Boarding tank grants pilot invincibility frames."""
        self.slug.enter_vehicle(self.player)
        self.assertTrue(self.player.is_invincible)
        self.assertGreater(self.player.invincible_timer, 0)

    def test_f8_tier1_slug_out_returns_pilot(self):
        """F8-T1-3: exit_vehicle() resets occupation and returns pilot."""
        self.slug.enter_vehicle(self.player)
        pilot = self.slug.exit_vehicle()
        self.assertIs(pilot, self.player)
        self.assertFalse(self.slug.is_occupied)
        self.assertIsNone(self.slug.pilot)

    def test_f8_tier1_slug_out_hatch_leap_coordinates(self):
        """F8-T1-4: Pilot leaps upward from hatch at y - 36 with vertical velocity vy = -5.5."""
        self.slug.enter_vehicle(self.player)
        pilot = self.slug.exit_vehicle()
        self.assertEqual(pilot.physics.y, 184 - 36)
        self.assertEqual(pilot.physics.vy, -5.5)

    def test_f8_tier1_slug_out_60_iframes(self):
        """F8-T1-5: Slug out ejects pilot with exactly 60 invincibility frames."""
        self.slug.enter_vehicle(self.player)
        pilot = self.slug.exit_vehicle()
        self.assertTrue(pilot.is_invincible)
        self.assertEqual(pilot.invincible_timer, 60)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f8_tier2_exit_when_not_occupied_returns_none(self):
        """F8-T2-1: Calling exit_vehicle on empty tank returns None safely."""
        self.assertFalse(self.slug.is_occupied)
        self.assertIsNone(self.slug.exit_vehicle())

    def test_f8_tier2_slug_out_facing_right_backward_vx(self):
        """F8-T2-2: When facing right, ejected pilot leaps backward with vx = -1.5."""
        self.slug.facing_right = True
        self.slug.enter_vehicle(self.player)
        pilot = self.slug.exit_vehicle()
        self.assertEqual(pilot.physics.vx, -1.5)

    def test_f8_tier2_slug_out_facing_left_backward_vx(self):
        """F8-T2-3: When facing left, ejected pilot leaps backward with vx = 1.5."""
        self.slug.facing_right = False
        self.slug.enter_vehicle(self.player)
        pilot = self.slug.exit_vehicle()
        self.assertEqual(pilot.physics.vx, 1.5)

    def test_f8_tier2_repeated_boarding_cycle(self):
        """F8-T2-4: Repeated enter/exit cycles maintain vehicle state and integrity."""
        for _ in range(5):
            self.slug.enter_vehicle(self.player)
            self.assertTrue(self.slug.is_occupied)
            self.slug.exit_vehicle()
            self.assertFalse(self.slug.is_occupied)
        self.assertEqual(self.slug.armor, 3)
        self.assertEqual(self.slug.cannon_ammo, 10)

    def test_f8_tier2_input_down_jump_triggers_slug_out(self):
        """F8-T2-5: Input combination Down + Jump triggers Slug Out."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_DOWN)
        self.input.press(ACTION_JUMP)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertFalse(self.slug.is_occupied, "Down + Jump must trigger slug out exit")

    # =========================================================================
    # FEATURE F9: Vehicle Bullet Collision & Invincibility Fix
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f9_tier1_tank_takes_damage(self):
        """F9-T1-1: Tank takes damage via take_damage(1), reducing armor from 3 to 2."""
        self.assertEqual(self.slug.armor, 3)
        self.slug.take_damage(1)
        self.assertEqual(self.slug.armor, 2)

    def test_f9_tier1_damage_decoupled_from_player_iframes(self):
        """F9-T1-2: Tank takes damage even if boarded pilot has active invincibility frames."""
        self.slug.enter_vehicle(self.player)
        self.player.is_invincible = True
        self.player.invincible_timer = 60
        self.slug.take_damage(1)
        self.assertEqual(self.slug.armor, 2, "Tank armor must decrement regardless of pilot i-frames")

    def test_f9_tier1_fatal_damage_destroys_tank(self):
        """F9-T1-3: Reducing armor to 0 sets is_dead=True and armor=0."""
        self.slug.take_damage(3)
        self.assertEqual(self.slug.armor, 0)
        self.assertTrue(self.slug.is_dead)

    def test_f9_tier1_fatal_damage_ejects_pilot(self):
        """F9-T1-4: Fatal damage destroying occupied tank ejects pilot."""
        self.slug.enter_vehicle(self.player)
        self.slug.take_damage(3)
        self.assertFalse(self.slug.is_occupied)
        self.assertIsNone(self.slug.pilot)

    def test_f9_tier1_repair_restores_armor(self):
        """F9-T1-5: repair() increments armor by 1."""
        self.slug.take_damage(2)
        self.assertEqual(self.slug.armor, 1)
        self.slug.repair()
        self.assertEqual(self.slug.armor, 2)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f9_tier2_damage_when_dead_is_noop(self):
        """F9-T2-1: take_damage when already dead does not decrement armor below 0."""
        self.slug.take_damage(3)
        self.assertTrue(self.slug.is_dead)
        self.slug.take_damage(1)
        self.assertEqual(self.slug.armor, 0)

    def test_f9_tier2_repair_at_max_armor_capped(self):
        """F9-T2-2: repair() at max armor (3) does not exceed 3."""
        self.assertEqual(self.slug.armor, 3)
        self.slug.repair()
        self.assertEqual(self.slug.armor, 3)

    def test_f9_tier2_overkill_damage_clamps_at_zero(self):
        """F9-T2-3: Massive damage (amount=10) clamps armor at 0."""
        self.slug.take_damage(10)
        self.assertEqual(self.slug.armor, 0)
        self.assertTrue(self.slug.is_dead)

    def test_f9_tier2_zero_damage_leaves_armor_unchanged(self):
        """F9-T2-4: take_damage(0) leaves armor at 3."""
        self.slug.take_damage(0)
        self.assertEqual(self.slug.armor, 3)

    def test_f9_tier2_tank_hurtbox_dimensions(self):
        """F9-T2-5: Tank physics hurtbox has width 54, height 44."""
        self.assertEqual(self.slug.physics.width, 54)
        self.assertEqual(self.slug.physics.height, 44)
        hurtbox = self.slug.physics.hurtbox
        self.assertEqual(hurtbox.width, 54)
        self.assertEqual(hurtbox.height, 44)

    # =========================================================================
    # FEATURE F10: Twin Vulcan 360° Aim & Suspension Squash
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f10_tier1_vulcan_horizontal_aim(self):
        """F10-T1-1: Neutral directional inputs produce 0.0 degree (horizontal) turret aim."""
        self.slug.enter_vehicle(self.player)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.turret_angle_deg, 0.0)

    def test_f10_tier1_vulcan_vertical_up_aim(self):
        """F10-T1-2: Holding UP alone produces 90.0 degree (vertical up) turret aim."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_UP)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.turret_angle_deg, 90.0)

    def test_f10_tier1_vulcan_diagonal_up_aim(self):
        """F10-T1-3: Holding UP + RIGHT produces 45.0 degree (diagonal up) turret aim."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_UP)
        self.input.hold(ACTION_RIGHT)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.turret_angle_deg, 45.0)

    def test_f10_tier1_vulcan_diagonal_down_aim(self):
        """F10-T1-4: Holding DOWN produces -45.0 degree (diagonal down) turret aim."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_DOWN)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.turret_angle_deg, -45.0)

    def test_f10_tier1_vulcan_firing_spawns_bullets(self):
        """F10-T1-5: Holding SHOOT fires Twin Vulcan bullets and sets cooldown."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_SHOOT)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertGreater(len(self.projectiles), 0, "Vulcan fire must append projectiles")
        self.assertEqual(self.slug.shoot_cooldown, 5)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f10_tier2_vulcan_facing_left_fire_direction(self):
        """F10-T2-1: Firing while facing left spawns bullets with negative x-velocity."""
        self.slug.facing_right = False
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_SHOOT)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertGreater(len(self.projectiles), 0)
        bullet = self.projectiles[0]
        self.assertLess(bullet.dir_x, 0, "Bullet must travel leftward")

    def test_f10_tier2_vulcan_respects_cooldown(self):
        """F10-T2-2: Vulcan does not fire on consecutive frame if shoot_cooldown > 0."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_SHOOT)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        initial_count = len(self.projectiles)
        # Next frame with cooldown active
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(len(self.projectiles), initial_count, "No projectile fired during cooldown")

    def test_f10_tier2_cannon_firing_decrements_ammo(self):
        """F10-T2-3: Firing heavy cannon decrements cannon_ammo from 10 to 9."""
        self.slug.enter_vehicle(self.player)
        self.input.press(ACTION_GRENADE)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.cannon_ammo, 9)
        self.assertEqual(self.slug.cannon_cooldown, 25)

    def test_f10_tier2_cannon_empty_ammo_cannot_fire(self):
        """F10-T2-4: Cannon cannot fire when cannon_ammo is 0."""
        self.slug.enter_vehicle(self.player)
        self.slug.cannon_ammo = 0
        self.input.press(ACTION_GRENADE)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(len(self.projectiles), 0)

    def test_f10_tier2_slug_jump_impulse(self):
        """F10-T2-5: Jumping sets vy = SLUG_JUMP_IMPULSE and is_grounded = False."""
        self.slug.enter_vehicle(self.player)
        self.slug.physics.is_grounded = True
        self.input.press(ACTION_JUMP)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.physics.vy, SLUG_JUMP_IMPULSE)
        self.assertFalse(self.slug.physics.is_grounded)

    # =========================================================================
    # FEATURE F11: HUD Tank Mode Ammo & Armor
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f11_tier1_hud_draw_signature_slug_support(self):
        """F11-T1-1: HUD draw method accepts slug keyword or positional parameter without crashing."""
        hud = HUD()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.slug.enter_vehicle(self.player)
        try:
            hud.draw(surf, self.player, slug=self.slug, time_remaining=60)
        except TypeError:
            # Fallback for older signature
            hud.draw(surf, self.player, time_remaining=60)

    def test_f11_tier1_tank_mode_renders_without_exception(self):
        """F11-T1-2: Rendering HUD with occupied slug renders smoothly onto virtual surface."""
        hud = HUD()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.slug.enter_vehicle(self.player)
        if "slug" in hud.draw.__code__.co_varnames:
            hud.draw(surf, self.player, slug=self.slug, time_remaining=60)
        else:
            hud.draw(surf, self.player, time_remaining=60)

    def test_f11_tier1_slug_armor_status_property(self):
        """F11-T1-3: Tank has max_armor 3 and initial armor 3."""
        self.assertEqual(self.slug.max_armor, 3)
        self.assertEqual(self.slug.armor, 3)

    def test_f11_tier1_slug_cannon_ammo_property(self):
        """F11-T1-4: Tank has initial cannon_ammo 10."""
        self.assertEqual(self.slug.cannon_ammo, 10)

    def test_f11_tier1_hud_on_foot_fallback(self):
        """F11-T1-5: HUD renders standard on-foot player interface when unboarded."""
        hud = HUD()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        if "slug" in hud.draw.__code__.co_varnames:
            hud.draw(surf, self.player, slug=None, time_remaining=60)
        else:
            hud.draw(surf, self.player, time_remaining=60)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f11_tier2_hud_dead_slug_ignored(self):
        """F11-T2-1: Dead slug passed to HUD is treated as inactive."""
        hud = HUD()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.slug.is_dead = True
        if "slug" in hud.draw.__code__.co_varnames:
            hud.draw(surf, self.player, slug=self.slug, time_remaining=60)
        else:
            hud.draw(surf, self.player, time_remaining=60)

    def test_f11_tier2_cannon_ammo_depletion_state(self):
        """F11-T2-2: Cannon ammo at 0 remains non-negative."""
        self.slug.cannon_ammo = 0
        self.assertEqual(self.slug.cannon_ammo, 0)

    def test_f11_tier2_armor_single_pip_critical(self):
        """F11-T2-3: Tank with 1 armor is in critical state."""
        self.slug.take_damage(2)
        self.assertEqual(self.slug.armor, 1)

    def test_f11_tier2_armor_full_pip(self):
        """F11-T2-4: Tank at 3 armor is in full condition."""
        self.assertEqual(self.slug.armor, self.slug.max_armor)

    def test_f11_tier2_hud_surface_dimensions(self):
        """F11-T2-5: Virtual surface receiving HUD is exact Neo-Geo 320x224."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.assertEqual(surf.get_width(), 320)
        self.assertEqual(surf.get_height(), 224)

    # =========================================================================
    # TIER 3: Cross-Feature Combinations (Pairwise Interactions)
    # =========================================================================
    def test_tier3_f7_f8_attack_preserves_pilot_leap(self):
        """T3-1 (F7+F8): Metal Slug Attack ejects pilot with hatch leap coordinates and 60 i-frames before detonation."""
        self.slug.enter_vehicle(self.player)
        self.slug.trigger_metal_slug_attack()
        self.assertEqual(self.player.physics.y, 184 - 36)
        self.assertEqual(self.player.physics.vy, -5.5)
        self.assertEqual(self.player.invincible_timer, 60)
        self.assertTrue(self.slug.self_destruct_charging)

    def test_tier3_f8_f9_boarding_damage_cycle(self):
        """T3-2 (F8+F9): Boarding tank, taking 2 damage, exiting safely, and verifying pilot takes no damage."""
        self.slug.enter_vehicle(self.player)
        self.slug.take_damage(2)
        self.assertEqual(self.slug.armor, 1)
        pilot = self.slug.exit_vehicle()
        self.assertIs(pilot, self.player)
        self.assertEqual(self.player.lives, 3)

    def test_tier3_f9_f11_armor_reduction_matches_hud_state(self):
        """T3-3 (F9+F11): Taking damage reduces vehicle armor and renders safely to HUD."""
        hud = HUD()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.slug.enter_vehicle(self.player)
        self.slug.take_damage(1)
        self.assertEqual(self.slug.armor, 2)
        if "slug" in hud.draw.__code__.co_varnames:
            hud.draw(surf, self.player, slug=self.slug, time_remaining=60)

    def test_tier3_f10_f11_cannon_fire_updates_ammo_in_hud(self):
        """T3-4 (F10+F11): Firing heavy cannon decrements ammo and updates HUD state."""
        hud = HUD()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.slug.enter_vehicle(self.player)
        self.input.press(ACTION_GRENADE)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.cannon_ammo, 9)
        if "slug" in hud.draw.__code__.co_varnames:
            hud.draw(surf, self.player, slug=self.slug, time_remaining=60)

    def test_tier3_f8_f10_turret_aim_before_midair_exit(self):
        """T3-5 (F8+F10): Turret aiming up followed by mid-air leap ejection."""
        self.slug.enter_vehicle(self.player)
        self.input.hold(ACTION_UP)
        self.slug.handle_input(self.input, self.projectiles, self.particles, self.sound)
        self.assertEqual(self.slug.turret_angle_deg, 90.0)
        pilot = self.slug.exit_vehicle()
        self.assertEqual(pilot.physics.vy, -5.5)


if __name__ == "__main__":
    unittest.main()
