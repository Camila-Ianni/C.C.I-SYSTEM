"""audio_bgm.py - Gestor de música ambiental BGM (PS5-Style) para C.C.I. System."""
from __future__ import annotations

import os
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent


class BGMManager:
    """Controlador central de música de fondo ambiental del menú."""
    _instance: BGMManager | None = None

    @classmethod
    def get_instance(cls) -> BGMManager:
        if cls._instance is None:
            cls._instance = BGMManager()
        return cls._instance

    def __init__(self):
        self.current_track: str | None = None
        self.is_playing: bool = False
        self.target_volume: float = 0.8
        self.muted: bool = False

    def play_ambient(self, volume: float | None = None, fade_ms: int = 1000):
        if not pygame.mixer.get_init():
            return
        if volume is not None:
            self.target_volume = max(0.0, min(1.0, float(volume)))
        if self.target_volume <= 0.001:
            self.fadeout(300)
            return

        bgm_path = ROOT / "assets_ui" / "ambient_bgm.wav"
        if not bgm_path.is_file():
            return
        track_str = str(bgm_path)
        try:
            if not self.is_playing or self.current_track != track_str or not pygame.mixer.music.get_busy():
                pygame.mixer.music.load(track_str)
                pygame.mixer.music.set_volume(self.target_volume)
                pygame.mixer.music.play(loops=-1, fade_ms=fade_ms)
                self.is_playing = True
                self.current_track = track_str
            else:
                pygame.mixer.music.set_volume(self.target_volume)
        except Exception as exc:
            print(f"[BGMManager] Error al reproducir audio ambiental: {exc}")

    def fadeout(self, ms: int = 500):
        if not pygame.mixer.get_init():
            return
        try:
            if self.is_playing or pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(ms)
                self.is_playing = False
        except Exception as exc:
            print(f"[BGMManager] Error al desvanecer audio ambiental: {exc}")

    def set_volume(self, volume: float):
        self.target_volume = max(0.0, min(1.0, float(volume)))
        if pygame.mixer.get_init() and self.is_playing:
            try:
                if self.target_volume <= 0.001:
                    self.fadeout(200)
                else:
                    pygame.mixer.music.set_volume(self.target_volume)
            except Exception:
                pass
