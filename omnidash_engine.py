"""omnidash_engine.py - Motor Base Auténtico estilo OmniDash para C.C.I. SYSTEM.
100% Python puro con Pygame-CE.
Implementa el diseño visual oficial de OmniDash Frutiger Aero (aero-home.jpg, garrison-theme-aero.css):
- Fondo panorámico Frutiger Aero (aero-background.webp: isla tropical soleada con mar turquesa y cielo azul).
- Barra superior oficial:
  * Izquierda: Perfil de jugador con avatar circular en gradiente celeste/azul, nombre 'Alex' y '18,450 G'.
  * Centro: 4 botones circulares de vidrio translúcido (Inicio con aura azul activa, Biblioteca, Comunidad, Ajustes).
  * Derecha: Reloj digital elegante con sombra Frutiger Aero.
- Barra inferior oficial de Store y navegación rápida.
- Cero archivos JS/CSS en el repositorio: 100% Python.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import datetime
import math
import os
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

# ==============================================================================
# UTILIDADES DE CRISTAL TRANSLÚCIDO SEGURO (PREVIENE BOTONES BLANCOS CIEGOS)
# ==============================================================================
def draw_glass_rect(surface: pygame.Surface, rect: pygame.Rect, bg_rgba: tuple, border_rgba: tuple | None = None, border_radius: int = 0, border_width: int = 1):
    w, h = rect.width, rect.height
    if w <= 0 or h <= 0:
        return
    g_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(g_surf, bg_rgba, (0, 0, w, h), border_radius=border_radius)
    if border_rgba:
        pygame.draw.rect(g_surf, border_rgba, (0, 0, w, h), width=border_width, border_radius=border_radius)
    surface.blit(g_surf, rect.topleft)


def draw_glass_circle(surface: pygame.Surface, center: tuple[int, int], radius: int, bg_rgba: tuple, border_rgba: tuple | None = None, border_width: int = 1):
    if radius <= 0:
        return
    size = radius * 2 + 6
    c_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    lc = (radius + 3, radius + 3)
    pygame.draw.circle(c_surf, bg_rgba, lc, radius)
    if border_rgba:
        pygame.draw.circle(c_surf, border_rgba, lc, radius, width=border_width)
    surface.blit(c_surf, (center[0] - radius - 3, center[1] - radius - 3))

THEMES = {
    "aero": {
        "id": "aero",
        "name": "Frutiger Aero (OmniDash Signature)",
        "bg_image": "assets_omnidash/aero-background.webp",
        "bg_base": (0, 119, 182),
        "accent": (0, 180, 216),
        "focus_glow": (182, 245, 90),  # Verde neón oficial OmniDash #b6f55a
        "panel_glass": (255, 255, 255, 110),
        "card_glass": (255, 255, 255, 140),
        "card_hover": (255, 255, 255, 220),
        "border_glass": (255, 255, 255, 190),
        "text_primary": (255, 255, 255),
        "text_secondary": (210, 235, 255),
        "text_dark": (12, 28, 48),
    }
}


class OmniDashEngine:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720, active_theme: str = "aero"):
        self.w = screen_w
        self.h = screen_h
        self.active_theme_id = "aero"
        self.theme = THEMES["aero"]

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
            self.font_clock = pygame.font.Font(font_file, 17)
            self.font_btn = pygame.font.Font(font_file, 13)
        except Exception:
            self.font_hero = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 26, bold=True)
            self.font_title = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 20, bold=True)
            self.font_body = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 15, bold=True)
            self.font_sub = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 13)
            self.font_badge = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 11, bold=True)
            self.font_clock = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 17, bold=True)
            self.font_btn = pygame.font.SysFont("Segoe UI, Helvetica, Arial", 13, bold=True)

        # Sonidos oficiales
        self.sfx = {}
        for sname in ("navigate.mp3", "reward.mp3", "startup.mp3", "shutdown.mp3"):
            sp = ROOT / "assets_ps4" / "audio" / sname
            if sp.exists() and pygame.mixer.get_init():
                try:
                    self.sfx[sname.split(".")[0]] = pygame.mixer.Sound(str(sp))
                except Exception:
                    pass

        # Cargar fondo oficial Frutiger Aero
        self.bg_surf = None
        aero_bg = ROOT / "assets_omnidash" / "aero-background.webp"
        if aero_bg.exists():
            try:
                loaded = pygame.image.load(str(aero_bg)).convert()
                self.bg_surf = pygame.transform.smoothscale(loaded, (self.w, self.h))
            except Exception:
                pass

        # Datos del jugador oficial OmniDash
        self.player_name = "Alex"
        self.gamerscore = 18450

        # Botones circulares oficiales del centro de la barra superior:
        # [ 🏠 Inicio ] [ 📚 Biblioteca ] [ 👥 Comunidad ] [ ⚙️ Ajustes ]
        self.nav_dock_items = [
            {"id": "home", "label": "Inicio", "icon": "🏠", "action": "HOME"},
            {"id": "library", "label": "Biblioteca", "icon": "📚", "action": "LIBRARY"},
            {"id": "community", "label": "Comunidad", "icon": "👥", "action": "COMMUNITY"},
            {"id": "settings", "label": "Ajustes", "icon": "⚙️", "action": "SETTINGS"},
        ]
        self.nav_dock_rects: list[pygame.Rect] = []
        self.hovered_nav_idx = -1
        self.active_nav_idx = 0

        # Botones inferiores oficiales de la fila Store
        self.store_chips = [
            {"id": "store", "label": "Explorar Tienda", "action": "LIBRARY"},
            {"id": "deals", "label": "Ofertas & Descuentos", "action": "LIBRARY"},
            {"id": "subs", "label": "Suscripciones", "action": "PROFILE"},
            {"id": "search", "label": "Buscar Juegos", "action": "LIBRARY"},
        ]
        self.store_chip_rects: list[pygame.Rect] = []

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
            prev_nav = self.hovered_nav_idx
            self.hovered_nav_idx = -1
            for idx, r in enumerate(self.nav_dock_rects):
                if r.collidepoint(mx, my):
                    self.hovered_nav_idx = idx
                    if prev_nav != idx:
                        self.play_sound("navigate")
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Clic en perfil de usuario (abre PROFILE)
            profile_rect = pygame.Rect(40, 20, 200, 56)
            if profile_rect.collidepoint(mx, my):
                self.play_sound("reward")
                return {"action": "NAVIGATE", "destination": "PROFILE"}

            # Clic en botones circulares de navegación superior
            for idx, r in enumerate(self.nav_dock_rects):
                if r.collidepoint(mx, my):
                    self.active_nav_idx = idx
                    item = self.nav_dock_items[idx]
                    self.play_sound("reward")
                    return {"action": "NAVIGATE", "destination": item["action"]}

            # Clic en chips de Store inferiores
            for idx, r in enumerate(self.store_chip_rects):
                if r.collidepoint(mx, my):
                    item = self.store_chips[idx]
                    self.play_sound("reward")
                    return {"action": "NAVIGATE", "destination": item["action"]}

        return None

    def render_background(self, surface: pygame.Surface):
        if self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill((0, 119, 182))

    def render_top_bar(self, surface: pygame.Surface, active_tab: str = "HOME"):
        # Gradiente superior de sombra
        top_grad = pygame.Surface((self.w, 90), pygame.SRCALPHA)
        for y in range(90):
            alpha = int(95 * (1.0 - y / 90.0))
            pygame.draw.line(top_grad, (0, 40, 90, alpha), (0, y), (self.w, y))
        surface.blit(top_grad, (0, 0))

        # 1. Perfil del Jugador oficial OmniDash (Izquierda)
        av_center = (64, 46)
        # Sombra avatar
        pygame.draw.circle(surface, (0, 25, 60, 120), (av_center[0], av_center[1] + 2), 23)
        # Fondo avatar radial celeste
        pygame.draw.circle(surface, (90, 166, 214), av_center, 22)
        # Borde blanco brillante
        pygame.draw.circle(surface, (255, 255, 255), av_center, 22, width=2)
        av_txt = self.font_body.render("A", True, (255, 255, 255))
        surface.blit(av_txt, av_txt.get_rect(center=av_center))

        # Nombre y Gamerscore
        name_t = self.font_title.render(self.player_name, True, (255, 255, 255))
        surface.blit(name_t, (96, 30))

        # Badge redondo blanco "G" con Gamerscore
        g_center = (104, 58)
        pygame.draw.circle(surface, (255, 255, 255), g_center, 8)
        g_txt = self.font_badge.render("G", True, (20, 20, 20))
        surface.blit(g_txt, g_txt.get_rect(center=g_center))

        score_t = self.font_sub.render(f"{self.gamerscore:,} G", True, (255, 255, 255))
        surface.blit(score_t, (118, 51))

        # 2. Dock Circular Central Oficial OmniDash Aero
        # 4 botones circulares: [ 🏠 ] [ 📚 ] [ 👥 ] [ ⚙️ ]
        self.nav_dock_rects = []
        cx_start = self.w // 2 - 100
        btn_radius = 21
        spacing = 52

        for idx, item in enumerate(self.nav_dock_items):
            bx = cx_start + idx * spacing
            by = 46
            rect = pygame.Rect(bx - btn_radius, by - btn_radius, btn_radius * 2, btn_radius * 2)
            self.nav_dock_rects.append(rect)

            is_active = (item["action"] == active_tab)
            is_hover = (idx == self.hovered_nav_idx)

            # Fondo circular de vidrio con contraste perfecto (cero bloque blanco sólido)
            if is_active:
                draw_glass_circle(surface, (bx, by), btn_radius, (31, 134, 214, 235), (255, 255, 255, 240), border_width=2)
            elif is_hover:
                draw_glass_circle(surface, (bx, by), btn_radius, (12, 60, 105, 220), (182, 245, 90), border_width=2)
            else:
                draw_glass_circle(surface, (bx, by), btn_radius, (10, 48, 80, 180), (255, 255, 255, 120), border_width=1)

            ico_t = self.font_body.render(item["icon"], True, (255, 255, 255))
            surface.blit(ico_t, ico_t.get_rect(center=(bx, by)))

        # 3. Reloj Digital oficial OmniDash (Derecha)
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        # Sombra de texto
        clock_shad = self.font_clock.render(now_str, True, (0, 35, 75))
        surface.blit(clock_shad, (self.w - 148, 37))
        clock_t = self.font_clock.render(now_str, True, (255, 255, 255))
        surface.blit(clock_t, (self.w - 150, 36))

    def render_bottom_dock(self, surface: pygame.Surface):
        # Fila Store oficial de OmniDash Frutiger Aero
        by = self.h - 52

        # Etiqueta 'Store'
        store_lbl = self.font_body.render("Store", True, (255, 255, 255))
        surface.blit(store_lbl, (110, by + 6))

        # Chips de vidrio translúcido con alto contraste
        self.store_chip_rects = []
        cx = 175
        for chip in self.store_chips:
            tw = max(110, len(chip["label"]) * 8 + 26)
            r = pygame.Rect(cx, by, tw, 30)
            self.store_chip_rects.append(r)

            is_hov = r.collidepoint(pygame.mouse.get_pos())
            bg_col = (14, 65, 110, 220) if is_hov else (10, 48, 80, 175)
            border_col = (182, 245, 90) if is_hov else (255, 255, 255, 120)
            draw_glass_rect(surface, r, bg_col, border_col, border_radius=15, border_width=1)

            lt = self.font_sub.render(chip["label"], True, (255, 255, 255))
            surface.blit(lt, lt.get_rect(center=r.center))
            cx += tw + 12

        # Leyenda de control derecha
        cust_t = self.font_sub.render("Ⓨ  Personalizar", True, (255, 255, 255))
        surface.blit(cust_t, (self.w - 160, by + 6))
