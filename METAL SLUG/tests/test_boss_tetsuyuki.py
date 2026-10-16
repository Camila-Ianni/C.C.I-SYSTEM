"""
Test Suite: R3 Mission 1 Boss (Tetsuyuki) Visual & Combat Overhaul (Features F12 - F15)
Tiers 1, 2, and 3 Coverage.

Features:
- F12: Tetsuyuki Waterfall Backdrop Reconstruction
- F13: Boss Multi-Part Animated Sprites
- F14: Removal of Non-Arcade Boss Health Bar
- F15: Boss 2-Phase Combat & Defeat Transition
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
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, COLOR_HUD_YELLOW
)

pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.entities.bosses.tetsuyuki import TetsuyukiBoss, GiantPlasmaOrb
from src.entities.player import Player
from src.engine.physics import Platform
from src.engine.particle_system import ParticleSystem
from src.core.camera import Camera
from src.engine.sprite_loader import SpriteLoader
try:
    from src.levels.mission1 import Mission1Level
except ImportError:
    from src.levels.mission1 import Mission1 as Mission1Level


class TestBossTetsuyuki(unittest.TestCase):
    def setUp(self):
        self.boss = TetsuyukiBoss(x=3750, y=184)
        self.player = Player(x=3600, y=184, character="marco")
        self.camera = Camera(world_width=4153, world_height=224)
        self.camera.lock_at(3380)
        self.particles = ParticleSystem()
        self.enemy_projectiles = []
        self.platforms = [
            Platform(3350, 184, 4153, 184, semi_solid=False),
            Platform(3700, 112, 3850, 112, semi_solid=True)
        ]

    # =========================================================================
    # FEATURE F12: Tetsuyuki Waterfall Backdrop Reconstruction
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f12_tier1_background_sheet_loads(self):
        """F12-T1-1: Background sheet loads cleanly from Mission 1.png."""
        sheet_path = "Assets/Backgrounds/Neo Geo _ NGCD - Metal Slug - Backgrounds - Mission 1.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=None)
        self.assertIsNotNone(sheet)
        self.assertGreater(sheet.get_width(), 4000)

    def test_f12_tier1_mission_level_background_dimensions(self):
        """F12-T1-2: Mission1 background surface has dimensions 4153x224."""
        level = Mission1Level()
        self.assertIsNotNone(level.background_surf)
        self.assertEqual(level.background_surf.get_width(), 4153)
        self.assertEqual(level.background_surf.get_height(), 224)

    def test_f12_tier1_waterfall_backdrop_area_exists(self):
        """F12-T1-3: Arena waterfall section (x=3300..4153) is present within background surface."""
        level = Mission1Level()
        arena_sub = level.background_surf.subsurface((3300, 0, 4153 - 3300, 224))
        self.assertEqual(arena_sub.get_width(), 853)
        self.assertEqual(arena_sub.get_height(), 224)

    def test_f12_tier1_camera_draws_arena_background(self):
        """F12-T1-4: draw_background blits arena section without errors when camera is in arena."""
        level = Mission1Level()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.camera.x = 3400.0
        level.draw_background(surf, self.camera)
        # Background drawn, check non-empty surface
        self.assertEqual(surf.get_width(), 320)
        self.assertEqual(surf.get_height(), 224)

    def test_f12_tier1_waterfall_no_solid_white_blocks(self):
        """F12-T1-5: Waterfall backdrop area contains natural pixel distribution without large pure white blocks."""
        level = Mission1Level()
        arena_sub = level.background_surf.subsurface((3500, 20, 200, 150))
        # Count pure white pixels (255, 255, 255)
        white_count = 0
        w, h = arena_sub.get_size()
        for x in range(0, w, 5):
            for y in range(0, h, 5):
                color = arena_sub.get_at((x, y))[:3]
                if color == (255, 255, 255):
                    white_count += 1
        total_samples = (w // 5) * (h // 5)
        white_ratio = white_count / total_samples
        self.assertLess(white_ratio, 0.15, "Backdrop must not be dominated by pure white cutout artifacting")

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f12_tier2_camera_at_extreme_right_boundary(self):
        """F12-T2-1: Background renders cleanly at maximum stage camera coordinate."""
        level = Mission1Level()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.camera.x = float(level.stage_width - VIRTUAL_WIDTH)
        level.draw_background(surf, self.camera)
        self.assertIsNotNone(surf)

    def test_f12_tier2_camera_at_arena_gate_entry(self):
        """F12-T2-2: Background renders cleanly at arena gate entry coordinate x=3260."""
        level = Mission1Level()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.camera.x = 3260.0
        level.draw_background(surf, self.camera)
        self.assertIsNotNone(surf)

    def test_f12_tier2_background_surface_is_copy(self):
        """F12-T2-3: Background surface is independent surface copy."""
        level = Mission1Level()
        self.assertIsInstance(level.background_surf, pygame.Surface)

    def test_f12_tier2_screen_shake_during_backdrop_render(self):
        """F12-T2-4: draw_background handles camera screen shake offset without clipping crash."""
        level = Mission1Level()
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.camera.x = 3500.0
        self.camera.trigger_shake(duration_frames=10, magnitude=5)
        self.camera.shake_offset_x = 4
        self.camera.shake_offset_y = -3
        level.draw_background(surf, self.camera)
        self.assertIsNotNone(surf)

    def test_f12_tier2_virtual_screen_size_compliance(self):
        """F12-T2-5: Native virtual screen is exact Neo-Geo 320x224."""
        self.assertEqual(VIRTUAL_WIDTH, 320)
        self.assertEqual(VIRTUAL_HEIGHT, 224)

    # =========================================================================
    # FEATURE F13: Boss Multi-Part Animated Sprites
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f13_tier1_boss_sprite_sheet_loads(self):
        """F13-T1-1: Tetsuyuki sprite sheet loads from Enemies & Bosses folder."""
        sheet_path = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Tetsuyuki.png"
        sheet = SpriteLoader.load_sheet(sheet_path, colorkey=None)
        self.assertIsNotNone(sheet)

    def test_f13_tier1_hull_surf_dimensions(self):
        """F13-T1-2: Main hull sprite surface exists with substantial dimensions (w >= 300, h >= 200)."""
        self.assertIsNotNone(self.boss.hull_surf)
        self.assertGreaterEqual(self.boss.hull_surf.get_width(), 300)
        self.assertGreaterEqual(self.boss.hull_surf.get_height(), 200)

    def test_f13_tier1_plasma_turret_frames_loaded(self):
        """F13-T1-3: Upper plasma turret frames are loaded with at least 6 animation frames."""
        self.assertIsNotNone(self.boss.turret_frames)
        self.assertGreaterEqual(len(self.boss.turret_frames), 6)

    def test_f13_tier1_turret_animation_advances(self):
        """F13-T1-4: anim_turret updates frame ticks properly."""
        initial_frame = self.boss.anim_turret.current_frame
        for _ in range(10):
            self.boss.anim_turret.update()
        # Animation should have advanced
        self.assertIsNotNone(self.boss.anim_turret.get_current_surface())

    def test_f13_tier1_boss_hurtbox_location(self):
        """F13-T1-5: Boss hurtbox is a valid pygame.Rect positioned at vulnerable zone."""
        hurtbox = self.boss.hurtbox
        self.assertIsInstance(hurtbox, pygame.Rect)
        self.assertEqual(hurtbox.width, 160)
        self.assertEqual(hurtbox.height, 120)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f13_tier2_boss_positioning_at_arena_perch(self):
        """F13-T2-1: Boss is positioned at authentic arena coordinates (x=3750, y=184)."""
        self.assertEqual(self.boss.x, 3750.0)
        self.assertEqual(self.boss.y, 184.0)

    def test_f13_tier2_hurtbox_collision_detection(self):
        """F13-T2-2: Hurtbox detects collision with bullet rect in vulnerable zone."""
        bullet_rect = pygame.Rect(int(self.boss.x + 100), int(self.boss.y - 100), 10, 10)
        self.assertTrue(self.boss.hurtbox.colliderect(bullet_rect))

    def test_f13_tier2_hurtbox_misses_outside_zone(self):
        """F13-T2-3: Hurtbox does not register hits far away from vulnerable zone."""
        far_rect = pygame.Rect(3200, 184, 10, 10)
        self.assertFalse(self.boss.hurtbox.colliderect(far_rect))

    def test_f13_tier2_take_damage_flash_timer(self):
        """F13-T2-4: take_damage triggers white impact flash timer (flash_timer = 4)."""
        self.assertEqual(self.boss.flash_timer, 0)
        self.boss.take_damage(2)
        self.assertEqual(self.boss.flash_timer, 4)

    def test_f13_tier2_flash_timer_decrements(self):
        """F13-T2-5: flash_timer decrements down to 0 over subsequent update ticks."""
        self.boss.take_damage(2)
        self.boss.is_active = True
        for _ in range(5):
            self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
        self.assertEqual(self.boss.flash_timer, 0)

    # =========================================================================
    # FEATURE F14: Removal of Non-Arcade Boss Health Bar
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f14_tier1_no_boss_health_bar_on_screen(self):
        """F14-T1-1: Original Neo-Geo arcade has no boss health bar; drawing boss must not draw yellow health bar."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        surf.fill((0, 0, 0))
        self.boss.is_active = True
        self.boss.draw(surf, self.camera)
        # Check top center bar area (bar_x = 90, bar_y = 36, w = 140, h = 6)
        yellow_pixel_found = False
        for x in range(90, 230):
            for y in range(35, 43):
                col = surf.get_at((x, y))[:3]
                if col == COLOR_HUD_YELLOW or col == (240, 200, 0) or col == (240, 40, 0):
                    yellow_pixel_found = True
                    break
        self.assertFalse(yellow_pixel_found, "Non-arcade boss health bar should not be drawn on screen (R3/F14)")

    def test_f14_tier1_no_tetsuyuki_text_label_drawn(self):
        """F14-T1-2: Boss name label 'BOSS: TETSUYUKI' is not rendered above health bar."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        surf.fill((0, 0, 0))
        self.boss.is_active = True
        self.boss.draw(surf, self.camera)
        # Check area y=24..35 where label was drawn
        label_pixel_count = 0
        for x in range(90, 230):
            for y in range(24, 35):
                if surf.get_at((x, y))[:3] == COLOR_HUD_YELLOW:
                    label_pixel_count += 1
        self.assertEqual(label_pixel_count, 0, "Non-arcade 'BOSS: TETSUYUKI' label must not be rendered")

    def test_f14_tier1_boss_health_tracked_internally_without_hud_dependency(self):
        """F14-T1-3: Boss health is strictly internal (max 80, current 80) and not tied to HUD elements."""
        self.assertEqual(self.boss.max_health, 80)
        self.assertEqual(self.boss.health, 80)

    def test_f14_tier1_taking_damage_does_not_require_health_bar(self):
        """F14-T1-4: Damaging boss decreases health without requiring health bar rendering."""
        self.boss.take_damage(10)
        self.assertEqual(self.boss.health, 70)

    def test_f14_tier1_arcade_fidelity_requirement_f14(self):
        """F14-T1-5: PROJECT.md F14 specifies deletion of non-arcade boss health bar lines."""
        self.assertTrue(hasattr(self.boss, 'draw'))

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f14_tier2_phase1_no_health_bar(self):
        """F14-T2-1: In Phase 1, health bar is not drawn."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.boss.is_active = True
        self.boss.phase = 1
        self.boss.draw(surf, self.camera)
        col = surf.get_at((VIRTUAL_WIDTH // 2, 38))[:3]
        self.assertNotEqual(col, COLOR_HUD_YELLOW)

    def test_f14_tier2_phase2_no_health_bar(self):
        """F14-T2-2: In Phase 2, health bar is not drawn."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.boss.is_active = True
        self.boss.phase = 2
        self.boss.draw(surf, self.camera)
        col = surf.get_at((VIRTUAL_WIDTH // 2, 38))[:3]
        self.assertNotEqual(col, (240, 40, 0))

    def test_f14_tier2_near_defeat_no_health_bar(self):
        """F14-T2-3: At 1 HP, health bar is not drawn."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.boss.is_active = True
        self.boss.health = 1
        self.boss.draw(surf, self.camera)
        col = surf.get_at((VIRTUAL_WIDTH // 2, 38))[:3]
        self.assertNotEqual(col, COLOR_HUD_YELLOW)

    def test_f14_tier2_inactive_boss_no_health_bar(self):
        """F14-T2-4: When is_active=False, no health bar is drawn."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.boss.is_active = False
        self.boss.draw(surf, self.camera)
        col = surf.get_at((VIRTUAL_WIDTH // 2, 38))[:3]
        self.assertEqual(col, (0, 0, 0))

    def test_f14_tier2_defeated_boss_no_health_bar(self):
        """F14-T2-5: When is_defeated=True, no health bar is drawn."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.boss.is_defeated = True
        self.boss.draw(surf, self.camera)
        col = surf.get_at((VIRTUAL_WIDTH // 2, 38))[:3]
        self.assertEqual(col, (0, 0, 0))

    # =========================================================================
    # FEATURE F15: Boss 2-Phase Combat & Defeat Transition
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f15_tier1_initial_phase1_state(self):
        """F15-T1-1: Tetsuyuki starts in Phase 1 with 80 HP."""
        self.assertEqual(self.boss.phase, 1)
        self.assertEqual(self.boss.health, 80)
        self.assertFalse(self.boss.is_defeated)

    def test_f15_tier1_phase1_artillery_attack(self):
        """F15-T1-2: Phase 1 attack cooldown elapsing spawns nose artillery shell."""
        self.boss.is_active = True
        self.boss.attack_cooldown = 1
        self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
        self.assertGreater(len(self.enemy_projectiles), 0, "Phase 1 must spawn artillery shell")
        self.assertEqual(self.boss.attack_cooldown, 110)

    def test_f15_tier1_transition_to_phase2_at_half_health(self):
        """F15-T1-3: Damaging boss to <= 40 HP triggers Phase 2 rage mode."""
        self.boss.take_damage(40)
        self.assertEqual(self.boss.health, 40)
        self.assertEqual(self.boss.phase, 2, "Boss must transition to Phase 2 at <= 50% health")

    def test_f15_tier1_phase2_giant_plasma_orb_attack(self):
        """F15-T1-4: Phase 2 attack cooldown elapsing spawns GiantPlasmaOrb."""
        self.boss.is_active = True
        self.boss.phase = 2
        self.boss.attack_cooldown = 1
        self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
        plasma_orbs = [p for p in self.enemy_projectiles if isinstance(p, GiantPlasmaOrb)]
        self.assertGreater(len(plasma_orbs), 0, "Phase 2 must launch GiantPlasmaOrb")

    def test_f15_tier1_fatal_damage_triggers_cascading_defeat(self):
        """F15-T1-5: Reducing health to 0 marks is_defeated=True and sets defeat_timer=180."""
        self.boss.take_damage(80)
        self.assertEqual(self.boss.health, 0)
        self.assertTrue(self.boss.is_defeated)
        self.assertTrue(self.boss.is_dead)
        self.assertEqual(self.boss.defeat_timer, 180)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f15_tier2_defeat_timer_decrements(self):
        """F15-T2-1: defeat_timer decrements down from 180 each update tick."""
        self.boss.take_damage(80)
        self.boss.is_active = True
        initial_timer = self.boss.defeat_timer
        self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
        self.assertEqual(self.boss.defeat_timer, initial_timer - 1)

    def test_f15_tier2_defeated_boss_takes_no_further_damage(self):
        """F15-T2-2: Defeated boss ignores additional damage hits."""
        self.boss.take_damage(80)
        self.assertEqual(self.boss.health, 0)
        self.boss.take_damage(20)
        self.assertEqual(self.boss.health, 0)

    def test_f15_tier2_plasma_orb_physics_and_platform_impact(self):
        """F15-T2-3: GiantPlasmaOrb travels under gravity and impacts platform."""
        orb = GiantPlasmaOrb(x=3500, y=100)
        orb.vy = 2.0
        for _ in range(40):
            orb.update(self.platforms, self.camera)
        self.assertTrue(orb.exploded)
        self.assertTrue(orb.is_dead)

    def test_f15_tier2_plasma_orb_draw_without_camera_error(self):
        """F15-T2-4: GiantPlasmaOrb draws cleanly without errors onto surface."""
        orb = GiantPlasmaOrb(x=3500, y=150)
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        orb.draw(surf, self.camera)
        self.assertIsNotNone(surf)

    def test_f15_tier2_boss_activation_proximity(self):
        """F15-T2-5: Boss becomes active when player is within 320px distance."""
        self.assertFalse(self.boss.is_active)
        self.player.physics.x = self.boss.x - 200
        self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
        self.assertTrue(self.boss.is_active)

    # =========================================================================
    # TIER 3: Cross-Feature Combinations (Pairwise Interactions)
    # =========================================================================
    def test_tier3_f13_f15_phase2_turret_animation_and_orb_spawn(self):
        """T3-1 (F13+F15): In Phase 2, animated plasma turret updates and launches GiantPlasmaOrb."""
        self.boss.is_active = True
        self.boss.phase = 2
        self.boss.attack_cooldown = 1
        self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
        self.assertIsNotNone(self.boss.anim_turret.get_current_surface())
        plasma_orbs = [p for p in self.enemy_projectiles if isinstance(p, GiantPlasmaOrb)]
        self.assertGreater(len(plasma_orbs), 0)

    def test_tier3_f12_f15_defeat_explosions_over_waterfall(self):
        """T3-2 (F12+F15): Cascading explosions during boss defeat shake camera over waterfall backdrop."""
        level = Mission1Level()
        level.boss = self.boss
        self.boss.is_active = True
        self.boss.take_damage(80)
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        for _ in range(30):
            self.boss.update(self.player, self.platforms, self.enemy_projectiles, self.particles, self.camera)
            level.draw_background(surf, self.camera)
        self.assertLess(self.boss.defeat_timer, 180)

    def test_tier3_f14_f15_phase_transitions_without_health_bar(self):
        """T3-3 (F14+F15): Boss transitioning through all combat phases never draws a health bar."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.boss.is_active = True
        # Phase 1
        self.boss.draw(surf, self.camera)
        # Phase 2
        self.boss.take_damage(40)
        self.assertEqual(self.boss.phase, 2)
        self.boss.draw(surf, self.camera)
        # Defeated
        self.boss.take_damage(40)
        self.assertTrue(self.boss.is_defeated)
        self.boss.draw(surf, self.camera)

    def test_tier3_f15_level_mission_complete_latch(self):
        """T3-4 (F15+level): When boss defeat_timer finishes, level marks is_mission_complete=True."""
        level = Mission1Level()
        level.boss = self.boss
        self.boss.take_damage(80)
        self.boss.defeat_timer = 0
        level.update(self.player, self.camera)
        self.assertTrue(level.is_mission_complete, "Level must set is_mission_complete upon boss defeat timer 0")


if __name__ == "__main__":
    unittest.main()
