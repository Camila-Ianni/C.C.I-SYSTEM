"""ps4_dashboard_ui.py - Interfaz PlayStation 4 auténtica (100% Python puro con Pygame).
Reimplementa la experiencia oficial de PS4:
- Barra de funciones superior interactiva (Perfil, Amigos/Grupos, Trofeos, Ajustes, Apagar, Reloj).
  Soporta clic de ratón, hover y teclado/mando.
- Cinta horizontal de mosaicos con carátulas oficiales, separación perfecta sin solapamientos,
  foco dinámico, botón 'INICIAR' dedicado y efectos de sonido originales.
- Fondo dinámico oficial PS4 y música ambiental.
- Cero archivos JS/CSS/HTML: GitHub permanece 100% Python.
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

# Colores Oficiales PlayStation / Dark Glass
COLOR_PS_BLUE = (14, 108, 196)
COLOR_PS_DARK = (10, 14, 22)
COLOR_WHITE = (255, 255, 255)
COLOR_MUTED = (180, 205, 235)
COLOR_DIM = (110, 135, 170)
COLOR_FOCUS_GLOW = (255, 255, 255)

RIBBON_ITEMS = [
    {
        "id": "snes",
        "title": "Super Nintendo",
        "subtitle": "16-BIT // 21 TÍTULOS DISPONIBLES (Mario World, Zelda, Metroid, DK)",
        "type": "CONSOLE",
        "badge": "SNES",
        "cover": "start.png",
        "color": (210, 60, 60),
    },
    {
        "id": "n64",
        "title": "Nintendo 64",
        "subtitle": "64-BIT 3D // 5 TÍTULOS PRESERVADOS (Super Mario 64, Ocarina, Smash)",
        "type": "CONSOLE",
        "badge": "N64",
        "cover": "elden.png",
        "color": (40, 110, 230),
    },
    {
        "id": "ps1",
        "title": "PlayStation",
        "subtitle": "32-BIT CD-ROM // CRASH BANDICOOT, RESIDENT EVIL",
        "type": "CONSOLE",
        "badge": "PS1",
        "cover": "ps.png",
        "color": (0, 114, 206),
    },
    {
        "id": "mame",
        "title": "Arcade Classics",
        "subtitle": "COIN-OP // CAPCOM CPS, MIDWAY, METAL SLUG, PAC-MAN",
        "type": "CONSOLE",
        "badge": "ARCADE",
        "cover": "battle.png",
        "color": (245, 166, 35),
    },
    {
        "id": "neogeo",
        "title": "SNK Neo-Geo",
        "subtitle": "24-BIT // 330 MEGA PRO-GEAR (Metal Slug, KOF 2002)",
        "type": "CONSOLE",
        "badge": "NEO-GEO",
        "cover": "red.png",
        "color": (230, 190, 40),
    },
    {
        "id": "nds",
        "title": "Nintendo DS",
        "subtitle": "DUAL SCREEN // POKÉMON WHITE 2, MARIO KART DS",
        "type": "CONSOLE",
        "badge": "NDS",
        "cover": "destiny.png",
        "color": (150, 165, 185),
    },
    {
        "id": "wii",
        "title": "Nintendo Wii",
        "subtitle": "MOTION CONTROL // WII SPORTS, MARIO GALAXY",
        "type": "CONSOLE",
        "badge": "WII",
        "cover": "detroit.png",
        "color": (170, 195, 220),
    },
    {
        "id": "community",
        "title": "Comunidad C.C.I.",
        "subtitle": "CHATS PRIVADOS, GRUPOS Y RETOS MULTIJUGADOR",
        "type": "COMMUNITY",
        "badge": "HUB",
        "cover": "friends.png",
        "color": (34, 197, 94),
    },
]


class PS4DashboardUI:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720):
        self.w = screen_w
        self.h = screen_h
        self.active_layer = "RIBBON"  # "TOPBAR" o "RIBBON"
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
            self.font_tile_title = pygame.font.Font(font_file, 18)
            self.font_btn = pygame.font.Font(font_file, 14)
        except Exception:
            self.font_title = pygame.font.SysFont("Helvetica, Arial", 28, bold=True)
            self.font_subtitle = pygame.font.SysFont("Helvetica, Arial", 15)
            self.font_badge = pygame.font.SysFont("Courier, monospace", 13, bold=True)
            self.font_clock = pygame.font.SysFont("Helvetica, Arial", 18, bold=True)
            self.font_top = pygame.font.SysFont("Helvetica, Arial", 14)
            self.font_tile_title = pygame.font.SysFont("Helvetica, Arial", 18, bold=True)
            self.font_btn = pygame.font.SysFont("Helvetica, Arial", 14, bold=True)

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

        # Cargar iconos de la barra superior
        self.icons = {}
        for name in ("plus", "friends", "trophy", "settings", "off", "user", "start", "ps"):
            ip = ROOT / "assets_ps4" / "icons" / f"{name}.png"
            if ip.exists():
                try:
                    self.icons[name] = pygame.image.load(str(ip)).convert_alpha()
                except Exception:
                    pass

        # Pre-cargar y cachear carátulas de juegos/consolas
        self.covers = {}
        for item in RIBBON_ITEMS:
            cname = item.get("cover")
            if cname:
                cp = ROOT / "assets_ps4" / "img" / cname
                if cp.exists():
                    try:
                        self.covers[cname] = pygame.image.load(str(cp)).convert_alpha()
                    except Exception:
                        pass

        # Definición de items de la barra superior
        self.top_items = [
            {"id": "plus", "label": "C.C.I. +", "icon": "plus", "action": "GROUPS"},
            {"id": "user", "label": "Alex (Nvl 12)", "icon": "user", "action": "PROFILE"},
            {"id": "friends", "label": "Amigos (3)", "icon": "friends", "action": "GROUPS"},
            {"id": "trophy", "label": "Trofeos", "icon": "trophy", "action": "ACHIEVEMENTS"},
            {"id": "settings", "label": "Ajustes", "icon": "settings", "action": "SETTINGS"},
            {"id": "off", "label": "Apagar", "icon": "off", "action": "QUIT"},
        ]

        # Estructuras para detección de clics y hover
        self.top_rects: list[pygame.Rect] = []
        self.card_rects: list[pygame.Rect] = []
        self.iniciar_btn_rect: pygame.Rect | None = None

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
        """Maneja eventos de ratón, teclado y joystick."""

        # 1. RATÓN: Detección de Hover (movimiento)
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos

            # Hover en la barra superior
            for idx, r in enumerate(self.top_rects):
                if r.collidepoint(mx, my):
                    if self.active_layer != "TOPBAR" or self.selected_top_idx != idx:
                        self.active_layer = "TOPBAR"
                        self.selected_top_idx = idx
                        self._play_sfx(self.sfx_nav)
                    return None

            # Hover en las tarjetas del Ribbon
            for idx, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    if self.active_layer != "RIBBON" or self.selected_tile_idx != idx:
                        self.active_layer = "RIBBON"
                        self.selected_tile_idx = idx
                        self._play_sfx(self.sfx_nav)
                    return None

        # 2. RATÓN: Clics Izquierdos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Clic en items de la barra superior
            for idx, r in enumerate(self.top_rects):
                if r.collidepoint(mx, my):
                    item = self.top_items[idx]
                    if item["id"] == "off":
                        self._play_sfx(self.sfx_off)
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                        return {"action": "QUIT"}
                    self._play_sfx(self.sfx_reward)
                    return {"action": "TOPBAR_ACTION", "item": item}

            # Clic en el botón INICIAR dedicado del mosaico enfocado
            if self.iniciar_btn_rect and self.iniciar_btn_rect.collidepoint(mx, my):
                item = RIBBON_ITEMS[self.selected_tile_idx]
                self._play_sfx(self.sfx_reward)
                return {"action": "SELECT_ITEM", "item": item}

            # Clic en mosaicos de la cinta
            for idx, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    if self.selected_tile_idx == idx and self.active_layer == "RIBBON":
                        item = RIBBON_ITEMS[idx]
                        self._play_sfx(self.sfx_reward)
                        return {"action": "SELECT_ITEM", "item": item}
                    else:
                        self.active_layer = "RIBBON"
                        self.selected_tile_idx = idx
                        self._play_sfx(self.sfx_nav)
                        return None

        # 3. RATÓN: Rueda de desplazamiento (Scroll)
        elif event.type == pygame.MOUSEWHEEL:
            if event.y < 0:  # Hacia abajo / derecha
                if self.selected_tile_idx < len(RIBBON_ITEMS) - 1:
                    self.active_layer = "RIBBON"
                    self.selected_tile_idx += 1
                    self._play_sfx(self.sfx_nav)
            elif event.y > 0:  # Hacia arriba / izquierda
                if self.selected_tile_idx > 0:
                    self.active_layer = "RIBBON"
                    self.selected_tile_idx -= 1
                    self._play_sfx(self.sfx_nav)

        # 4. TECLADO: Flechas, WASD, Enter, Espacio, Escape
        elif event.type == pygame.KEYDOWN:
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
                        return {"action": "QUIT"}
                    self._play_sfx(self.sfx_reward)
                    return {"action": "TOPBAR_ACTION", "item": top_sel}
                elif event.key == pygame.K_ESCAPE:
                    self.active_layer = "RIBBON"
                    self._play_sfx(self.sfx_nav)

        # 5. MANDO / JOYSTICK: D-pad y Botones
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  # Botón Cruz / A
                if self.active_layer == "RIBBON":
                    item = RIBBON_ITEMS[self.selected_tile_idx]
                    self._play_sfx(self.sfx_reward)
                    return {"action": "SELECT_ITEM", "item": item}
                elif self.active_layer == "TOPBAR":
                    top_sel = self.top_items[self.selected_top_idx]
                    if top_sel["id"] == "off":
                        self._play_sfx(self.sfx_off)
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                        return {"action": "QUIT"}
                    self._play_sfx(self.sfx_reward)
                    return {"action": "TOPBAR_ACTION", "item": top_sel}
            elif event.button == 1:  # Botón Círculo / B
                if self.active_layer == "TOPBAR":
                    self.active_layer = "RIBBON"
                    self._play_sfx(self.sfx_nav)

        return None

    def render(self, surface: pygame.Surface):
        self.anim_timer += 0.025

        # 1. Fondo PS4 (textura oficial o azul dinámico)
        if self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill(COLOR_PS_BLUE)
            # Ondas procedurales suaves
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

        # 2. Barra Superior de Funciones (Top Bar) con botones funcionales y separados
        self._render_topbar(surface)

        # 3. Cinta Central de Mosaicos con separación garantizada sin roturas
        self._render_ribbon(surface)

        # 4. Barra Inferior con Guía de Botones PlayStation
        self._render_bottom_legend(surface)

    def _render_topbar(self, surface: pygame.Surface):
        top_y = 38
        is_top_active = (self.active_layer == "TOPBAR")

        # Notificación ticker a la izquierda
        ticker_txt = self.font_top.render("C.C.I. SYSTEM — VIRTUAL CONSOLE v2.1.0", True, COLOR_MUTED)
        surface.blit(ticker_txt, (50, top_y + 6))

        # Cálculo de botones superiores con suficiente separación
        self.top_rects = []
        base_x = 450
        spacing = 115

        for idx, item in enumerate(self.top_items):
            ix = base_x + idx * spacing
            is_sel = is_top_active and (idx == self.selected_top_idx)

            # Rectángulo clickeable para este botón
            pill_w = spacing - 10
            pill_rect = pygame.Rect(ix - 6, top_y, pill_w, 34)
            self.top_rects.append(pill_rect)

            # Fondo píldora si está seleccionado / hover
            if is_sel:
                pygame.draw.rect(surface, (255, 255, 255, 55), pill_rect, border_radius=17)
                pygame.draw.rect(surface, COLOR_WHITE, pill_rect, width=2, border_radius=17)

            # Icono
            icon_name = item.get("icon")
            icon_img = self.icons.get(icon_name)
            if icon_img:
                scaled_icon = pygame.transform.smoothscale(icon_img, (20, 20))
                surface.blit(scaled_icon, (ix, top_y + 7))
            else:
                pygame.draw.circle(surface, COLOR_WHITE if is_sel else COLOR_MUTED, (ix + 10, top_y + 17), 7)

            # Etiqueta de texto
            lbl_color = COLOR_WHITE if is_sel else COLOR_MUTED
            short_lbl = item["label"].split(" ")[0]
            lbl = self.font_top.render(short_lbl, True, lbl_color)
            surface.blit(lbl, (ix + 26, top_y + 7))

        # Reloj digital en vivo a la derecha extrema
        now_str = datetime.datetime.now().strftime("%H:%M")
        clock_txt = self.font_clock.render(now_str, True, COLOR_WHITE)
        surface.blit(clock_txt, (self.w - 85, top_y + 6))

    def _render_ribbon(self, surface: pygame.Surface):
        is_ribbon_active = (self.active_layer == "RIBBON")
        sel_idx = self.selected_tile_idx

        # Dimensiones de tarjetas
        card_w_normal, card_h_normal = 190, 190
        card_w_focused, card_h_focused = 245, 245
        gap = 28  # Espacio exacto garantizado entre tarjetas consecutivas
        baseline_y = 440  # Línea base inferior para alinear las tarjetas

        # Ancho y alto de cada tarjeta según su estado
        widths = []
        heights = []
        for i in range(len(RIBBON_ITEMS)):
            if i == sel_idx and is_ribbon_active:
                widths.append(card_w_focused)
                heights.append(card_h_focused)
            else:
                widths.append(card_w_normal)
                heights.append(card_h_normal)

        # Cálculo secuencial de posiciones X relativas
        # Esto GARANTIZA matemáticamente que NINGUNA tarjeta colisione ni se rompa
        rel_x = [0]
        for i in range(1, len(RIBBON_ITEMS)):
            rel_x.append(rel_x[-1] + widths[i - 1] + gap)

        # Posicionamiento de la cámara: anclar la tarjeta seleccionada a un X visible
        target_scroll = 90 - rel_x[sel_idx]
        self.scroll_x += (target_scroll - self.scroll_x) * 0.22

        self.card_rects = []
        self.iniciar_btn_rect = None

        # Renderizar cada tarjeta
        for idx, item in enumerate(RIBBON_ITEMS):
            is_sel = (idx == sel_idx)
            cw = widths[idx]
            ch = heights[idx]

            cx = rel_x[idx] + int(self.scroll_x)
            cy = baseline_y - ch

            card_rect = pygame.Rect(cx, cy, cw, ch)
            self.card_rects.append(card_rect)

            # Descartar si está fuera de pantalla
            if cx + cw < -60 or cx > self.w + 60:
                continue

            # Superficie de la tarjeta
            card_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)

            # Fondo base con gradiente
            bg_base = item.get("color", (40, 60, 90))
            pygame.draw.rect(card_surf, (bg_base[0] // 3, bg_base[1] // 3, bg_base[2] // 3, 240), (0, 0, cw, ch), border_radius=10)

            # Carátula oficial de juego / consola
            cover_img = self.covers.get(item.get("cover"))
            if cover_img:
                if is_sel and is_ribbon_active:
                    # En foco: dejar espacio inferior para el botón INICIAR
                    art_h = ch - 44
                    scaled_art = pygame.transform.smoothscale(cover_img, (cw, art_h))
                    card_surf.blit(scaled_art, (0, 0))
                else:
                    # Normal: carátula completa
                    scaled_art = pygame.transform.smoothscale(cover_img, (cw, ch))
                    card_surf.blit(scaled_art, (0, 0))
            else:
                # Símbolo vectorial si no hay carátula
                sym_t = self.font_tile_title.render(item.get("icon_symbol", item["title"]), True, COLOR_WHITE)
                card_surf.blit(sym_t, sym_t.get_rect(center=(cw // 2, ch // 2 - 10)))

            # Modo Enfocado: Borde blanco PS4 y botón 'INICIAR'
            if is_sel and is_ribbon_active:
                # Resplandor exterior
                glow_r = pygame.Rect(cx - 3, cy - 3, cw + 6, ch + 6)
                pygame.draw.rect(surface, (255, 255, 255, 50), glow_r, width=2, border_radius=14)

                # Borde nítido blanco interior
                pygame.draw.rect(card_surf, COLOR_FOCUS_GLOW, (0, 0, cw, ch), width=3, border_radius=10)

                # Botón 'INICIAR' dedicado en la parte inferior de la tarjeta
                btn_h = 36
                btn_y_local = ch - btn_h - 4
                btn_pill = pygame.Surface((cw - 12, btn_h), pygame.SRCALPHA)
                pygame.draw.rect(btn_pill, COLOR_WHITE, (0, 0, cw - 12, btn_h), border_radius=6)
                start_t = self.font_btn.render("▶  INICIAR", True, (10, 20, 40))
                btn_pill.blit(start_t, start_t.get_rect(center=((cw - 12) // 2, btn_h // 2)))
                card_surf.blit(btn_pill, (6, btn_y_local))

                self.iniciar_btn_rect = pygame.Rect(cx + 6, cy + btn_y_local, cw - 12, btn_h)

            else:
                # Modo Normal: Borde sutil y badge en la parte inferior
                pygame.draw.rect(card_surf, (255, 255, 255, 35), (0, 0, cw, ch), width=1, border_radius=10)

                # Franja oscura inferior con el badge
                badge_bar = pygame.Surface((cw, 28), pygame.SRCALPHA)
                badge_bar.fill((0, 0, 0, 160))
                badge_t = self.font_badge.render(item["badge"], True, COLOR_MUTED)
                badge_bar.blit(badge_t, badge_t.get_rect(center=(cw // 2, 14)))
                card_surf.blit(badge_bar, (0, ch - 28))

            surface.blit(card_surf, (cx, cy))

            # Si es el mosaico seleccionado: dibujar título y subtítulo DEBAJO de la tarjeta
            if is_sel:
                info_y = baseline_y + 18
                main_t = self.font_title.render(item["title"], True, COLOR_WHITE)
                surface.blit(main_t, (cx, info_y))

                sub_t = self.font_subtitle.render(item["subtitle"], True, COLOR_MUTED)
                surface.blit(sub_t, (cx, info_y + 36))

    def _render_bottom_legend(self, surface: pygame.Surface):
        bar_y = self.h - 46
        pygame.draw.line(surface, (255, 255, 255, 20), (0, bar_y), (self.w, bar_y), 1)

        legend_items = [
            ("⌧", "Iniciar"),
            ("◯", "Atrás"),
            ("⇦ ⇨", "Desplazar"),
            ("⇧ ⇩", "Barra Superior / Mosaicos"),
        ]

        cur_x = 50
        for glyph, text in legend_items:
            gt = self.font_badge.render(glyph, True, COLOR_WHITE)
            tt = self.font_top.render(text, True, COLOR_MUTED)

            surface.blit(gt, (cur_x, bar_y + 14))
            surface.blit(tt, (cur_x + gt.get_width() + 8, bar_y + 12))
            cur_x += gt.get_width() + tt.get_width() + 28


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
                elif item_id == "off":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt):
        pass

    def draw(self, screen):
        self.ui.render(screen)
