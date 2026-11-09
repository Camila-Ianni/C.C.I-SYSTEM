"""omnidash_engine.py - Motor Base Auténtico estilo OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE.
Implementa el diseño oficial de OmniDash (Frutiger Aero, Helix Dark Glass, Xbox Series, Wii):
- Fondo panorámico Frutiger Aero (isla tropical soleada con mar turquesa y cielo azul).
- Barra superior: Perfil de jugador a la izquierda (Avatar + Gamerscore 18,450 G),
  dock flotante central con píldoras de navegación (Inicio, Biblioteca, Buscar, Ajustes), reloj a la derecha.
- Dock inferior con botones de navegación rápida y leyendas de mando.
- Cero archivos JS/CSS: GitHub 100% Python.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import datetime
import math
import os
import sys
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

THEMES = {
    "aero": {
        "id": "aero",
        "name": "Frutiger Aero (OmniDash Signature)",
        "bg_image": "assets_omnidash/aero-background.webp",
        "bg_base": (0, 119, 182),
        "accent": (0, 180, 216),
        "panel_glass": (255, 255, 255, 110),
        "card_glass": (255, 255, 255, 150),
        "card_hover": (255, 255, 255, 215),
        "border_glass": (255, 255, 255, 180),
        "text_primary": (12, 28, 48),
        "text_secondary": (25, 60, 95),
        "text_bright": (255, 255, 255),
        "focus_glow": (255, 255, 255),
    },
    "helix": {
        "id": "helix",
        "name": "Helix (Black Glass PC)",
        "bg_image": None,
        "bg_base": (10, 12, 16),
        "accent": (147, 51, 234),
        "panel_glass": (20, 24, 34, 220),
        "card_glass": (26, 32, 44, 220),
        "card_hover": (44, 54, 74, 240),
        "border_glass": (168, 85, 247, 180),
        "text_primary": (255, 255, 255),
        "text_secondary": (170, 185, 210),
        "text_bright": (255, 255, 255),
        "focus_glow": (168, 85, 247),
    },
    "xbox": {
        "id": "xbox",
        "name": "Xbox Series",
        "bg_image": None,
        "bg_base": (15, 20, 24),
        "accent": (16, 160, 68),
        "panel_glass": (24, 32, 38, 220),
        "card_glass": (30, 40, 48, 220),
        "card_hover": (46, 60, 72, 240),
        "border_glass": (16, 200, 80, 180),
        "text_primary": (255, 255, 255),
        "text_secondary": (180, 200, 190),
        "text_bright": (255, 255, 255),
        "focus_glow": (16, 200, 80),
    },
}


class OmniDashEngine:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720, active_theme: str = "aero"):
        self.w = screen_w
        self.h = screen_h
        self.active_theme_id = active_theme if active_theme in THEMES else "aero"
        self.theme = THEMES[self.active_theme_id]

        self.anim_timer = 0.0

        # Fuentes oficiales SST o sistema
        font_path = ROOT / "assets_ps4" / "font" / "sst.ttf"
        font_file = str(font_path) if font_path.exists() else None

        pygame.font.init()
        try:
            self.font_hero = pygame.font.Font(font_file, 26)
            self.font_title = pygame.font.Font(font_file, 20)
            self.font_body = pygame.font.Font(font_file, 15)
            self.font_sub = pygame.font.Font(font_file, 13)
            self.font_badge = pygame.font.Font(font_file, 11)
            self.font_clock = pygame.font.Font(font_file, 16)
            self.font_btn = pygame.font.Font(font_file, 13)
        except Exception:
            self.font_hero = pygame.font.SysFont("Helvetica, Arial", 26, bold=True)
            self.font_title = pygame.font.SysFont("Helvetica, Arial", 20, bold=True)
            self.font_body = pygame.font.SysFont("Helvetica, Arial", 15, bold=True)
            self.font_sub = pygame.font.SysFont("Helvetica, Arial", 13)
            self.font_badge = pygame.font.SysFont("Courier, monospace", 11, bold=True)
            self.font_clock = pygame.font.SysFont("Helvetica, Arial", 16, bold=True)
            self.font_btn = pygame.font.SysFont("Helvetica, Arial", 13, bold=True)

        # Sonidos
        self.sfx = {}
        for sname in ("navigate.mp3", "reward.mp3", "startup.mp3", "shutdown.mp3"):
            sp = ROOT / "assets_ps4" / "audio" / sname
            if sp.exists() and pygame.mixer.get_init():
                try:
                    self.sfx[sname.split(".")[0]] = pygame.mixer.Sound(str(sp))
                except Exception:
                    pass

        # Cargar fondo Frutiger Aero
        self.bg_surf = None
        aero_bg = ROOT / "assets_omnidash" / "aero-background.webp"
        if aero_bg.exists():
            try:
                loaded = pygame.image.load(str(aero_bg)).convert()
                self.bg_surf = pygame.transform.smoothscale(loaded, (self.w, self.h))
            except Exception:
                pass

        # Datos del jugador
        self.player_name = "Alex"
        self.gamerscore = 18450

        # Botones del Dock central superior de OmniDash: [ 🏠 Inicio ] [ 📚 Biblioteca ] [ 🔍 Buscar ] [ ⚙️ Ajustes ]
        self.nav_dock_items = [
            {"id": "home", "label": "Inicio", "icon": "🏠", "action": "HOME"},
            {"id": "library", "label": "Biblioteca", "icon": "📚", "action": "LIBRARY"},
            {"id": "community", "label": "Comunidad", "icon": "👥", "action": "GROUPS"},
            {"id": "settings", "label": "Ajustes", "icon": "⚙️", "action": "SETTINGS"},
        ]
        self.nav_dock_rects: list[pygame.Rect] = []
        self.hovered_nav_idx = -1

        # Botones del pie de página OmniDash
        self.bottom_pills = [
            {"id": "consoles", "label": "Consolas", "icon": "🎮", "action": "HOME"},
            {"id": "community", "label": "Comunidad C.C.I.", "icon": "👥", "action": "GROUPS"},
            {"id": "trophies", "label": "Logros", "icon": "🏆", "action": "PROFILE"},
            {"id": "settings", "label": "Ajustes", "icon": "⚙️", "action": "SETTINGS"},
            {"id": "theme", "label": "Tema", "icon": "🎨", "action": "CYCLE_THEME"},
            {"id": "off", "label": "Apagar", "icon": "⏻", "action": "QUIT"},
        ]
        self.bottom_pill_rects: list[pygame.Rect] = []
        self.hovered_bottom_idx = -1

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
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos

            # Hover en dock superior
            prev_nav = self.hovered_nav_idx
            self.hovered_nav_idx = -1
            for idx, r in enumerate(self.nav_dock_rects):
                if r.collidepoint(mx, my):
                    self.hovered_nav_idx = idx
                    if prev_nav != idx:
                        self.play_sound("navigate")
                    break

            # Hover en píldoras inferiores
            prev_bot = self.hovered_bottom_idx
            self.hovered_bottom_idx = -1
            for idx, r in enumerate(self.bottom_pill_rects):
                if r.collidepoint(mx, my):
                    self.hovered_bottom_idx = idx
                    if prev_bot != idx:
                        self.play_sound("navigate")
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Clic en dock superior
            for idx, r in enumerate(self.nav_dock_rects):
                if r.collidepoint(mx, my):
                    item = self.nav_dock_items[idx]
                    self.play_sound("reward")
                    return {"action": "NAVIGATE", "destination": item["action"]}

            # Clic en píldoras inferiores
            for idx, r in enumerate(self.bottom_pill_rects):
                if r.collidepoint(mx, my):
                    item = self.bottom_pills[idx]
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

        if self.active_theme_id == "aero" and self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill(t["bg_base"])

    def render_top_bar(self, surface: pygame.Surface):
        top_y = 20
        t = self.theme

        # 1. Perfil del Jugador Izquierda (Avatar circular + Nombre + Gamerscore)
        p_surf = pygame.Surface((190, 48), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, t["panel_glass"], (0, 0, 190, 48), border_radius=24)
        pygame.draw.rect(p_surf, t["border_glass"], (0, 0, 190, 48), width=1, border_radius=24)
        surface.blit(p_surf, (36, top_y))

        # Avatar
        pygame.draw.circle(surface, (20, 40, 70), (60, top_y + 24), 16)
        pygame.draw.circle(surface, t["accent"], (60, top_y + 24), 16, width=2)
        av_txt = self.font_badge.render("A", True, (255, 255, 255))
        surface.blit(av_txt, av_txt.get_rect(center=(60, top_y + 24)))

        # Nombre y Gamerscore
        name_t = self.font_body.render(self.player_name, True, t["text_primary"])
        surface.blit(name_t, (84, top_y + 8))

        gs_t = self.font_badge.render(f"🎮 {self.gamerscore:,} G", True, t["text_secondary"])
        surface.blit(gs_t, (84, top_y + 28))

        # 2. Dock Flotante Central de OmniDash [ 🏠 Inicio ] [ 📚 Biblioteca ] [ 👥 Comunidad ] [ ⚙️ Ajustes ]
        dock_w = 460
        dock_h = 44
        dock_x = (self.w - dock_w) // 2
        d_surf = pygame.Surface((dock_w, dock_h), pygame.SRCALPHA)
        pygame.draw.rect(d_surf, t["panel_glass"], (0, 0, dock_w, dock_h), border_radius=22)
        pygame.draw.rect(d_surf, t["border_glass"], (0, 0, dock_w, dock_h), width=1, border_radius=22)
        surface.blit(d_surf, (dock_x, top_y + 2))

        self.nav_dock_rects = []
        item_w = 105
        for idx, it in enumerate(self.nav_dock_items):
            ix = dock_x + 10 + idx * (item_w + 6)
            rect = pygame.Rect(ix, top_y + 6, item_w, 36)
            self.nav_dock_rects.append(rect)

            is_hov = (idx == self.hovered_nav_idx)
            if is_hov:
                pygame.draw.rect(surface, (255, 255, 255, 80), rect, border_radius=18)
                pygame.draw.rect(surface, (255, 255, 255), rect, width=1, border_radius=18)

            txt = self.font_sub.render(f"{it['icon']} {it['label']}", True, t["text_primary"])
            surface.blit(txt, txt.get_rect(center=rect.center))

        # 3. Reloj Digital Derecha
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        clock_pill = pygame.Surface((120, 44), pygame.SRCALPHA)
        pygame.draw.rect(clock_pill, t["panel_glass"], (0, 0, 120, 44), border_radius=22)
        pygame.draw.rect(clock_pill, t["border_glass"], (0, 0, 120, 44), width=1, border_radius=22)
        surface.blit(clock_pill, (self.w - 156, top_y + 2))

        ct = self.font_clock.render(now_str, True, t["text_primary"])
        surface.blit(ct, ct.get_rect(center=(self.w - 96, top_y + 24)))

    def render_bottom_dock(self, surface: pygame.Surface, extra_actions: list[tuple[str, str]] = None):
        dock_y = self.h - 58
        t = self.theme

        # Píldoras de acción rápida a la izquierda
        self.bottom_pill_rects = []
        cur_x = 36
        for idx, pill in enumerate(self.bottom_pills):
            p_w = 120 if pill["id"] == "community" else 105
            p_rect = pygame.Rect(cur_x, dock_y, p_w, 36)
            self.bottom_pill_rects.append(p_rect)

            is_hov = (idx == self.hovered_bottom_idx)
            p_surf = pygame.Surface((p_w, 36), pygame.SRCALPHA)
            bg_col = (255, 255, 255, 80) if is_hov else (255, 255, 255, 35)
            pygame.draw.rect(p_surf, bg_col, (0, 0, p_w, 36), border_radius=18)
            pygame.draw.rect(p_surf, (255, 255, 255, 140), (0, 0, p_w, 36), width=1, border_radius=18)
            surface.blit(p_surf, (cur_x, dock_y))

            pt = self.font_sub.render(f"{pill['icon']} {pill['label']}", True, t["text_primary"])
            surface.blit(pt, pt.get_rect(center=p_rect.center))
            cur_x += p_w + 10

        # Guía de mando a la derecha
        guide_t = self.font_badge.render("🎮 [Y] Tema   [A] Seleccionar   [B] Atrás", True, t["text_primary"])
        g_rect = guide_t.get_rect(right=self.w - 36, centery=dock_y + 18)
        surface.blit(guide_t, g_rect)
