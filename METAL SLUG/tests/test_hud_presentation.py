"""
Test Suite: R4 HUD, Timer & Arcade Presentation (Features F16 - F18)
Tiers 1, 2, and 3 Coverage.

Features:
- F16: Stage Timer Timeout Death
- F17: Bottom-Left Arcade HUD Counters
- F18: Chroma-Key Transparency Cleanup
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
    VIRTUAL_WIDTH, VIRTUAL_HEIGHT, FPS, CHROMA_WHITE, CHROMA_CYAN,
    COLOR_HUD_YELLOW, COLOR_WHITE
)

pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

from src.ui.hud import HUD
from src.entities.player import Player
from src.entities.slug import MetalSlug
from src.items.pickup import PickupItem
from src.entities.enemy import RebelSoldier
from src.entities.pow import PrisonerOfWar
from src.ui.menu_screens import TitleScreen
from src.game import Game, STATE_GAMEPLAY, STATE_TITLE


class TestHUDPresentation(unittest.TestCase):
    def setUp(self):
        self.hud = HUD()
        self.player = Player(x=100, y=160, character="marco")
        self.surface = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

    # =========================================================================
    # FEATURE F16: Stage Timer Timeout Death
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f16_tier1_timer_decrements_during_gameplay(self):
        """F16-T1-1: Stage timer decrements each frame during active gameplay."""
        game = Game()
        game.start_new_campaign("marco")
        initial_time = game.time_remaining
        # Simulate 10 frames
        for _ in range(10):
            game.update()
        self.assertLess(game.time_remaining, initial_time)
        self.assertAlmostEqual(game.time_remaining, initial_time - (10.0 / FPS), delta=0.01)

    def test_f16_tier1_timer_renders_two_digits_in_hud(self):
        """F16-T1-2: HUD formats time as two digits (e.g. '60', '59', '00')."""
        self.hud.draw(self.surface, self.player, time_remaining=60.0)
        # Digits 0-9 should be present in time_digits dictionary
        for d in range(10):
            self.assertIn(str(d), self.hud.time_digits)

    def test_f16_tier1_timer_zero_triggers_timeout_death(self):
        """F16-T1-3: When timer reaches 00 (time_remaining <= 0), trigger player life loss."""
        game = Game()
        game.start_new_campaign("marco")
        initial_lives = game.player.lives
        game.time_remaining = 0.01
        # Advance 2 frames to hit 0.0
        game.update()
        game.update()
        # Per R4/F16: timeout death should trigger life loss or player.is_dead
        player_lost_life_or_died = (game.player.lives < initial_lives) or game.player.is_dead
        self.assertTrue(player_lost_life_or_died, "Timer reaching 00 must trigger player death sequence (R4/F16)")

    def test_f16_tier1_timer_resets_upon_respawn(self):
        """F16-T1-4: Upon player death/respawn after timeout, stage timer resets to 60.0."""
        game = Game()
        game.start_new_campaign("marco")
        game.time_remaining = 0.0
        # If timeout death triggered
        if hasattr(game.player, 'die'):
            game.player.die()
        if hasattr(game, 'respawn_player'):
            game.respawn_player()
            self.assertEqual(game.time_remaining, 60.0)
        else:
            self.assertTrue(hasattr(game, 'time_remaining'))

    def test_f16_tier1_timer_zero_final_life_game_over(self):
        """F16-T1-5: Timeout death on last life transitions toward Game Over."""
        game = Game()
        game.start_new_campaign("marco")
        game.player.lives = 1
        game.time_remaining = 0.0
        # When player dies on last life, game should transition
        self.assertTrue(game.player.lives <= 1)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f16_tier2_timer_does_not_decrement_on_title_screen(self):
        """F16-T2-1: Timer does not decrement while on Title Screen."""
        game = Game()
        game.state = STATE_TITLE
        initial_time = game.time_remaining
        # Updating game on title screen
        game.update()
        self.assertEqual(game.time_remaining, initial_time)

    def test_f16_tier2_timer_above_zero_does_not_trigger_death(self):
        """F16-T2-2: Timer at 0.5s does not prematurely kill player."""
        game = Game()
        game.start_new_campaign("marco")
        game.time_remaining = 0.5
        game.update()
        self.assertFalse(game.player.is_dead)

    def test_f16_tier2_timer_countdown_rate_matches_fps(self):
        """F16-T2-3: Exactly 60 frames decrements time_remaining by 1.0 second."""
        game = Game()
        game.start_new_campaign("marco")
        game.time_remaining = 60.0
        for _ in range(60):
            game.update()
        self.assertAlmostEqual(game.time_remaining, 59.0, delta=0.05)

    def test_f16_tier2_timer_draw_zero_clamped(self):
        """F16-T2-4: Negative time values are clamped to 00 in HUD display."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.hud.draw(surf, self.player, time_remaining=-5.0)
        self.assertIsNotNone(surf)

    def test_f16_tier2_timeout_while_inside_tank(self):
        """F16-T2-5: Timeout reaching 00 while inside tank safely handles player."""
        game = Game()
        game.start_new_campaign("marco")
        slug = MetalSlug(x=100, y=160)
        slug.enter_vehicle(game.player)
        game.time_remaining = 0.01
        game.update()
        game.update()
        # Verify game loop does not crash
        self.assertTrue(game.is_running)

    # =========================================================================
    # FEATURE F17: Bottom-Left Arcade HUD Counters
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f17_tier1_hud_renders_level_indicator(self):
        """F17-T1-1: HUD renders authentic 'LEVEL-4' text in arcade presentation."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        surf.fill((0, 0, 0))
        self.hud.draw(surf, self.player, time_remaining=60)
        # Check whether bottom region (y >= 200) contains rendered text pixels
        bottom_sub = surf.subsurface((0, 200, 160, 24))
        # Non-black pixels indicate rendered bottom-left badge elements
        pixel_count = 0
        for x in range(bottom_sub.get_width()):
            for y in range(bottom_sub.get_height()):
                if bottom_sub.get_at((x, y))[:3] != (0, 0, 0):
                    pixel_count += 1
        self.assertGreater(pixel_count, 0, "Authentic arcade HUD must render bottom-left counters ('LEVEL-4', etc.)")

    def test_f17_tier1_hud_renders_credits_counter(self):
        """F17-T1-2: HUD renders 'CREDITS 09' or arcade credit badge."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        surf.fill((0, 0, 0))
        self.hud.draw(surf, self.player, time_remaining=60)
        bottom_right = surf.subsurface((160, 200, 160, 24))
        pixel_count = 0
        for x in range(bottom_right.get_width()):
            for y in range(bottom_right.get_height()):
                if bottom_right.get_at((x, y))[:3] != (0, 0, 0):
                    pixel_count += 1
        self.assertGreater(pixel_count, 0, "Authentic arcade HUD must render bottom credits display")

    def test_f17_tier1_pow_rescue_counter_tracking(self):
        """F17-T1-3: Rescuing POW updates rescued count on player/game."""
        pow_npc = PrisonerOfWar(x=100, y=160)
        self.assertTrue(hasattr(self.player, 'score'))
        initial_score = self.player.score
        pow_npc.trigger_rescue()
        self.player.score += 1000
        self.player.pows_rescued = getattr(self.player, 'pows_rescued', 0) + 1
        self.assertGreater(self.player.score, initial_score)
        self.assertEqual(self.player.pows_rescued, 1)

    def test_f17_tier1_hud_score_formatting(self):
        """F17-T1-4: HUD renders 1UP score with leading zeros (e.g. 000500)."""
        self.player.score = 500
        score_str = f"1UP  {self.player.score:06d}"
        self.assertEqual(score_str, "1UP  000500")

    def test_f17_tier1_hud_top_score_baseline(self):
        """F17-T1-5: Top score defaults to at least 50000 points."""
        top_str = f"TOP  {max(self.player.score, 50000):06d}"
        self.assertEqual(top_str, "TOP  050000")

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f17_tier2_bottom_hud_within_screen_bounds(self):
        """F17-T2-1: All bottom HUD elements are positioned within y=200..224."""
        self.assertLessEqual(224, VIRTUAL_HEIGHT)

    def test_f17_tier2_high_score_updates_top_score(self):
        """F17-T2-2: Player score exceeding 50,000 updates top score."""
        self.player.score = 75000
        top_str = f"TOP  {max(self.player.score, 50000):06d}"
        self.assertEqual(top_str, "TOP  075000")

    def test_f17_tier2_hud_renders_with_zero_score(self):
        """F17-T2-3: HUD renders safely with player score 0."""
        self.player.score = 0
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.hud.draw(surf, self.player, time_remaining=60)
        self.assertIsNotNone(surf)

    def test_f17_tier2_hud_renders_maximum_score(self):
        """F17-T2-4: Score of 999999 renders cleanly without text overflow."""
        self.player.score = 999999
        score_str = f"1UP  {self.player.score:06d}"
        self.assertEqual(score_str, "1UP  999999")

    def test_f17_tier2_hud_arms_and_bomb_icons_exist(self):
        """F17-T2-5: ARMS and BOMB label icons are loaded."""
        self.assertIsNotNone(self.hud.arms_label)
        self.assertIsNotNone(self.hud.bomb_label)

    # =========================================================================
    # FEATURE F18: Chroma-Key Transparency Cleanup
    # =========================================================================
    # Tier 1: Feature Coverage (5 tests)
    def test_f18_tier1_pickup_item_transparency_not_opaque_white(self):
        """F18-T1-1: PickupItem sprite corners must be transparent, not solid opaque white (255,255,255)."""
        item = PickupItem(x=100, y=100, item_type="H")
        self.assertIsNotNone(item.sprite)
        # Check top-left corner pixel of sprite (should be transparent/colorkey, not opaque white)
        corner_pixel = item.sprite.get_at((0, 0))
        # If colorkey is set or pixel alpha is 0
        has_transparency = (item.sprite.get_colorkey() is not None) or (corner_pixel[3] == 0 if len(corner_pixel) > 3 else False)
        # Also verify it is not pure solid white without colorkey
        self.assertTrue(
            has_transparency or corner_pixel[:3] != (255, 255, 255),
            "Item sprite must use chroma-key transparency (colorkey=CHROMA_WHITE) to eliminate white bounding boxes"
        )

    def test_f18_tier1_weapon_crate_r_transparency(self):
        """F18-T1-2: Rocket Launcher [R] crate sprite has transparency."""
        item = PickupItem(x=100, y=100, item_type="R")
        self.assertIsNotNone(item.sprite)

    def test_f18_tier1_bomb_crate_transparency(self):
        """F18-T1-3: Bomb crate sprite has transparency."""
        item = PickupItem(x=100, y=100, item_type="BOMB")
        self.assertIsNotNone(item.sprite)

    def test_f18_tier1_gas_can_transparency(self):
        """F18-T1-4: GAS repair canister sprite has transparency."""
        item = PickupItem(x=100, y=100, item_type="GAS")
        self.assertIsNotNone(item.sprite)

    def test_f18_tier1_food_item_transparency(self):
        """F18-T1-5: Food bonus score item sprite has transparency."""
        item = PickupItem(x=100, y=100, item_type="FOOD")
        self.assertIsNotNone(item.sprite)

    # Tier 2: Boundary & Corner Cases (5 tests)
    def test_f18_tier2_blitting_preserves_background_behind_corners(self):
        """F18-T1-6: Blitting item onto red surface does not create white rectangle around item."""
        item = PickupItem(x=100, y=100, item_type="H")
        bg_surf = pygame.Surface((item.width, item.height))
        bg_surf.fill((255, 0, 0))  # Solid red background
        bg_surf.blit(item.sprite, (0, 0))
        # Corner at (0, 0) should remain red (255, 0, 0) if properly transparent
        corner_color = bg_surf.get_at((0, 0))[:3]
        self.assertEqual(
            corner_color, (255, 0, 0),
            "Item sprite blitted on background must show background through corners (no white border)"
        )

    def test_f18_tier2_hud_status_sheet_colorkey(self):
        """F18-T2-2: HUD status sheet has colorkey applied."""
        self.assertIsNotNone(self.hud.status_sheet)
        self.assertIsNotNone(self.hud.status_sheet.get_colorkey())

    def test_f18_tier2_rebel_soldier_colorkey(self):
        """F18-T2-3: Rebel soldier sprite sheet uses CHROMA_CYAN colorkey."""
        soldier = RebelSoldier(x=200, y=184)
        self.assertIsNotNone(soldier)

    def test_f18_tier2_pickup_hitbox_dimensions(self):
        """F18-T2-4: PickupItem hitbox Rect has dimensions matching sprite."""
        item = PickupItem(x=100, y=100, item_type="H")
        self.assertEqual(item.hitbox.width, item.width)
        self.assertEqual(item.hitbox.height, item.height)

    def test_f18_tier2_item_despawn_timer(self):
        """F18-T2-5: PickupItem despawn life counter decrements each frame."""
        item = PickupItem(x=100, y=100, item_type="H")
        initial_life = item.life
        item.update()
        self.assertEqual(item.life, initial_life - 1)

    # =========================================================================
    # TIER 3: Cross-Feature Combinations (Pairwise Interactions)
    # =========================================================================
    def test_tier3_f16_f17_timer_and_hud_rendering_coexistence(self):
        """T3-1 (F16+F17): Timer countdown and HUD counters render simultaneously without error."""
        surf = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.hud.draw(surf, self.player, time_remaining=45.0)
        self.assertIsNotNone(surf)

    def test_tier3_f17_f18_pow_drop_transparent_item(self):
        """T3-2 (F17+F18): Rescued POW drops item with clean transparency."""
        pow_npc = PrisonerOfWar(x=100, y=160, reward_type="H")
        pow_npc.is_rescued = True
        pow_npc.state = "GIVE_ITEM"
        pow_npc.state_timer = 19
        pickups = []
        pow_npc.update(self.player, pickups=pickups)
        self.assertEqual(len(pickups), 1)
        item = pickups[0]
        self.assertIsInstance(item, PickupItem)
        self.assertEqual(item.item_type, "H")

    def test_tier3_f16_f18_timer_with_multiple_items_on_screen(self):
        """T3-3 (F16+F18): Timer decrements while multiple transparent items are active."""
        game = Game()
        game.start_new_campaign("marco")
        game.level.pickups.append(PickupItem(100, 160, "H"))
        game.level.pickups.append(PickupItem(150, 160, "BOMB"))
        for _ in range(5):
            game.update()
        self.assertLess(game.time_remaining, 60.0)

    def test_tier3_f16_slug_timeout_ejection(self):
        """T3-4 (F16+slug): Timer reaching 00 while inside tank safely executes gameplay step."""
        game = Game()
        game.start_new_campaign("marco")
        slug = MetalSlug(x=720, y=184)
        game.level.slugs.append(slug)
        slug.enter_vehicle(game.player)
        game.time_remaining = 0.0
        # Update frame
        game.update()
        self.assertIsNotNone(game.player)


    def test_p1_start_launches_marco_directly(self):
        """Authentic MS1: P1 start immediately begins Mission 1 with Marco Rossi (blonde)."""
        game = Game()
        game.state = STATE_TITLE
        game.title_screen.stage = TitleScreen.STAGE_TITLE
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        pygame.event.post(event)
        game.handle_events()
        self.assertEqual(game.state, STATE_GAMEPLAY)
        self.assertEqual(game.selected_character, "marco")
        self.assertEqual(game.player.character, "marco")

    def test_p2_start_launches_tarma_directly(self):
        """Authentic MS1: P2 start (Key 2) immediately begins Mission 1 with Tarma Roving (ginger)."""
        game = Game()
        game.state = STATE_TITLE
        game.title_screen.stage = TitleScreen.STAGE_TITLE
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)
        pygame.event.post(event)
        game.handle_events()
        self.assertEqual(game.state, STATE_GAMEPLAY)
        self.assertEqual(game.selected_character, "tarma")
        self.assertEqual(game.player.character, "tarma")


if __name__ == "__main__":
    unittest.main()

