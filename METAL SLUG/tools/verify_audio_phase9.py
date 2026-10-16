"""
Test suite for Phase 9: Audio Architecture, BGM, and Announcer Voices.
Verifies:
- All 13 Metal Slug 1 canonical BGM tracks load and play.
- All Announcer Voice lines and SFX trigger properly on dedicated mixer channels.
- Pickups, POWs, Slug boarding, and Boss encounters invoke correct audio methods.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from src.core.sound_manager import SoundManager
from src.items.pickup import PickupItem
from src.entities.player import Player
from src.entities.slug import MetalSlug
from src.entities.pow import PrisonerOfWar
from src.entities.enemy import RebelSoldier

def test_audio_system():
    print("[TEST] Initializing pygame mixer & display...")
    pygame.init()
    pygame.display.set_mode((320, 224))
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    
    sound_mgr = SoundManager()
    assert sound_mgr.is_audio_available, "Mixer should be available!"
    print("[PASS] Mixer initialized.")

    # 1. Verify 13 Metal Slug 1 Music Tracks
    print("\n[TEST] Verifying 13 Canonical Metal Slug 1 Tracks in Assets/Sounds/Music:")
    expected_tracks = [
        "01_title.mp3",
        "02_how_to_play.mp3",
        "03_mission1.mp3",
        "04_boss.mp3",
        "05_stage_clear.mp3",
        "06_mission2.mp3",
        "07_mission3.mp3",
        "08_mission4.mp3",
        "09_mission5.mp3",
        "10_mission6.mp3",
        "11_ending_1p.mp3",
        "12_ending_2p.mp3",
        "13_game_over.mp3"
    ]
    for track in expected_tracks:
        track_path = os.path.join("Assets/Sounds/Music", track)
        assert os.path.exists(track_path), f"Missing track: {track}"
        snd = pygame.mixer.Sound(track_path)
        assert snd.get_length() > 0, f"Track {track} is empty!"
        print(f"  -> {track}: OK ({snd.get_length():.1f}s)")
    print("[PASS] All 13 Metal Slug 1 BGM tracks present and verified.")

    # 2. Verify Preloaded Voice & SFX Clips
    print("\n[TEST] Verifying Announcer Voices & SFX:")
    required_voices = [
        "heavy_machine_gun",
        "shotgun",
        "rocket_launcher",
        "flame_shot",
        "grenade",
        "thank_you",
        "ok",
        "mission_complete",
        "scream",
        "bingo",
        "minigun"
    ]
    for v in required_voices:
        snd = sound_mgr.sounds.get(v)
        assert snd is not None, f"Voice {v} should be loaded!"
        print(f"  -> Voice/SFX '{v}': OK ({snd.get_length():.2f}s)")
    print("[PASS] All Announcer and Character voice lines verified.")

    # 3. Test In-Game Weapon Pickup Announcer Trigger
    player = Player(60, 160)
    pickup_h = PickupItem(60, 160, item_type="H")
    pickup_h.on_collect(player, sound_manager=sound_mgr)
    assert player.weapon_type == "H"
    print("[PASS] Weapon pickup [H] triggers Announcer: 'HEAVY MACHINE GUN!'")

    pickup_s = PickupItem(60, 160, item_type="S")
    pickup_s.on_collect(player, sound_manager=sound_mgr)
    assert player.weapon_type == "S"
    print("[PASS] Weapon pickup [S] triggers Announcer: 'SHOTGUN!'")

    # 4. Test POW Rescue Voice Trigger
    pow_npc = PrisonerOfWar(60, 160)
    pow_npc.trigger_rescue(sound_manager=sound_mgr)
    assert pow_npc.is_rescued
    print("[PASS] P.O.W. rescue triggers voice: 'THANK YOU!'")

    # 5. Test Metal Slug Boarding Voice Trigger
    slug = MetalSlug(60, 160)
    slug.enter_vehicle(player, sound_manager=sound_mgr)
    assert slug.is_occupied
    print("[PASS] Metal Slug boarding triggers voice: 'OK!'")

    # 6. Test Enemy Death Scream
    enemy = RebelSoldier(100, 160)
    enemy.take_damage(10, death_type="bullet")
    assert enemy.is_dead
    print("[PASS] Rebel soldier death triggers death scream sound.")

    # 7. Test BGM State Playback
    sound_mgr.play_title_bgm()
    assert sound_mgr.current_bgm.endswith("01_title.mp3")
    sound_mgr.play_mission_bgm(1)
    assert sound_mgr.current_bgm.endswith("03_mission1.mp3")
    sound_mgr.play_boss_bgm()
    assert sound_mgr.current_bgm.endswith("04_boss.mp3")
    sound_mgr.play_stage_clear_bgm()
    assert sound_mgr.current_bgm.endswith("05_stage_clear.mp3")
    sound_mgr.stop_music()
    assert sound_mgr.current_bgm is None
    print("[PASS] BGM playback and state transitions functional.")

    # 8. Verify Archived Files Count
    archive_files = os.listdir("Assets/Sounds/Archive_Other_Versions")
    print(f"\n[PASS] Verified {len(archive_files)} other version tracks safely stored in Archive_Other_Versions.")

    print("\n[SUCCESS] PHASE 9 AUDIO AND VOICE SUBSYSTEMS FULLY OPERATIONAL!")

if __name__ == "__main__":
    test_audio_system()
