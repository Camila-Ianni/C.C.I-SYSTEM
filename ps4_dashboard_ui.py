"""ps4_dashboard_ui.py - Interfaz de Usuario estilo PlayStation 4 (100% Python puro con Pygame).
Reimplementa la experiencia completa de la PS4:
- Barra de funciones superior (Perfil, Amigos/Grupos, Trofeos, Ajustes, Apagar, Reloj en vivo).
- Cinta horizontal de mosaicos con foco dinámico, sonido 'navigate.mp3', botón 'INICIAR' y animaciones.
- Fondo dinámico de ondas PlayStation / C.C.I. SYSTEM.
- 100% Python puro sin archivos JS ni CSS: GitHub se mantiene 100% Python.
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

# Colores Oficiales PS4 / Dark Glass
COLOR_PS_BLUE = (14, 108, 196)
COLOR_PS_DARK = (10, 14, 22)
COLOR_WHITE = (255, 255, 255)
COLOR_MUTED = (180, 200, 225)
COLOR_DIM = (110, 130, 160)
COLOR_FOCUS_GLOW = (255, 255, 255)
COLOR_TOPBAR_BG = (10, 30, 60, 140)

RIBBON_ITEMS = [
    {
        "id": "snes",
        "title": "Super Nintendo",
        "subtitle": "16-BIT // 21 TÍTULOS DISPONIBLES",
        "type": "CONSOLE",
        "badge": "SNES",
        "icon_symbol": "SUPER NINTENDO",
        "color": (210, 60, 60),
    },
    {
        "id": "n64",
        "title": "Nintendo 64",
        "subtitle": "64-BIT 3D // 5 TÍTULOS PRESERVADOS",
        "type": "CONSOLE",
        "badge": "N64",
        "icon_symbol": "NINTENDO 64",
        "color": (66, 133, 244),
    },
    {
        "id": "ps1",
        "title": "PlayStation",
        "subtitle": "32-BIT CD-ROM // CRASH & RESIDENT EVIL",
        "type": "CONSOLE",
        "badge": "PS1",
        "icon_symbol": "PLAYSTATION",
        "color": (0, 114, 206),
    },
    {
        "id": "mame",
        "title": "Arcade Classics",
        "subtitle": "COIN-OP // CAPCOM CPS & MIDWAY",
        "type": "CONSOLE",
        "badge": "ARCADE",
        "icon_symbol": "ARCADE",
        "color": (245, 166, 35),
    },
    {
        "id": "neogeo",
        "title": "SNK Neo-Geo",
        "subtitle": "24-BIT // 330 MEGA PRO-GEAR",
        "type": "CONSOLE",
        "badge": "NEO-GEO",
        "icon_symbol": "NEO-GEO MVS",
        "color": (230, 190, 40),
    },
    {
        "id": "nds",
        "title": "Nintendo DS",
        "subtitle": "DUAL SCREEN // POKÉMON & MARIO",
        "type": "CONSOLE",
        "badge": "NDS",
        "icon_symbol": "NINTENDO DS",
        "color": (160, 170, 185),
    },
    {
        "id": "wii",
        "title": "Nintendo Wii",
        "subtitle": "MOTION CONTROL // WII SPORTS",
        "type": "CONSOLE",
        "badge": "WII",
        "icon_symbol": "NINTENDO WII",
        "color": (180, 200, 220),
    },
    {
        "id": "community",
        "title": "Comunidad C.C.I.",
        "subtitle": "CHATS PRIVADOS, GRUPOS Y SOLICITUDES",
        "type": "COMMUNITY",
        "badge": "HUB",
        "icon_symbol": "COMUNIDAD",
        "color": (34, 197, 94),
    },
]


class PS4DashboardUI:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720):
        self.w = screen_w
        self.h = screen_h
        self.active_layer = "RIBBON"  # "TOPBAR", "RIBBON" o "SUBPANEL"
        self.selected_tile_idx = 0
        self.selected_top_idx = 1  # 0: Plus, 1: User, 2: Friends, 3: Trophies, 4: Settings, 5: Off
        self.scroll_x = 0.0
        self.anim_timer = 0.0

        # Fuentes oficiales SST si existen, fallback a sistema
        font_path = ROOT / "assets_ps4" / "font" / "sst.ttf"
        font_file = str(font_path) if font_path.exists() else None

        pygame.font.init()
        try:
            self.font_title = pygame.font.Font(font_file, 28)
            self.font_subtitle = pygame.font.Font(font_file, 15)
            self.font_badge = pygame.font.Font(font_file, 13)
            self.font_clock = pygame.font.Font(font_file, 18)
            self.font_top = pygame.font.Font(font_file, 14)
            self.font_tile_title = pygame.font.Font(font_file, 20)
        except Exception:
            self.font_title = pygame.font.SysFont("Helvetica, Arial", 28, bold=True)
            self.font_subtitle = pygame.font.SysFont("Helvetica, Arial", 15)
            self.font_badge = pygame.font.SysFont("Courier, monospace", 13, bold=True)
            self.font_clock = pygame.font.SysFont("Helvetica, Arial", 18, bold=True)
            self.font_top = pygame.font.SysFont("Helvetica, Arial", 14)
            self.font_tile_title = pygame.font.SysFont("Helvetica, Arial", 20, bold=True)

        # Cargar sonidos oficiales PS4
        self.sfx_nav = self._load_sound("navigate.mp3")
        self.sfx_start = self._load_sound("startup.mp3")
        self.sfx_reward = self._load_sound("reward.mp3")
        self.sfx_off = self._load_sound("shutdown.mp3")

        # Cargar textura de fondo oficial PS4 si existe
        bg_path = ROOT / "assets_ps4" / "background.png"
        self.bg_surf = None
        if bg_path.exists():
            try:
                loaded = pygame.image.load(str(bg_path)).convert()
                self.bg_surf = pygame.transform.smoothscale(loaded, (self.w, self.h))
            except Exception:
                pass

        # Cargar iconos
        self.icons = {}
        for name in ("plus", "friends", "trophy", "settings", "off", "user", "start", "ps"):
            ip = ROOT / "assets_ps4" / "icons" / f"{name}.png"
            if ip.exists():
                try:
                    self.icons[name] = pygame.image.load(str(ip)).convert_alpha()
                except Exception:
                    pass

        # Top Bar items
        self.top_items = [
            {"id": "plus", "label": "C.C.I. PLUS", "icon": "plus"},
            {"id": "user", "label": "Alex (Nvl 12)", "icon": "user"},
            {"id": "friends", "label": "Amigos (3)", "icon": "friends"},
            {"id": "trophy", "label": "Trofeos", "icon": "trophy"},
            {"id": "settings", "label": "Ajustes", "icon": "settings"},
            {"id": "off", "label": "Apagar", "icon": "off"},
        ]

    def _load_sound(self, name: str) -> pygame.mixer.Sound | None:
        p = ROOT / "assets_ps4" / "audio" / name
        if p.exists() and pygame.mixer.get_init():
            try:
                return pygame.mixer.Sound(str(p))
            except Exception:
                pass
        return None

    def _play_sfx(self, sfx: pygame.mixer.Sound | None):
        if sfx:
            try:
                sfx.play()
            except Exception:
                pass

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """Maneja eventos de teclado, ratón y gamepad con comportamiento idéntico a PS4."""
        if event.type == pygame.KEYDOWN:
            if self.active_layer == "RIBBON":
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.selected_tile_idx < len(RIBBON_ITEMS) - 1:
                        self.selected_tile_idx += 1
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if self.selected_tile_idx > 0:
                        self.selected_tile_idx -= 1
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.active_layer = "TOPBAR"
                    self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_x):
                    item = RIBBON_ITEMS[self.selected_tile_idx]
                    self._play_sfx(self.sfx_reward)
                    return {"action": "SELECT_ITEM", "item": item}

            elif self.active_layer == "TOPBAR":
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.selected_top_idx < len(self.top_items) - 1:
                        self.selected_top_idx += 1
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if self.selected_top_idx > 0:
                        self.selected_top_idx -= 1
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.active_layer = "RIBBON"
                    self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_x):
                    top_sel = self.top_items[self.selected_top_idx]
                    if top_sel["id"] == "off":
                        self._play_sfx(self.sfx_off)
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    else:
                        self._play_sfx(self.sfx_reward)
                        return {"action": "TOPBAR_ACTION", "item": top_sel}

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  # Botón Cruz / A
                if self.active_layer == "RIBBON":
                    item = RIBBON_ITEMS[self.selected_tile_idx]
                    self._play_sfx(self.sfx_reward)
                    return {"action": "SELECT_ITEM", "item": item}
            elif event.button == 1:  # Botón Círculo / B
                if self.active_layer == "TOPBAR":
                    self.active_layer = "RIBBON"
                    self._play_sfx(self.sfx_nav)

        return None

    def render(self, surface: pygame.Surface):
        self.anim_timer += 0.025

        # 1. Fondo PS4 (textura oficial u ondas proceduras en azul dinámico)
        if self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill(COLOR_PS_BLUE)
            # Ondas procedurales de partículas si no hay textura
            for i in range(3):
                wave_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
                pts = []
                for x in range(0, self.w + 20, 20):
                    y = int(self.h * 0.65 + math.sin(x * 0.003 + self.anim_timer + i) * 60)
                    pts.append((x, y))
                pts.append((self.w, self.h))
                pts.append((0, self.h))
                pygame.draw.polygon(wave_surf, (255, 255, 255, 8 + i * 5), pts)
                surface.blit(wave_surf, (0, 0))

        # 2. Barra Superior de Funciones (Top Bar)
        self._render_topbar(surface)

        # 3. Cinta Central de Mosaicos (Horizontal Ribbon)
        self._render_ribbon(surface)

        # 4. Barra Inferior con Guía de Botones PlayStation
        self._render_bottom_legend(surface)

    def _render_topbar(self, surface: pygame.Surface):
        top_y = 48
        is_top_active = (self.active_layer == "TOPBAR")

        # Notificación ticker a la izquierda
        ticker_txt = self.font_top.render("C.C.I. SYSTEM — VIRTUAL CONSOLE v2.1.0", True, COLOR_MUTED)
        surface.blit(ticker_txt, (60, top_y + 4))

        # Items de la barra superior a la derecha
        base_x = 520
        spacing = 110

        for idx, item in enumerate(self.top_items):
            ix = base_x + idx * spacing
            is_sel = is_top_active and (idx == self.selected_top_idx)

            # Fondo píldora si está seleccionado
            if is_sel:
                pill_w = 95
                pill_rect = pygame.Rect(ix - 8, top_y - 4, pill_w, 34)
                pygame.draw.rect(surface, (255, 255, 255, 45), pill_rect, border_radius=9999)
                pygame.draw.rect(surface, COLOR_WHITE, pill_rect, width=1, border_radius=9999)

            # Icono
            icon_name = item.get("icon")
            icon_img = self.icons.get(icon_name)
            if icon_img:
                scaled_icon = pygame.transform.smoothscale(icon_img, (22, 22))
                surface.blit(scaled_icon, (ix, top_y + 2))
            else:
                pygame.draw.circle(surface, COLOR_WHITE if is_sel else COLOR_MUTED, (ix + 11, top_y + 13), 8)

            # Etiqueta
            lbl_color = COLOR_WHITE if is_sel else COLOR_MUTED
            lbl = self.font_top.render(item["label"].split(" ")[0], True, lbl_color)
            surface.blit(lbl, (ix + 28, top_y + 4))

        # Reloj digital en vivo a la derecha extrema
        now_str = datetime.datetime.now().strftime("%H:%M")
        clock_txt = self.font_clock.render(now_str, True, COLOR_WHITE)
        surface.blit(clock_txt, (self.w - 95, top_y + 2))

    def _render_ribbon(self, surface: pygame.Surface):
        is_ribbon_active = (self.active_layer == "RIBBON")

        # Parámetros geométricos de mosaicos
        normal_size = 230
        focused_size = 270
        spacing = 30

        # Suavizado de desplazamiento de cámara horizontal
        target_scroll = -self.selected_tile_idx * (normal_size + spacing)
        self.scroll_x += (target_scroll - self.scroll_x) * 0.18

        base_x = 100 + int(self.scroll_x)
        center_y = 380

        for idx, item in enumerate(RIBBON_ITEMS):
            is_sel = (idx == self.selected_tile_idx)
            tile_size = focused_size if (is_sel and is_ribbon_active) else normal_size

            # Coordenadas
            tx = base_x + idx * (normal_size + spacing)
            ty = center_y - tile_size // 2

            # Optimización de recorte
            if tx + tile_size < -50 or tx > self.w + 50:
                continue

            tile_surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)

            # Fondo del mosaico con gradiente
            bg_base = item.get("color", (40, 60, 90))
            pygame.draw.rect(tile_surf, (bg_base[0] // 3, bg_base[1] // 3, bg_base[2] // 3, 230), (0, 0, tile_size, tile_size), border_radius=12)

            # Borde activo con brillo blanco PS4
            if is_sel and is_ribbon_active:
                pygame.draw.rect(tile_surf, COLOR_FOCUS_GLOW, (0, 0, tile_size, tile_size), width=3, border_radius=12)
                # Resplandor exterior
                glow_rect = pygame.Rect(tx - 4, ty - 4, tile_size + 8, tile_size + 8)
                pygame.draw.rect(surface, (255, 255, 255, 40), glow_rect, width=2, border_radius=16)
            else:
                pygame.draw.rect(tile_surf, (255, 255, 255, 30), (0, 0, tile_size, tile_size), width=1, border_radius=12)

            # Emblema / Símbolo central de la plataforma
            sym_t = self.font_tile_title.render(item["icon_symbol"], True, COLOR_WHITE)
            sym_r = sym_t.get_rect(center=(tile_size // 2, tile_size // 2 - 10))
            tile_surf.blit(sym_t, sym_r)

            # Badge inferior dentro del mosaico
            badge_t = self.font_badge.render(item["badge"], True, COLOR_MUTED)
            badge_r = badge_t.get_rect(center=(tile_size // 2, tile_size - 28))
            tile_surf.blit(badge_t, badge_r)

            surface.blit(tile_surf, (tx, ty))

            # Si es el mosaico seleccionado, dibujar botón 'INICIAR' debajo y título
            if is_sel:
                # Título principal del juego o consola debajo
                t_y = ty + tile_size + 24
                main_t = self.font_title.render(item["title"], True, COLOR_WHITE)
                surface.blit(main_t, (tx, t_y))

                sub_t = self.font_subtitle.render(item["subtitle"], True, COLOR_MUTED)
                surface.blit(sub_t, (tx, t_y + 36))

                # Botón 'Iniciar' estilo PS4
                if is_ribbon_active:
                    btn_pill = pygame.Surface((120, 36), pygame.SRCALPHA)
                    pygame.draw.rect(btn_pill, COLOR_WHITE, (0, 0, 120, 36), border_radius=6)
                    start_t = self.font_badge.render("INICIAR", True, (0, 0, 0))
                    btn_pill.blit(start_t, start_t.get_rect(center=(60, 18)))
                    surface.blit(btn_pill, (tx, ty + tile_size - 48))

    def _render_bottom_legend(self, surface: pygame.Surface):
        bar_y = self.h - 52
        pygame.draw.line(surface, (255, 255, 255, 25), (0, bar_y), (self.w, bar_y), 1)

        legend_items = [
            ("⌧", "Entrar / Iniciar"),
            ("◯", "Atrás"),
            ("△", "Opciones"),
            ("⇦ ⇨", "Desplazar"),
            ("⇧ ⇩", "Cambiar Fila"),
        ]

        cur_x = 60
        for glyph, text in legend_items:
            gt = self.font_badge.render(glyph, True, COLOR_WHITE)
            tt = self.font_top.render(text, True, COLOR_MUTED)

            surface.blit(gt, (cur_x, bar_y + 16))
            surface.blit(tt, (cur_x + gt.get_width() + 8, bar_y + 14))
            cur_x += gt.get_width() + tt.get_width() + 32


class PS4DashboardState:
    """Estado de StateMachine para integrar el PS4 Dashboard dentro del ciclo de vida de C.C.I. SYSTEM."""

    def __init__(self, state_machine, on_game_launch=None):
        self.state_machine = state_machine
        self.on_game_launch = on_game_launch
        self.ui = PS4DashboardUI(1280, 720)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.ui.handle_event(event)
            if not res:
                continue
            action = res.get("action")
            if action == "SELECT_ITEM":
                item = res["item"]
                if item["type"] == "CONSOLE":
                    self.state_machine.change_state("LIBRARY", default_console=item["id"])
                elif item["type"] == "COMMUNITY":
                    self.state_machine.change_state("GROUPS")
            elif action == "TOPBAR_ACTION":
                item = res["item"]
                item_id = item.get("id")
                if item_id == "user":
                    self.state_machine.change_state("PROFILE")
                elif item_id == "trophy":
                    self.state_machine.change_state("ACHIEVEMENTS")
                elif item_id == "settings":
                    self.state_machine.change_state("SETTINGS")
                elif item_id in ("friends", "plus"):
                    self.state_machine.change_state("GROUPS")

    def update(self, dt):
        pass

    def draw(self, screen):
        self.ui.render(screen)

