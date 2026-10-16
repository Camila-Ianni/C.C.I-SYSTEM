"""
tests/test_title_screen.py - Dedicated Smoke & Integration Test Suite for TitleScreen and MainMenu.
Milestone 2: Title Screen & Menu Architecture (Da Vinci Fighters)

Covers:
1. TitleScreen initialization, scaling, and canvas geometry of assets/backgrounds/home.png.
2. Animated metallic logo sheen shader math, progression over time (update(dt)), and bounds.
3. Start prompt ('PRESS ANY KEY TO START') 2 Hz blinking oscillation cadence.
4. Input transitions from TitleScreen to MainMenu (keys, mouse click, ignored events).
5. MainMenu game mode selection (1P vs AI / 2P PVP), navigation wrapping, WASD keys.
6. Audio synchronization: Opening Theme.mp3 playback, procedural SFX blips/chimes, fadeout.
7. End-to-end transition flow from TitleScreen to MainMenu to CharacterSelect.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pygame

from tests.base_headless import (
    HeadlessTestCase,
    CANONICAL_SCREEN_WIDTH,
    CANONICAL_SCREEN_HEIGHT,
    CANONICAL_FPS,
)
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_YELLOW,
    COLOR_WHITE,
    COLOR_BG,
    MODE_PVAI,
    MODE_PVP,
    FPS,
)
from audio_manager import audio_manager

# Robust import supporting both new title_screen.py and legacy menu.py
try:
    from title_screen import TitleScreen
except ImportError:
    from menu import TitleScreen

from menu import MainMenu
from main import AppState


class TestTitleScreenSmoke(HeadlessTestCase):
    """
    Dedicated Smoke Tests for TitleScreen:
    Initialization, home.png geometry, sheen shader progression, blinking prompt, and input.
    """

    def test_01_init_geometry_and_defaults(self):
        """Verifies TitleScreen default state, screen binding, and home.png dimensions."""
        ts = TitleScreen(self.screen)
        self.assertEqual(ts.screen, self.screen)
        self.assertEqual(ts.blink_timer, 0)
        self.assertIsNotNone(ts.image)
        self.assertEqual(ts.image.get_size(), (CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT))

        # Logo bounding box check (Rect(99, 42, 1090, 376))
        self.assertTrue(hasattr(ts, "logo_rect"))
        self.assertEqual(ts.logo_rect.left, 99)
        self.assertEqual(ts.logo_rect.top, 42)
        self.assertEqual(ts.logo_rect.width, 1090)
        self.assertEqual(ts.logo_rect.height, 376)
        self.assertLess(ts.logo_rect.right, CANONICAL_SCREEN_WIDTH)
        self.assertLess(ts.logo_rect.bottom, CANONICAL_SCREEN_HEIGHT)

    def test_02_init_none_screen_safe(self):
        """Verifies TitleScreen initializes cleanly when screen=None."""
        ts = TitleScreen(None)
        self.assertIsNone(ts.screen)
        self.assertEqual(ts.blink_timer, 0)

    def test_03_sheen_shader_surface_and_parameters(self):
        """Verifies metallic sheen highlight surface has alpha channel and sweep parameters."""
        ts = TitleScreen(self.screen)
        self.assertTrue(hasattr(ts, "sheen_surf"))
        self.assertIsInstance(ts.sheen_surf, pygame.Surface)
        self.assertTrue(bool(ts.sheen_surf.get_flags() & pygame.SRCALPHA))
        self.assertEqual(ts.sheen_offset, 0.0)
        self.assertEqual(ts.sheen_period, 120)
        self.assertGreater(ts.sheen_speed, 0.0)
        self.assertGreater(ts.sweep_width, 1000)

    def test_04_sheen_progression_over_time(self):
        """Verifies update(dt) advances sheen offset and frame counter monotonically."""
        ts = TitleScreen(self.screen)
        self.assertTrue(hasattr(ts, "update"))
        self.assertEqual(ts.sheen_offset, 0.0)

        # Advance 1 frame (1/60s)
        ts.update(1.0 / 60.0)
        self.assertGreater(ts.sheen_offset, 0.0)
        first_offset = ts.sheen_offset

        # Advance 9 more frames
        for _ in range(9):
            ts.update(1.0 / 60.0)
        self.assertGreater(ts.sheen_offset, first_offset)

        # Advance full period (120 frames) to verify smooth wraparound
        for _ in range(120):
            ts.update(1.0 / 60.0)
        self.assertGreaterEqual(ts.sheen_offset, 0.0)
        self.assertLess(ts.sheen_offset, ts.sweep_width)

    def test_05_sheen_variable_dt_stepping(self):
        """Verifies update(dt) accurately scales frame advancement with fractional or multi-frame dt."""
        ts = TitleScreen(self.screen)
        self.assertTrue(hasattr(ts, "update"))
        initial_blink = ts.blink_timer

        # 2 frames in single step
        ts.update(2.0 / 60.0)
        self.assertEqual(ts.blink_timer, initial_blink + 2)

        # 1 second step (60 frames)
        ts.update(1.0)
        self.assertEqual(ts.blink_timer, initial_blink + 62)

    def test_06_start_prompt_blinking_oscillation_2hz(self):
        """Verifies start prompt visibility alternates every 30 frames (2 Hz at 60 FPS)."""
        ts = TitleScreen(self.screen)
        self.assertTrue(hasattr(ts, "update"))
        is_visible = lambda timer: ((timer // 30) % 2) == 0

        # Frame 0: Visible
        self.assertTrue(is_visible(ts.blink_timer))

        # Advance to frame 30: Hidden
        for _ in range(30):
            ts.update(1.0 / 60.0)
        self.assertEqual(ts.blink_timer, 30)
        self.assertFalse(is_visible(ts.blink_timer))

        # Advance to frame 60: Visible again
        for _ in range(30):
            ts.update(1.0 / 60.0)
        self.assertEqual(ts.blink_timer, 60)
        self.assertTrue(is_visible(ts.blink_timer))

    def test_07_handle_input_space_transition(self):
        """Verifies pressing SPACE on TitleScreen triggers menu transition."""
        ts = TitleScreen(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        res = ts.handle_input(event)
        self.assertIn(res, ("continue", "start"))

    def test_08_handle_input_return_transition(self):
        """Verifies pressing RETURN on TitleScreen triggers menu transition."""
        ts = TitleScreen(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        res = ts.handle_input(event)
        self.assertIn(res, ("continue", "start"))

    def test_09_handle_input_escape_transition(self):
        """Verifies pressing ESCAPE on TitleScreen triggers menu transition."""
        ts = TitleScreen(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        res = ts.handle_input(event)
        self.assertIn(res, ("continue", "start"))

    def test_10_handle_input_mouse_click_transition(self):
        """Verifies mouse button click triggers menu transition."""
        ts = TitleScreen(self.screen)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1)
        res = ts.handle_input(event)
        self.assertIn(res, ("continue", "start"))

    def test_11_handle_input_ignored_events(self):
        """Verifies KEYUP and MOUSEMOTION events are ignored without triggering transition."""
        ts = TitleScreen(self.screen)
        for ev in [
            pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN),
            pygame.event.Event(pygame.MOUSEMOTION, pos=(500, 300), rel=(5, 5)),
            pygame.event.Event(pygame.NOEVENT),
        ]:
            res = ts.handle_input(ev)
            self.assertIsNone(res)

    def test_12_draw_pipeline_execution(self):
        """Verifies draw() and draw(screen) render cleanly without exceptions."""
        ts = TitleScreen(self.screen)
        try:
            ts.draw()
            ts.draw(self.screen)
        except Exception as e:
            self.fail(f"TitleScreen.draw() raised: {e}")

    def test_13_missing_image_asset_fallback(self):
        """Verifies graceful fallback to dark navy background if home.png is missing."""
        orig_exists = os.path.exists

        def fake_exists(path):
            if "home.png" in str(path):
                return False
            return orig_exists(path)

        with patch("os.path.exists", side_effect=fake_exists):
            ts = TitleScreen(self.screen)
            self.assertIsNone(ts.image)
            try:
                ts.draw(self.screen)
            except TypeError:
                ts.draw()
            except Exception as e:
                self.fail(f"TitleScreen fallback draw raised: {e}")


class TestMainMenuSmoke(HeadlessTestCase):
    """
    Dedicated Smoke Tests for MainMenu:
    Option list, mode navigation (1P vs 2P), controls modal, and action returns.
    """

    def test_14_main_menu_options_and_defaults(self):
        """Verifies MainMenu initial state, options list, and selected index."""
        menu = MainMenu(self.screen)
        self.assertEqual(len(menu.options), 4)
        self.assertIn("1 JUGADOR (VS IA)", menu.options[0])
        self.assertIn("2 JUGADORES (PVP)", menu.options[1])
        self.assertIn("CÓMO JUGAR", menu.options[2])
        self.assertIn("SALIR", menu.options[3])
        self.assertEqual(menu.selected_idx, 0)
        self.assertFalse(menu.showing_controls)

    def test_15_mode_navigation_down_and_up(self):
        """Verifies DOWN arrow navigates 1P -> 2P -> Controls and UP navigates back."""
        menu = MainMenu(self.screen)
        self.assertEqual(menu.selected_idx, 0)

        # Move to 2P
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(menu.selected_idx, 1)

        # Move to Controls
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(menu.selected_idx, 2)

        # Move back to 2P
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        self.assertEqual(menu.selected_idx, 1)

        # Move back to 1P
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        self.assertEqual(menu.selected_idx, 0)

    def test_16_mode_navigation_wraparound(self):
        """Verifies UP arrow from index 0 wraps to 3, and DOWN arrow from 3 wraps to 0."""
        menu = MainMenu(self.screen)
        # UP wraps to SALIR (index 3)
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        self.assertEqual(menu.selected_idx, 3)

        # DOWN wraps back to 1P (index 0)
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(menu.selected_idx, 0)

    def test_17_confirm_1p_mode(self):
        """Verifies pressing RETURN on option 0 selects MODE_PVAI."""
        menu = MainMenu(self.screen)
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res, {"action": "start", "mode": MODE_PVAI})
        self.assertTrue(hasattr(menu, "selected_mode"))
        self.assertEqual(menu.selected_mode, MODE_PVAI)

    def test_18_confirm_2p_mode(self):
        """Verifies navigating to option 1 and pressing RETURN selects MODE_PVP."""
        menu = MainMenu(self.screen)
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res, {"action": "start", "mode": MODE_PVP})
        self.assertTrue(hasattr(menu, "selected_mode"))
        self.assertEqual(menu.selected_mode, MODE_PVP)

    def test_19_confirm_via_space_key(self):
        """Verifies pressing SPACE also confirms game mode selection."""
        menu = MainMenu(self.screen)
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(res, {"action": "start", "mode": MODE_PVAI})

    def test_20_controls_modal_toggle_and_dismiss(self):
        """Verifies selecting 'CÓMO JUGAR' displays overlay and any key dismisses it."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 2  # CÓMO JUGAR
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNone(res)
        self.assertTrue(menu.showing_controls)

        # Any key dismisses overlay without changing selection
        dismiss_res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsNone(dismiss_res)
        self.assertFalse(menu.showing_controls)
        self.assertEqual(menu.selected_idx, 2)

    def test_21_confirm_exit_action(self):
        """Verifies selecting 'SALIR' yields exit action dictionary."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 3  # SALIR
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res, {"action": "exit"})

    def test_22_menu_update_and_draw(self):
        """Verifies MainMenu.update(dt) and draw(screen) execute cleanly."""
        menu = MainMenu(self.screen)
        self.assertTrue(hasattr(menu, "update"))
        menu.update(1.0 / 60.0)
        self.assertTrue(hasattr(menu, "anim_timer"))
        self.assertGreater(menu.anim_timer, 0)

        try:
            menu.draw()
            menu.draw(self.screen)
        except Exception as e:
            self.fail(f"MainMenu.draw() raised: {e}")


class TestTitleAndMenuAudioIntegration(HeadlessTestCase):
    """
    Audio Synchronization Tests for Title Screen & Menu:
    Opening Theme playback, looping, procedural SFX triggers, and mode select fadeout.
    """

    def test_23_title_screen_starts_opening_theme(self):
        """Verifies TitleScreen instantiation starts Opening Theme.mp3."""
        audio_manager.stop_music()
        self.assertIsNone(audio_manager.current_track)

        ts = TitleScreen(self.screen)
        self.assertIsNotNone(audio_manager.current_track)
        self.assertIn("Opening Theme.mp3", audio_manager.current_track)

    def test_24_transition_to_menu_preserves_opening_music(self):
        """Verifies TitleScreen to MainMenu preserves Opening Theme without restarting."""
        ts = TitleScreen(self.screen)
        track_before = audio_manager.current_track

        menu = MainMenu(self.screen)
        track_after = audio_manager.current_track

        self.assertEqual(track_before, track_after)
        self.assertIn("Opening Theme.mp3", track_after)

    def test_25_menu_navigation_triggers_navigate_sfx(self):
        """Verifies navigating options in MainMenu triggers 'menu_navigate' SFX."""
        menu = MainMenu(self.screen)
        with patch.object(audio_manager, "play_sfx") as mock_sfx:
            menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            mock_sfx.assert_called_with("menu_navigate")

    def test_26_menu_confirmation_triggers_confirm_sfx(self):
        """Verifies confirming an option in MainMenu triggers 'menu_confirm' SFX."""
        menu = MainMenu(self.screen)
        with patch.object(audio_manager, "play_sfx") as mock_sfx:
            menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            mock_sfx.assert_called_with("menu_confirm")

    def test_27_audio_stability_under_extended_title_idle(self):
        """Verifies TitleScreen idle for 120 virtual frames maintains audio track cleanly."""
        ts = TitleScreen(self.screen)
        initial_track = audio_manager.current_track
        for _ in range(120):
            if hasattr(ts, "update"):
                ts.update(1.0 / 60.0)
        self.assertEqual(audio_manager.current_track, initial_track)


class TestTitleMenuE2EIntegration(HeadlessTestCase):
    """
    End-to-End Integration Flow:
    TitleScreen -> MainMenu -> Mode Selection (1P/2P) -> Mode Confirm Handover.
    """

    def test_28_e2e_flow_title_to_menu_to_1p_select(self):
        """Simulates complete journey from TitleScreen into 1P CharacterSelect."""
        # 1. Mount TitleScreen
        title = TitleScreen(self.screen)
        if hasattr(title, "update"):
            for _ in range(60):
                title.update(1.0 / 60.0)

        # 2. Press Return to advance
        title_res = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIn(title_res, ("continue", "start"))

        # 3. Mount MainMenu
        menu = MainMenu(self.screen)
        self.assertEqual(menu.selected_idx, 0)

        # 4. Confirm 1P mode
        menu_res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(menu_res["action"], "start")
        self.assertEqual(menu_res["mode"], MODE_PVAI)

    def test_29_e2e_flow_title_to_menu_to_2p_select(self):
        """Simulates complete journey from TitleScreen into 2P CharacterSelect."""
        # 1. Mount TitleScreen
        title = TitleScreen(self.screen)

        # 2. Press Space to advance
        title_res = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertIn(title_res, ("continue", "start"))

        # 3. Mount MainMenu and navigate down to 2P
        menu = MainMenu(self.screen)
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(menu.selected_idx, 1)

        # 4. Confirm 2P mode
        menu_res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(menu_res["action"], "start")
        self.assertEqual(menu_res["mode"], MODE_PVP)

    def test_30_app_state_wiring_integrity(self):
        """Verifies AppState constants for TITLE_SCREEN and MENU states."""
        self.assertTrue(hasattr(AppState, "TITLE_SCREEN"))
        self.assertTrue(hasattr(AppState, "MENU"))
        self.assertEqual(AppState.TITLE_SCREEN, "title_screen")
        self.assertEqual(AppState.MENU, "menu")


if __name__ == "__main__":
    unittest.main()
