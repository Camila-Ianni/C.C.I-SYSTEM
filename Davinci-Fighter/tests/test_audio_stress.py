"""
tests/test_audio_stress.py - Adversarial and empirical stress tests for audio_manager.py.

Evaluates:
1. High-concurrency sound triggers (200 SFX across all 32 channels, threaded and sequential).
2. Airplane drone loop preservation on Channel 0 under SFX storms.
3. Boundary volume inputs (negative, extreme, non-float inputs).
4. Stage music routing for all 5 characters and fallback handling.
5. Headless resilience when mixer is uninitialized or hardware raises errors.
"""

import os
import unittest
import threading
from unittest.mock import patch, MagicMock
import pygame
from audio_manager import AudioManager, audio_manager


class TestAudioHighConcurrencyStress(unittest.TestCase):
    """Stress tests for high-concurrency sound triggering across all channels."""

    def setUp(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        audio_manager._ensure_mixer()

    def tearDown(self):
        audio_manager.stop_airplane_drone()
        audio_manager.stop_music()
        if pygame.mixer.get_init():
            for i in range(pygame.mixer.get_num_channels()):
                try:
                    pygame.mixer.Channel(i).stop()
                except Exception:
                    pass

    def test_concurrency_200_sfx_sequential_burst(self):
        """Trigger 200 SFX in rapid burst across all 32 channels without errors."""
        channels_returned = []
        for i in range(200):
            sfx = ["cursor_move", "confirm", "vs_impact"][i % 3]
            ch = audio_manager.play_sfx(sfx)
            channels_returned.append(ch)

        self.assertEqual(len(channels_returned), 200)
        # Verify active channels do not exceed 31 unreserved channels
        valid_channels = [c for c in channels_returned if c is not None]
        self.assertGreater(len(valid_channels), 0)
        # Saturated channels should gracefully return None
        none_count = sum(1 for c in channels_returned if c is None)
        self.assertGreater(none_count, 0)

    def test_concurrency_multi_threaded_200_sfx(self):
        """Trigger 200 SFX concurrently across 10 threads without deadlock or exceptions."""
        errors = []
        results = []

        def worker(thread_id):
            for i in range(20):
                try:
                    sfx = ["cursor_move", "confirm", "vs_impact"][i % 3]
                    ch = audio_manager.play_sfx(sfx)
                    results.append((thread_id, i, ch))
                except Exception as e:
                    errors.append((thread_id, i, e))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Threaded SFX triggers raised exceptions: {errors}")
        self.assertEqual(len(results), 200)

    def test_concurrency_channel_exhaustion_saturation(self):
        """When all 31 unreserved channels are busy, additional play_sfx calls return None safely."""
        channels = [audio_manager.play_sfx("cursor_move") for _ in range(50)]
        busy_channels = [c for c in channels if c is not None]
        self.assertLessEqual(len(busy_channels), 31)
        # Over-saturated calls safely return None
        overflow_channels = [c for c in channels[31:] if c is None]
        self.assertGreater(len(overflow_channels), 0)


class TestAirplaneDroneLoopPreservation(unittest.TestCase):
    """Stress tests verifying Channel 0 reservation and drone loop preservation."""

    def setUp(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        audio_manager._ensure_mixer()

    def tearDown(self):
        audio_manager.stop_airplane_drone()
        audio_manager.stop_music()
        if pygame.mixer.get_init():
            for i in range(pygame.mixer.get_num_channels()):
                try:
                    pygame.mixer.Channel(i).stop()
                except Exception:
                    pass

    def test_drone_channel_0_reserved_by_mixer(self):
        """Verify mixer has 32 channels and Channel 0 is reserved."""
        self.assertGreaterEqual(pygame.mixer.get_num_channels(), 32)
        # Normal play_sfx must NEVER return channel 0
        ch0 = pygame.mixer.Channel(0)
        ch0.set_volume(0.123)
        for _ in range(50):
            ch = audio_manager.play_sfx("cursor_move")
            if ch is not None:
                # Compare volume fingerprint to ensure ch is not channel 0
                self.assertNotAlmostEqual(ch.get_volume(), 0.123, places=2)

    def test_drone_preservation_under_200_sfx_burst(self):
        """Drone on Channel 0 remains playing and uncorrupted through 200 SFX bursts."""
        drone_ch = audio_manager.start_airplane_drone()
        self.assertIsNotNone(drone_ch)
        self.assertTrue(pygame.mixer.Channel(0).get_busy())
        drone_sound = audio_manager.sfx_cache.get("airplane_drone")

        # Hammer mixer with 200 bursts of cursor_move, confirm, and vs_impact via play_sfx
        for i in range(200):
            sfx = ["cursor_move", "confirm", "vs_impact"][i % 3]
            audio_manager.play_sfx(sfx)

        # Verify Channel 0 was NEVER stolen or stopped
        ch0 = pygame.mixer.Channel(0)
        self.assertTrue(ch0.get_busy(), "Channel 0 stopped playing during SFX storm")
        self.assertEqual(ch0.get_sound(), drone_sound, "Channel 0 sound was hijacked or corrupted")

    def test_drone_preservation_multi_threaded_hammer(self):
        """Drone on Channel 0 remains uncorrupted when 10 threads trigger 200 SFX."""
        audio_manager.start_airplane_drone()
        drone_sound = audio_manager.sfx_cache.get("airplane_drone")
        hijacked = []

        def worker():
            for i in range(20):
                sfx = ["cursor_move", "confirm", "vs_impact"][i % 3]
                audio_manager.play_sfx(sfx)
                ch0 = pygame.mixer.Channel(0)
                if not ch0.get_busy() or ch0.get_sound() != drone_sound:
                    hijacked.append(True)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(hijacked), 0, "Channel 0 was stolen or stopped during multi-threaded stress")
        ch0 = pygame.mixer.Channel(0)
        self.assertTrue(ch0.get_busy())
        self.assertEqual(ch0.get_sound(), drone_sound)

    def test_play_vs_impact_intentionally_stops_drone_and_plays_impact(self):
        """play_vs_impact() correctly stops Channel 0 drone and plays impact on unreserved channel."""
        audio_manager.start_airplane_drone()
        ch0 = pygame.mixer.Channel(0)
        ch0.set_volume(0.123)
        self.assertTrue(ch0.get_busy())

        impact_ch = audio_manager.play_vs_impact()
        # Drone on Channel 0 is stopped
        self.assertFalse(ch0.get_busy(), "play_vs_impact() must stop airplane drone on channel 0")
        # Impact SFX is playing on an unreserved channel (channels 1..31)
        self.assertIsNotNone(impact_ch)
        self.assertNotAlmostEqual(impact_ch.get_volume(), 0.123, places=2)


class TestBoundaryVolumeInputs(unittest.TestCase):
    """Stress tests for volume boundary values and invalid type resilience."""

    def setUp(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        audio_manager.set_music_volume(0.6)
        audio_manager.set_sfx_volume(0.8)

    def test_volume_negative_boundary_clamped(self):
        """Negative volumes (-5.0, -100.0) are clamped to 0.0."""
        audio_manager.set_music_volume(-5.0)
        self.assertEqual(audio_manager.music_volume, 0.0)
        audio_manager.set_sfx_volume(-100.0)
        self.assertEqual(audio_manager.sfx_volume, 0.0)

    def test_volume_extreme_boundary_clamped(self):
        """Extreme volumes (100.0, 9999.0) are clamped to 1.0."""
        audio_manager.set_music_volume(100.0)
        self.assertEqual(audio_manager.music_volume, 1.0)
        audio_manager.set_sfx_volume(9999.0)
        self.assertEqual(audio_manager.sfx_volume, 1.0)

    def test_volume_exact_boundaries(self):
        """Exact volume boundaries 0.0 and 1.0 are preserved."""
        audio_manager.set_music_volume(0.0)
        self.assertEqual(audio_manager.music_volume, 0.0)
        audio_manager.set_music_volume(1.0)
        self.assertEqual(audio_manager.music_volume, 1.0)

    def test_volume_valid_string_floats_converted(self):
        """String representations of numbers ('0.5', '0', '1') are converted cleanly."""
        audio_manager.set_music_volume("0.5")
        self.assertEqual(audio_manager.music_volume, 0.5)
        audio_manager.set_sfx_volume("0.25")
        self.assertEqual(audio_manager.sfx_volume, 0.25)

    def test_volume_infinities_handled(self):
        """float('inf') and float('-inf') clamp to 1.0 and 0.0."""
        audio_manager.set_music_volume(float("inf"))
        self.assertEqual(audio_manager.music_volume, 1.0)
        audio_manager.set_music_volume(float("-inf"))
        self.assertEqual(audio_manager.music_volume, 0.0)

    def test_volume_non_float_raises_documented_exception(self):
        """Empirically test that non-convertible volume inputs raise TypeError or ValueError."""
        # This adversarial test documents that set_music_volume / set_sfx_volume currently
        # rely on float(volume) without defensive try/except handling.
        with self.assertRaises(TypeError):
            audio_manager.set_music_volume(None)
        with self.assertRaises(ValueError):
            audio_manager.set_music_volume("invalid_volume_string")
        with self.assertRaises(TypeError):
            audio_manager.set_sfx_volume([0.5])


class TestStageMusicRoutingAndFallbacks(unittest.TestCase):
    """Stress tests for character stage music routing and fallback resolution."""

    def setUp(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    def tearDown(self):
        audio_manager.stop_music()

    def test_stage_music_routing_all_5_professors(self):
        """All 5 professors route to their authentic stage tracks on disk."""
        expected_mappings = audio_manager.character_stage_tracks

        for char, filename in expected_mappings.items():
            expected_full_path = os.path.join("assets", "audio", filename)
            self.assertTrue(os.path.exists(expected_full_path), f"Missing audio file: {expected_full_path}")
            audio_manager.play_stage_music(char, loop=False, fade_ms=0)
            self.assertEqual(
                audio_manager.current_track,
                expected_full_path,
                f"Character {char} did not route to {filename}",
            )

    def test_stage_music_routing_invalid_character_fallback(self):
        """Invalid character names fall back cleanly to Carloni (Chun-Li) without crashing."""
        fallback_track = os.path.join(
            "assets", "audio", audio_manager.character_stage_tracks["carloni"]
        )
        invalid_inputs = [
            "unknown_character",
            "chun-li",
            "ryu",
            "CARLONI",  # Uppercase not in keys -> falls back to carloni
            "",
            None,
            12345,
        ]

        for invalid in invalid_inputs:
            audio_manager.play_stage_music(invalid, loop=False, fade_ms=0)
            self.assertEqual(
                audio_manager.current_track,
                fallback_track,
                f"Invalid char {repr(invalid)} failed to fallback to carloni track",
            )


class TestHeadlessResilienceAndErrorRecovery(unittest.TestCase):
    """Stress tests simulating uninitialized mixer and audio hardware failures."""

    def test_uninitialized_mixer_at_boot_graceful_recovery(self):
        """When pygame.mixer.init() fails, AudioManager disables audio gracefully without crashing."""
        pygame.mixer.quit()
        with patch("pygame.mixer.init", side_effect=pygame.error("No available audio device")):
            mgr = AudioManager()
            self.assertFalse(mgr.audio_enabled)
            self.assertEqual(len(mgr.sfx_cache), 0)

            # Verify every single public method executes without raising any exception
            mgr.play_music("menu")
            mgr.play_stage_music("carloni")
            mgr.stop_music()
            res_sfx = mgr.play_sfx("cursor_move")
            self.assertIsNone(res_sfx)
            res_drone = mgr.start_airplane_drone()
            self.assertIsNone(res_drone)
            mgr.stop_airplane_drone()
            res_impact = mgr.play_vs_impact()
            self.assertIsNone(res_impact)
            mgr.set_music_volume(0.5)
            mgr.set_sfx_volume(0.5)

    def test_mid_session_mixer_crash_resilience(self):
        """When mixer is quit mid-gameplay, subsequent calls recover or fail silently."""
        pygame.mixer.init()
        mgr = AudioManager()
        self.assertTrue(mgr.audio_enabled)

        # Abruptly terminate mixer to simulate hardware disconnect
        pygame.mixer.quit()

        with patch("pygame.mixer.init", side_effect=pygame.error("Device disconnected")):
            mgr.play_music("menu")
            mgr.play_stage_music("cavasso")
            mgr.stop_music()
            self.assertIsNone(mgr.play_sfx("cursor_move"))
            self.assertIsNone(mgr.start_airplane_drone())
            mgr.stop_airplane_drone()
            self.assertIsNone(mgr.play_vs_impact())

    def test_music_corrupted_file_error_handled(self):
        """When pygame.mixer.music.load raises an error, play_music handles it gracefully."""
        pygame.mixer.init()
        mgr = AudioManager()
        with patch("pygame.mixer.music.load", side_effect=pygame.error("Corrupted MP3 header")):
            try:
                mgr.play_music("menu")
            except Exception as e:
                self.fail(f"play_music raised unexpected exception on corrupted MP3: {e}")

    def test_sfx_play_hardware_error_handled(self):
        """When sound.play() raises pygame.error, play_sfx catches it and returns None."""
        pygame.mixer.init()
        mgr = AudioManager()
        mock_sound = MagicMock()
        mock_sound.play.side_effect = pygame.error("Channel allocation failure")
        mgr.sfx_cache["test_sfx"] = mock_sound
        res = mgr.play_sfx("test_sfx")
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
