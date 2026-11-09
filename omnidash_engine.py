"""omnidash_engine.py - Motor Base Unificado estilo OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE.
Soporta:
- Arquitectura Dark Glass moderna a 1280x720 / 60 FPS.
- 4 Temas completos con fondos procedurales: PlayStation 4, Frutiger Aero, Helix Dark Glass y Xbox Series.
- Barra superior de estado (Perfil, Gamerscore, Ticker de notificaciones, Reloj).
- Barra inferior de control (Leyenda universal de mandos y teclado).
- Gestor universal de entrada: Ratón (hover/clic), Teclado y Mando (con hotplugging).
- Sistema de audio nativo con efectos de sonido de consola.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import datetime
import math
import os
import sys
import time
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

# Definición de Temas OmniDash
THEMES = {
    "ps4": {
        "id": "ps4",
        "name": "PlayStation 4",
        "bg_base": (14, 108, 196),
        "accent": (0, 162, 255),
        "panel_bg": (15, 24, 40, 225),
        "card_bg": (20, 32, 54, 230),
        "card_hover": (34, 52, 85, 245),
        "text_primary": (255, 255, 255),
        "text_secondary": (180, 205, 235),
        "focus_glow": (255, 255, 255),
    },
    "aero": {
        "id": "aero",
        "name": "Frutiger Aero",
        "bg_base": (2, 136, 209),
        "accent": (79, 195, 247),
        "panel_bg": (255, 255, 255, 120),
        "card_bg": (255, 255, 255, 160),
        "card_hover": (255, 255, 255, 210),
        "text_primary": (10, 30, 50),
        "text_secondary": (30, 70, 100),
        "focus_glow": (255, 255, 255),
    },
    "helix": {
        "id": "helix",
        "name": "Helix (Dark Glass)",
        "bg_base": (12, 14, 20),
        "accent": (147, 51, 234),
        "panel_bg": (20, 24, 34, 230),
        "card_bg": (28, 34, 48, 230),
        "card_hover": (45, 54, 76, 245),
        "text_primary": (250, 250, 255),
        "text_secondary": (165, 175, 200),
        "focus_glow": (168, 85, 247),
    },
    "xbox": {
        "id": "xbox",
        "name": "Xbox Series",
        "bg_base": (16, 22, 26),
        "accent": (16, 160, 68),
        "panel_bg": (24, 32, 38, 230),
        "card_bg": (32, 42, 50, 230),
        "card_hover": (48, 62, 74, 245),
        "text_primary": (255, 255, 255),
        "text_secondary": (175, 195, 185),
        "focus_glow": (16, 200, 80),
    },
}


class OmniDashEngine:
    """Motor unificado de interfaz tipo consola para C.C.I. SYSTEM."""

    def __init__(self, screen_w: int = 1280, screen_h: int = 720, active_theme: str = "ps4"):
        self.w = screen_w
        self.h = screen_h
        self.active_theme_id = active_theme if active_theme in THEMES else "ps4"
        self.theme = THEMES[self.active_theme_id]

        self.anim_timer = 0.0
        self.particles: list[dict] = []
        self._init_particles()

        # Fuentes oficiales SST o sistema
        font_path = ROOT / "assets_ps4" / "font" / "sst.ttf"
        font_file = str(font_path) if font_path.exists() else None

        pygame.font.init()
        try:
            self.font_title = pygame.font.Font(font_file, 26)
            self.font_body = pygame.font.Font(font_file, 16)
            self.font_sub = pygame.font.Font(font_file, 14)
            self.font_badge = pygame.font.Font(font_file, 12)
            self.font_clock = pygame.font.Font(font_file, 17)
            self.font_btn = pygame.font.Font(font_file, 13)
        except Exception:
            self.font_title = pygame.font.SysFont("Helvetica, Arial", 26, bold=True)
            self.font_body = pygame.font.SysFont("Helvetica, Arial", 16, bold=True)
            self.font_sub = pygame.font.SysFont("Helvetica, Arial", 14)
            self.font_badge = pygame.font.SysFont("Courier, monospace", 12, bold=True)
            self.font_clock = pygame.font.SysFont("Helvetica, Arial", 17, bold=True)
            self.font_btn = pygame.font.SysFont("Helvetica, Arial", 13, bold=True)

        # Sonidos oficiales
        self.sfx = {}
        for sname in ("navigate.mp3", "reward.mp3", "startup.mp3", "shutdown.mp3"):
            sp = ROOT / "assets_ps4" / "audio" / sname
            if sp.exists() and pygame.mixer.get_init():
                try:
                    self.sfx[sname.split(".")[0]] = pygame.mixer.Sound(str(sp))
                except Exception:
                    pass

        # Textura de fondo opcional
        self.bg_surf = None
        bg_path = ROOT / "assets_ps4" / "background.png"
        if bg_path.exists():
            try:
                loaded = pygame.image.load(str(bg_path)).convert()
                self.bg_surf = pygame.transform.smoothscale(loaded, (self.w, self.h))
            except Exception:
                pass

        # Datos del jugador en el Shell
        self.player_name = "Alex"
        self.player_level = 12
        self.gamerscore = 12450
        self.ticker_text = "C.C.I. SYSTEM — VIRTUAL CONSOLE v2.1.0"
        self.is_online = True

        # Botones superiores de acceso rápido
        self.top_buttons = [
            {"id": "user", "label": "Alex", "icon": "👤", "action": "PROFILE"},
            {"id": "gamerscore", "label": "12,450 G", "icon": "🏆", "action": "ACHIEVEMENTS"},
            {"id": "theme", "label": "Tema", "icon": "🎨", "action": "CYCLE_THEME"},
            {"id": "settings", "label": "Ajustes", "icon": "⚙️", "action": "SETTINGS"},
            {"id": "off", "label": "Apagar", "icon": "⏻", "action": "QUIT"},
        ]
        self.top_rects: list[pygame.Rect] = []
        self.hovered_top_idx = -1

    def _init_particles(self):
        self.particles = []
        for i in range(25):
            self.particles.append({
                "x": (i * 57) % self.w,
                "y": (i * 31) % self.h,
                "vx": (i % 3 + 1) * 0.4,
                "vy": -((i % 2) * 0.5 + 0.3),
                "radius": (i % 4) + 2,
                "alpha": 30 + (i * 7) % 70,
            })

    def set_theme(self, theme_id: str):
        if theme_id in THEMES:
            self.active_theme_id = theme_id
            self.theme = THEMES[theme_id]
            self.play_sound("reward")

    def cycle_theme(self):
        theme_keys = list(THEMES.keys())
        cur = theme_keys.index(self.active_theme_id)
        next_key = theme_keys[(cur + 1) % len(theme_keys)]
        self.set_theme(next_key)

    def play_sound(self, name: str):
        s = self.sfx.get(name)
        if s:
            try:
                s.play()
            except Exception:
                pass

    def handle_shell_event(self, event: pygame.event.Event) -> dict | None:
        """Maneja eventos de la barra superior y accesos globales de OmniDash."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            prev_hover = self.hovered_top_idx
            self.hovered_top_idx = -1
            for idx, r in enumerate(self.top_rects):
                if r.collidepoint(mx, my):
                    self.hovered_top_idx = idx
                    if prev_hover != idx:
                        self.play_sound("navigate")
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for idx, r in enumerate(self.top_rects):
                if r.collidepoint(mx, my):
                    item = self.top_buttons[idx]
                    if item["action"] == "CYCLE_THEME":
                        self.cycle_theme()
                        return None
                    elif item["action"] == "QUIT":
                        self.play_sound("shutdown")
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                        return {"action": "QUIT"}
                    else:
                        self.play_sound("reward")
                        return {"action": "NAVIGATE", "destination": item["action"]}

        return None

    def render_background(self, surface: pygame.Surface):
        self.anim_timer += 0.02
        t = self.theme

        # 1. Base Wallpaper
        if self.active_theme_id == "ps4" and self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill(t["bg_base"])

        # 2. Efectos Procedurales por Tema
        if self.active_theme_id in ("ps4", "aero"):
            # Ondas dinámicas fluidas
            for i in range(3):
                wave_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
                pts = []
                for x in range(0, self.w + 25, 25):
                    wave_y = int(self.h * 0.68 + math.sin(x * 0.003 + self.anim_timer + i * 1.2) * 55)
                    pts.append((x, wave_y))
                pts.append((self.w, self.h))
                pts.append((0, self.h))
                wave_color = (255, 255, 255, 10 + i * 6) if self.active_theme_id == "ps4" else (255, 255, 255, 20 + i * 10)
                pygame.draw.polygon(wave_surf, wave_color, pts)
                surface.blit(wave_surf, (0, 0))

        # Partículas flotantes estilo cristal / bokeh
        for p in self.particles:
            p["x"] = (p["x"] + p["vx"]) % self.w
            p["y"] = (p["y"] + p["vy"]) % self.h
            p_surf = pygame.Surface((p["radius"] * 2, p["radius"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (255, 255, 255, p["alpha"]), (p["radius"], p["radius"]), p["radius"])
            surface.blit(p_surf, (int(p["x"]), int(p["y"])))

    def render_top_bar(self, surface: pygame.Surface):
        top_y = 30
        t = self.theme

        # Banner izquierdo con Ticker de estado y logo
        ticker_t = self.font_sub.render(self.ticker_text, True, t["text_secondary"])
        surface.blit(ticker_t, (40, top_y + 8))

        # Indicador online
        pygame.draw.circle(surface, (34, 197, 94), (28, top_y + 15), 5)

        # Botones de navegación a la derecha
        self.top_rects = []
        base_x = 520
        spacing = 130

        for idx, btn in enumerate(self.top_buttons):
            bx = base_x + idx * spacing
            btn_rect = pygame.Rect(bx, top_y, 118, 34)
            self.top_rects.append(btn_rect)

            is_hov = (idx == self.hovered_top_idx)

            # Fondo del botón
            pill_color = (255, 255, 255, 60) if is_hov else (255, 255, 255, 18)
            pygame.draw.rect(surface, pill_color, btn_rect, border_radius=17)
            if is_hov:
                pygame.draw.rect(surface, t["focus_glow"], btn_rect, width=2, border_radius=17)

            # Icono + Etiqueta
            ico_t = self.font_sub.render(btn["icon"], True, t["text_primary"])
            surface.blit(ico_t, (btn_rect.x + 12, btn_rect.y + 7))

            lbl_t = self.font_btn.render(btn["label"], True, t["text_primary"])
            surface.blit(lbl_t, (btn_rect.x + 36, btn_rect.y + 8))

        # Reloj digital en vivo
        now_str = datetime.datetime.now().strftime("%H:%M")
        clock_t = self.font_clock.render(now_str, True, t["text_primary"])
        surface.blit(clock_t, (self.w - 85, top_y + 7))

    def render_bottom_dock(self, surface: pygame.Surface, extra_actions: list[tuple[str, str]] = None):
        dock_y = self.h - 46
        t = self.theme
        pygame.draw.line(surface, (255, 255, 255, 25), (0, dock_y), (self.w, dock_y), 1)

        actions = [
            ("⌧", "Seleccionar / Iniciar"),
            ("◯", "Atrás / Volver"),
            ("△", "Cambiar Tema"),
            ("⇦ ⇨", "Desplazar Mosaicos"),
        ]
        if extra_actions:
            actions.extend(extra_actions)

        cx = 40
        for glyph, desc in actions:
            gt = self.font_badge.render(glyph, True, t["accent"] if glyph in ("⌧", "△") else t["text_primary"])
            dt = self.font_sub.render(desc, True, t["text_secondary"])

            surface.blit(gt, (cx, dock_y + 14))
            surface.blit(dt, (cx + gt.get_width() + 8, dock_y + 12))
            cx += gt.get_width() + dt.get_width() + 32
