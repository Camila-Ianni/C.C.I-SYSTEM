"""
audio_manager.py - Gestor centralizado de audio y motor de síntesis procedimental arcade.
Soporta:
- Síntesis de SFX arcade en memoria mediante numpy y pygame.sndarray (cursor, confirmación, drone de avión, impacto VS).
- Mapeo dedicado de música de escenarios CPS1 por profesor.
- Transiciones suaves (fade_ms) y tolerancia total a entornos sin audio / SDL_AUDIODRIVER=dummy.
"""

import os
import random
import pygame
import numpy as np


class AudioManager:
    """
    Gestor de audio de alta fidelidad para Da Vinci Fighters.
    """
    def __init__(self, audio_dir=None):
        if audio_dir is None:
            self.audio_dir = os.path.join("assets", "audio")
        else:
            self.audio_dir = audio_dir

        self.current_track = None
        self.music_volume = 0.6
        self.sfx_volume = 0.8
        self.sfx_cache = {}
        self.drone_channel = None
        self.audio_enabled = True

        # Pistas principales de interfaz y secuencias
        self.music_tracks = {
            "menu": "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3",
            "opening": "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3",
            "title": "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3",
            "character_select": "(SEGA) Street Fighter II SCE Music - Character Select.mp3",
            "select": "(SEGA) Street Fighter II SCE Music - Character Select.mp3",
            "victory": "(SEGA) Street Fighter II SCE Music - Staff Roll (Credits).mp3",
            "credits": "(SEGA) Street Fighter II SCE Music - Staff Roll (Credits).mp3",
            "bonus": "(SEGA) Street Fighter II SCE Music - Bonus Stage.mp3",
        }

        # Pistas oficiales asignadas a cada profesor
        self.character_stage_tracks = {
            "carloni": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "cavasso": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
            "romero": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "gamaliel": "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3",
            "sellanes": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
        }

        # Mapeo exhaustivo de canciones oficiales de fondos de pelea (SEGA Genesis / Arcade)
        self.stage_music_mapping = {
            # Blanka Stage (Brasil - Río Amazonas)
            "blanka": "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3",
            "gamaliel": "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3",
            "brazil": "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3",
            "amazon": "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3",

            # Guile Stage (USA - Base Aérea / Hangar militar)
            "guile": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
            "cavasso": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
            "airbase": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
            "hangar": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
            "usa_low": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",
            "usa_guile": "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3",

            # M. Bison Stage (Final Boss / URSS Fábrica / Sellanes)
            "bison": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "m_bison": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "m bison": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "mbison": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "sellanes": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "ussr": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "urss": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "russia": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",
            "zangief": "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3",

            # Ryu Stage (Japón - Castillo Suzaku / Ken Muelle)
            "ryu": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "carloni": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "japan": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "suzaku": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "ken": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "usa": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "usa_up": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "usa_ken": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "harbor": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "port": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "china": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",
            "chunli": "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3",

            # Sagat Stage (Tailandia - Templo Ayutthaya / Romero / E. Honda Baño Público / India Dhalsim)
            "sagat": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "romero": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "thailand": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "honda": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "ehonda": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "japan_up": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "bathhouse": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "sento": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "india": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
            "dhalsim": "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3",
        }

        # Lista de fallback para pistas de combate genéricas
        self.fight_tracks = list(self.character_stage_tracks.values())

        # Inicialización segura
        self._ensure_mixer()
        self._init_procedural_sfx()

    def _ensure_mixer(self):
        """Inicializa pygame.mixer si aún no está activo, expandiendo a 32 canales."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2)
                pygame.mixer.set_num_channels(32)
                pygame.mixer.set_reserved(1)  # Canal 0 reservado para el drone de avión continuo
                self.audio_enabled = True
            except Exception as e:
                self.audio_enabled = False
                print(f"[AudioManager] Audio mixer no disponible: {e}")
        else:
            try:
                if pygame.mixer.get_num_channels() < 32:
                    pygame.mixer.set_num_channels(32)
                pygame.mixer.set_reserved(1)
            except Exception:
                pass

    def _init_procedural_sfx(self):
        """
        Sintetiza en memoria los efectos de sonido arcade mediante numpy y sndarray.
        Evita dependencias de archivos externos para la interacción UI y transiciones.
        """
        if not self.audio_enabled or not pygame.mixer.get_init():
            return

        try:
            init_info = pygame.mixer.get_init()
            if not init_info:
                return
            sample_rate, fmt, channels = init_info

            def to_sound(mono_wave):
                """Convierte una onda normalizada [-1.0, 1.0] a pygame.mixer.Sound PCM-16."""
                mono_clamped = np.clip(mono_wave, -0.98, 0.98)
                pcm16 = (mono_clamped * 32767).astype(np.int16)
                if channels == 1:
                    arr = pcm16
                elif channels == 2:
                    arr = np.column_stack((pcm16, pcm16))
                else:
                    arr = np.tile(pcm16[:, np.newaxis], (1, channels))
                sound = pygame.sndarray.make_sound(arr)
                sound.set_volume(self.sfx_volume)
                return sound

            # 1. cursor_move: Blip arcade 8-bit rápido (440 Hz square wave, 40ms, decaimiento)
            dur_c = 0.040
            n_c = int(sample_rate * dur_c)
            t_c = np.linspace(0, dur_c, n_c, False)
            decay_c = np.linspace(1.0, 0.0, n_c) ** 1.8
            w_cursor = 0.35 * np.sign(np.sin(2 * np.pi * 440 * t_c)) * decay_c
            snd_cursor = to_sound(w_cursor)
            self.sfx_cache["cursor_move"] = snd_cursor
            self.sfx_cache["menu_navigate"] = snd_cursor

            # 2. confirm: Doble campana brillante (660 Hz -> 880 Hz, 120ms total)
            dur_cf = 0.120
            n_half = int(sample_rate * (dur_cf / 2))
            t_half = np.linspace(0, dur_cf / 2, n_half, False)
            decay_h = np.exp(-22 * t_half)
            w1 = (0.35 * np.sin(2 * np.pi * 660 * t_half) + 0.12 * np.sign(np.sin(2 * np.pi * 660 * t_half))) * decay_h
            w2 = (0.40 * np.sin(2 * np.pi * 880 * t_half) + 0.15 * np.sign(np.sin(2 * np.pi * 880 * t_half))) * decay_h
            snd_confirm = to_sound(np.concatenate((w1, w2)))
            self.sfx_cache["confirm"] = snd_confirm
            self.sfx_cache["select"] = snd_confirm
            self.sfx_cache["menu_confirm"] = snd_confirm

            # 3. airplane_drone: Zumbido de motor continuo en loop (120-180 Hz modulado, 0.5s)
            dur_d = 0.500
            n_d = int(sample_rate * dur_d)
            t_d = np.linspace(0, dur_d, n_d, False)
            phase_d = 2 * np.pi * 145 * t_d - (25.0 / 6.0) * np.cos(2 * np.pi * 6 * t_d)
            carrier = 0.28 * np.sin(phase_d) + 0.12 * np.sin(2 * phase_d)
            sub = 0.20 * np.sin(2 * np.pi * 72.5 * t_d)
            flutter = 0.04 * np.random.uniform(-1, 1, n_d)
            w_drone = carrier + sub + flutter
            # Micro-crossfade en los bordes para loop sin saltos
            fade_samples = int(0.01 * sample_rate)
            win = np.linspace(0, 1, fade_samples)
            w_drone[:fade_samples] = w_drone[:fade_samples] * win + w_drone[-fade_samples:] * (1 - win)
            w_drone[-fade_samples:] = w_drone[:fade_samples]
            w_drone = w_drone - np.mean(w_drone)
            self.sfx_cache["airplane_drone"] = to_sound(w_drone * 0.55)

            # 4. vs_impact: Impacto arcade contundente (bass thump con pitch glide 160->42 Hz + crash de ruido)
            dur_i = 0.550
            n_i = int(sample_rate * dur_i)
            t_i = np.linspace(0, dur_i, n_i, False)
            freq_glide = 42.0 + 118.0 * np.exp(-18 * t_i)
            phase_glide = 2 * np.pi * np.cumsum(freq_glide) / sample_rate
            thump = 0.65 * np.sin(phase_glide) * np.exp(-7 * t_i)
            noise = np.random.uniform(-1, 1, n_i)
            crash = 0.40 * noise * np.exp(-24 * t_i) + 0.15 * noise * np.exp(-9 * t_i)
            self.sfx_cache["vs_impact"] = to_sound(thump + crash)

            # 5. coin / insert coin: Sonido de inserción de crédito desde assets/audio/Sounds/insert coin.mp3
            snd_coin = None
            coin_path = os.path.join(self.audio_dir, "Sounds", "insert coin.mp3")
            if os.path.exists(coin_path):
                try:
                    snd_coin = pygame.mixer.Sound(coin_path)
                    snd_coin.set_volume(self.sfx_volume)
                except Exception as e:
                    print(f"[AudioManager] Fallback en carga de insert coin.mp3: {e}")

            if snd_coin is None:
                # Fallback procedimental clásico de doble campana arcade (987 Hz -> 1318 Hz)
                dur_cn = 0.180
                n_cn_half = int(sample_rate * (dur_cn / 2))
                t_cn1 = np.linspace(0, dur_cn / 2, n_cn_half, False)
                t_cn2 = np.linspace(0, dur_cn / 2, n_cn_half, False)
                decay_cn = np.exp(-16 * t_cn1)
                w_coin1 = (0.50 * np.sin(2 * np.pi * 987.77 * t_cn1) + 0.25 * np.sin(2 * np.pi * 1975.53 * t_cn1)) * decay_cn
                w_coin2 = (0.60 * np.sin(2 * np.pi * 1318.51 * t_cn2) + 0.30 * np.sin(2 * np.pi * 2637.02 * t_cn2)) * decay_cn
                snd_coin = to_sound(np.concatenate((w_coin1, w_coin2)))

            self.sfx_cache["coin"] = snd_coin
            self.sfx_cache["credit"] = snd_coin
            self.sfx_cache["insert coin"] = snd_coin

            # 6. crate_break / wood_smash: Fractura contundente de madera (crunch de ruido + golpe sordo 140->50 Hz + astillas)
            dur_crk = 0.280
            n_crk = int(sample_rate * dur_crk)
            t_crk = np.linspace(0, dur_crk, n_crk, False)
            noise_crk = np.random.uniform(-1, 1, n_crk)
            decay_n = np.exp(-26 * t_crk)
            freq_crk = 140.0 * np.exp(-14 * t_crk) + 50.0
            thud_crk = np.sin(2 * np.pi * freq_crk * t_crk) * np.exp(-16 * t_crk)
            click_crk = np.sin(2 * np.pi * 1200 * t_crk) * np.exp(-70 * t_crk)
            w_crate = 0.45 * noise_crk * decay_n + 0.45 * thud_crk + 0.20 * click_crk
            snd_crate = to_sound(w_crate * 0.9)
            self.sfx_cache["crate_break"] = snd_crate
            self.sfx_cache["wood_smash"] = snd_crate
            self.sfx_cache["insert_coin"] = snd_coin

        except Exception as e:
            print(f"[AudioManager] Error generando SFX procedimentales: {e}")

    def play_music(self, theme_name="menu", loop=True, fade_ms=500):
        """
        Reproduce una pista de música con soporte para desvanecimiento y bucle.
        Acepta tanto bool como int en `loop` para compatibilidad total.
        """
        if not self.audio_enabled:
            return
        self._ensure_mixer()
        if not pygame.mixer.get_init():
            return

        file_name = None
        if theme_name in self.music_tracks:
            file_name = self.music_tracks[theme_name]
        elif theme_name in self.character_stage_tracks:
            file_name = self.character_stage_tracks[theme_name]
        elif theme_name == "fight":
            file_name = random.choice(self.fight_tracks)
        else:
            # Si se pasa un nombre de archivo directo o ruta
            if os.path.exists(os.path.join(self.audio_dir, theme_name)):
                file_name = theme_name

        if not file_name:
            return

        file_path = os.path.join(self.audio_dir, file_name)

        # Evitar reiniciar la misma pista si ya se encuentra sonando
        if self.current_track == file_path and pygame.mixer.music.get_busy():
            return

        if not os.path.exists(file_path):
            print(f"[AudioManager] Pista de audio no encontrada: {file_path}")
            return

        loops = -1 if (isinstance(loop, bool) and loop) or loop == -1 else (0 if not loop else int(loop))

        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(self.music_volume)
            if fade_ms and fade_ms > 0:
                pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            else:
                pygame.mixer.music.play(loops=loops)
            self.current_track = file_path
        except Exception as e:
            print(f"[AudioManager] Error reproduciendo {file_path}: {e}")

    def play_stage_music(self, char_or_stage, loop=True, fade_ms=500):
        """Reproduce la pista arcade oficial del escenario según personaje o ID de escenario."""
        key = str(char_or_stage).lower() if char_or_stage else "carloni"
        file_name = self.stage_music_mapping.get(key)
        if not file_name:
            file_name = self.character_stage_tracks.get(key, "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3")
        self.play_music(file_name, loop=loop, fade_ms=fade_ms)

    def stop_music(self, fade_ms=0):
        """Detiene la música actual de forma inmediata o con fadeout suave."""
        if not pygame.mixer.get_init():
            return
        try:
            if fade_ms and fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
            self.current_track = None
        except Exception as e:
            print(f"[AudioManager] Error deteniendo musica: {e}")

    def play_sfx(self, sfx_name, loop=False):
        """Reproduce un efecto de sonido corto mediante cache en memoria o archivo en disco."""
        if not self.audio_enabled or not pygame.mixer.get_init():
            return None

        sound = self.sfx_cache.get(sfx_name)
        if not sound:
            candidates = [
                os.path.join(self.audio_dir, sfx_name),
                os.path.join(self.audio_dir, "Sounds", sfx_name),
                os.path.join(self.audio_dir, "Sounds", sfx_name.replace("_", " ")),
                os.path.join(self.audio_dir, "Sounds", sfx_name.replace(" ", "_")),
            ]
            for c in candidates:
                for ext in ["", ".mp3", ".wav"]:
                    p = c + ext
                    if os.path.isfile(p):
                        try:
                            sound = pygame.mixer.Sound(p)
                            sound.set_volume(self.sfx_volume)
                            self.sfx_cache[sfx_name] = sound
                            break
                        except Exception:
                            pass
                if sound:
                    break

        if sound:
            try:
                loops = -1 if loop else 0
                return sound.play(loops=loops)
            except Exception as e:
                print(f"[AudioManager] Error reproduciendo SFX {sfx_name}: {e}")
                return None
        return None

    def start_airplane_drone(self):
        """Inicia el zumbido continuo del motor en el canal 0 reservado."""
        if not self.audio_enabled or not pygame.mixer.get_init():
            return None

        sound = self.sfx_cache.get("airplane_drone")
        if sound:
            try:
                ch0 = pygame.mixer.Channel(0)
                if ch0.get_busy() and ch0.get_sound() == sound:
                    return ch0
                ch0.play(sound, loops=-1)
                self.drone_channel = ch0
                return ch0
            except Exception as e:
                print(f"[AudioManager] Error iniciando drone: {e}")
                return None
        return None

    def stop_airplane_drone(self):
        """Detiene inmediatamente el motor del avión en el canal 0 reservado."""
        if not pygame.mixer.get_init():
            return
        try:
            ch0 = pygame.mixer.Channel(0)
            ch0.stop()
        except Exception:
            pass
        self.drone_channel = None

    def play_vs_impact(self):
        """Detiene el avión y reproduce el impacto 'VS' contundente."""
        self.stop_airplane_drone()
        return self.play_sfx("vs_impact")

    def set_music_volume(self, volume):
        """Ajusta el volumen de la música (0.0 a 1.0)."""
        self.music_volume = max(0.0, min(1.0, float(volume)))
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

    def set_sfx_volume(self, volume):
        """Ajusta el volumen global de los SFX (0.0 a 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, float(volume)))
        for sound in self.sfx_cache.values():
            if sound:
                try:
                    sound.set_volume(self.sfx_volume)
                except Exception:
                    pass


# Instancia singleton global del gestor de audio
audio_manager = AudioManager()
