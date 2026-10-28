"""screenshot_manager.py - Sistema de Captura de Pantalla (PS5 Share / F12) para C.C.I. System."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent
CAPTURAS_DIR = ROOT / "capturas"


class ScreenshotManager:
    """Gestor global de capturas de pantalla, sonido de obturador y notificación toast."""
    _instance: ScreenshotManager | None = None

    @classmethod
    def get_instance(cls) -> ScreenshotManager:
        if cls._instance is None:
            cls._instance = ScreenshotManager()
        return cls._instance

    def __init__(self):
        self.toast_filename = ""
        self.toast_until = 0.0
        self.toast_thumb: pygame.Surface | None = None
        self.shutter_sound: pygame.mixer.Sound | None = None
        self._font_bold: pygame.font.Font | None = None
        self._font_regular: pygame.font.Font | None = None
        self._load_shutter()

    def _load_shutter(self):
        shutter_path = ROOT / "assets_ui" / "shutter.wav"
        if shutter_path.is_file() and pygame.mixer.get_init():
            try:
                self.shutter_sound = pygame.mixer.Sound(str(shutter_path))
                self.shutter_sound.set_volume(0.85)
            except Exception as exc:
                print(f"[ScreenshotManager] Audio obturador no cargado: {exc}")

    def take_screenshot(self, surface: pygame.Surface | None = None) -> str | None:
        """Captura la pantalla actual, reproduce sonido de cámara y lanza notificación."""
        if surface is None:
            surface = pygame.display.get_surface()
        if surface is None:
            return None

        # Sonido de obturador mecánico
        if self.shutter_sound is not None:
            try:
                self.shutter_sound.play()
            except Exception:
                pass

        CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captura_{timestamp}.png"
        filepath = CAPTURAS_DIR / filename

        try:
            pygame.image.save(surface, str(filepath))
            print(f"[ScreenshotManager] Captura guardada con éxito: {filepath}")

            # Generar miniatura para notificación PS5
            sw, sh = surface.get_size()
            aspect = sw / max(1, sh)
            thumb_h = 44
            thumb_w = int(thumb_h * aspect)
            self.toast_thumb = pygame.transform.smoothscale(surface, (thumb_w, thumb_h))
            self.toast_filename = filename
            self.toast_until = time.monotonic() + 3.2
            return str(filepath)
        except Exception as exc:
            print(f"[ScreenshotManager] Error al guardar captura: {exc}")
            return None

    def draw_overlay(self, screen: pygame.Surface):
        """Superpone banner emergente estilo PS5 con miniatura y texto brillante."""
        now = time.monotonic()
        if now >= self.toast_until:
            return

        remaining = self.toast_until - now
        total_time = 3.2
        # Entrada suave (0.3s) y salida suave (0.5s)
        if remaining < 0.5:
            alpha = int(255 * (remaining / 0.5))
        elif (total_time - remaining) < 0.3:
            alpha = int(255 * ((total_time - remaining) / 0.3))
        else:
            alpha = 255

        banner_w, banner_h = 370, 58
        banner_x = screen.get_width() - banner_w - 20
        banner_y = 20

        overlay = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        # Fondo oscuro translúcido
        pygame.draw.rect(overlay, (10, 14, 22, int(235 * (alpha / 255))), (0, 0, banner_w, banner_h), border_radius=8)
        # Borde cian PS5
        pygame.draw.rect(overlay, (0, 229, 255, int(220 * (alpha / 255))), (0, 0, banner_w, banner_h), 2, border_radius=8)

        # Miniatura capturada
        thumb_x = 8
        if self.toast_thumb is not None:
            overlay.blit(self.toast_thumb, (thumb_x, 7))
            pygame.draw.rect(overlay, (255, 255, 255, int(180 * (alpha / 255))), (thumb_x, 7, self.toast_thumb.get_width(), 44), 1)
            thumb_x += self.toast_thumb.get_width() + 10

        if self._font_bold is None:
            self._font_bold = pygame.font.SysFont("Helvetica,Arial", 12, bold=True)
            self._font_regular = pygame.font.SysFont("Helvetica,Arial", 11)

        title_surf = self._font_bold.render("📸 CAPTURA GUARDADA", True, (0, 229, 255))
        sub_surf = self._font_regular.render(self.toast_filename, True, (230, 235, 245))
        loc_surf = self._font_regular.render("Guardado en carpeta capturas/", True, (150, 155, 165))

        overlay.blit(title_surf, (thumb_x, 8))
        overlay.blit(sub_surf, (thumb_x, 24))
        overlay.blit(loc_surf, (thumb_x, 39))

        screen.blit(overlay, (banner_x, banner_y))

    @staticmethod
    def get_capture_count() -> int:
        if not CAPTURAS_DIR.is_dir():
            return 0
        return sum(1 for p in CAPTURAS_DIR.glob("*.png"))

    @staticmethod
    def open_capturas_folder():
        CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(CAPTURAS_DIR)], check=False)
            elif sys.platform == "win32":
                os.startfile(str(CAPTURAS_DIR))
            else:
                subprocess.run(["xdg-open", str(CAPTURAS_DIR)], check=False)
        except Exception as exc:
            print(f"[ScreenshotManager] Error abriendo carpeta de capturas: {exc}")
