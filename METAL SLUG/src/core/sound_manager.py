"""
Modular Sound Manager for Metal Slug 1 (Phase 9 Complete).
Manages:
- Dedicated audio channels: Player SFX, Explosions/Tanks, Announcer/Voices, Enemy SFX.
- Background Music (BGM) tracks 01 through 13 for each stage, boss, menu and ending.
- Announcer voice lines: "Heavy Machine Gun!", "Shotgun!", "Rocket Launcher!",
  "Flame Shot!", "Mission Complete!", "OK!", "Thank You!", Soldier screams.
"""
import os
import pygame

class SoundManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, sfx_dir="Assets/Sounds/VOICE", music_dir="Assets/Sounds/Music"):
        if self._initialized:
            return
        self._initialized = True
        
        self.sfx_dir = sfx_dir
        self.music_dir = music_dir
        self.sounds = {}
        self.current_bgm = None
        self.is_audio_available = False
        
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.channel_player = pygame.mixer.Channel(0)
            self.channel_explosions = pygame.mixer.Channel(1)
            self.channel_voice = pygame.mixer.Channel(2)
            self.channel_enemies = pygame.mixer.Channel(3)
            self.is_audio_available = True
            
            self.preload_voices()
        except Exception as e:
            print(f"[SoundManager] Audio initialization skipped or muted: {e}")

    def preload_voices(self):
        """Preloads standard voice clips and sound effects."""
        voice_files = {
            "heavy_machine_gun": "voice_heavy_machine_gun.mp3",
            "shotgun": "voice_shotgun.mp3",
            "rocket_launcher": "voice_rocket_launcher.mp3",
            "flame_shot": "voice_flame_shot.mp3",
            "grenade": "voice_grenade.mp3",
            "thank_you": "voice_thank_you.mp3",
            "ok": "voice_ok.mp3",
            "mission_complete": "voice_mission_complete.mp3",
            "scream": "voice_scream.mp3",
            "bingo": "sfx_bingo.mp3",
            "minigun": "sfx_minigun.mp3"
        }
        for name, filename in voice_files.items():
            path = os.path.join(self.sfx_dir, filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except Exception:
                    self.sounds[name] = None
            else:
                self.sounds[name] = None

        # Preload synthesized weapon SFX
        try:
            from src.core.sfx_synth import generate_weapon_sfx
            synth_sfx = generate_weapon_sfx()
            for sname, snd_obj in synth_sfx.items():
                self.sounds[sname] = snd_obj
        except Exception as e:
            print(f"[SoundManager] Synthesized audio skipped: {e}")

    def play_sound(self, name, channel_name="player", volume=1.0):
        """Plays a preloaded sound on the designated channel without blocking."""
        if not self.is_audio_available:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        
        snd.set_volume(volume)
        ch = {
            "player": self.channel_player,
            "explosion": self.channel_explosions,
            "voice": self.channel_voice,
            "enemy": self.channel_enemies,
        }.get(channel_name, self.channel_player)
        
        try:
            ch.play(snd)
        except Exception:
            pass

    def play_voice(self, name, volume=1.0):
        self.play_sound(name, channel_name="voice", volume=volume)

    # Voice Announcer Triggers
    def play_announcer_weapon(self, weapon_type):
        mapping = {
            "H": "heavy_machine_gun",
            "S": "shotgun",
            "R": "rocket_launcher",
            "F": "flame_shot",
            "BOMB": "grenade",
            "GAS": "bingo",
            "FOOD": "bingo",
        }
        snd_name = mapping.get(weapon_type)
        if snd_name:
            self.play_voice(snd_name, volume=1.0)

    def play_pow_thank_you(self):
        self.play_voice("thank_you", volume=1.0)

    def play_slug_ok(self):
        self.play_voice("ok", volume=1.0)

    def play_mission_complete_voice(self):
        self.play_voice("mission_complete", volume=1.0)

    def play_soldier_scream(self):
        self.play_sound("scream", channel_name="enemy", volume=0.85)

    def play_vulcan_fire(self):
        self.play_sound("minigun", channel_name="player", volume=0.7)

    def play_explosion(self):
        self.play_sound("grenade", channel_name="explosion", volume=0.9)

    # Background Music (BGM) Handlers
    def play_music(self, relative_path, loop=-1, volume=0.65):
        """Plays a background music track if available."""
        if not self.is_audio_available:
            return
        full_path = os.path.join(self.music_dir, relative_path)
        if full_path == self.current_bgm:
            return  # Already playing this track
        if os.path.exists(full_path):
            try:
                pygame.mixer.music.load(full_path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(loop)
                self.current_bgm = full_path
            except Exception as e:
                print(f"[SoundManager] Music load error: {e}")

    def stop_music(self):
        if self.is_audio_available:
            try:
                pygame.mixer.music.stop()
                self.current_bgm = None
            except Exception:
                pass

    def play_title_bgm(self):
        self.play_music("01_title.mp3", loop=-1, volume=0.65)

    def play_char_select_bgm(self):
        self.play_music("02_how_to_play.mp3", loop=-1, volume=0.65)

    def play_mission_bgm(self, mission_num):
        track_map = {
            1: "03_mission1.mp3",
            2: "06_mission2.mp3",
            3: "07_mission3.mp3",
            4: "08_mission4.mp3",
            5: "09_mission5.mp3",
            6: "10_mission6.mp3",
        }
        track = track_map.get(mission_num, "03_mission1.mp3")
        self.play_music(track, loop=-1, volume=0.65)

    def play_boss_bgm(self):
        self.play_music("04_boss.mp3", loop=-1, volume=0.7)

    def play_stage_clear_bgm(self):
        self.play_music("05_stage_clear.mp3", loop=0, volume=0.75)

    def play_game_over_bgm(self):
        self.play_music("13_game_over.mp3", loop=0, volume=0.75)

    def play_victory_bgm(self):
        self.play_music("11_ending_1p.mp3", loop=-1, volume=0.7)
