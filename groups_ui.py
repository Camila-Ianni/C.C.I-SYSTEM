"""
groups_ui.py - Pantallas funcionales de Grupos y Comunidades para C.C.I. SYSTEM.

Implementa los dos estados de interfaz gráfica basados en el diseño pixel art:
1. GroupsHubState ('GROUPS'): Vista general de gestión de grupos, chats privados,
   solicitudes, tarjetas de comunidades y panel lateral de detalle con botón 'Entrar al grupo'.
2. CommunityViewState ('COMMUNITY'): Vista interna del grupo con selector lateral de comunidades,
   categorías y canales (# general, voz, eventos), chat interactivo en tiempo real con
   tarjetas multimedia, lista de miembros y barra de estado.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pygame

from sidebar_ui import (
    LOGICAL_H,
    LOGICAL_W,
    SIDEBAR_W,
    draw_sidebar,
    load_sidebar,
    make_sidebar_font,
    sidebar_destination,
)
from states import BaseState

ROOT = Path(__file__).resolve().parent

# Catálogo predefinido de comunidades sincronizado con el diseño de C.C.I. SYSTEM
COMMUNITIES_CATALOG = [
    {
        "id": "night_raid",
        "name": "NIGHT RAID",
        "badge": "👑",
        "type": "Grupo privado",
        "is_private": True,
        "description": "Comunidad enfocada en juegos competitivos, eventos y proyectos de C.C.I.",
        "members": 24,
        "online": 5,
        "channels_count": 12,
        "voice_count": 3,
        "banner_path": "assets/communities/banner_night_raid.png",
        "emblem_path": "assets/communities/emblem_wolf.png",
        "channels": {
            "info": ["anuncios", "reglas", "bienvenidas"],
            "text": ["general", "off-topic", "clips-y-memes", "busqueda-de-equipo", "sugerencias"],
            "voice": [
                {"name": "Sala principal", "users": 5, "max": 16},
                {"name": "Gaming", "users": 3, "max": 8},
                {"name": "Rankeds", "users": 0, "max": 5},
                {"name": "Streaming", "users": 1, "max": 4},
            ],
        },
    },
    {
        "id": "sakura_club",
        "name": "SAKURA CLUB",
        "badge": "🌸",
        "type": "Grupo público",
        "is_private": False,
        "description": "Espacio chill de anime, música lofi, arte pixel y charlas nocturnas.",
        "members": 18,
        "online": 3,
        "channels_count": 8,
        "voice_count": 2,
        "banner_path": "assets/communities/banner_sakura_club.png",
        "emblem_path": "assets/communities/emblem_sakura.png",
        "channels": {
            "info": ["anuncios", "reglas"],
            "text": ["general", "arte-y-dibujo", "musica-lofi"],
            "voice": [
                {"name": "Chill Room", "users": 2, "max": 10},
                {"name": "Musica 24/7", "users": 1, "max": 15},
            ],
        },
    },
    {
        "id": "da_vinci_team",
        "name": "DA VINCI TEAM",
        "badge": "⚙️",
        "type": "Grupo privado",
        "is_private": True,
        "description": "Desarrolladores, modders y competidores de Da Vinci Fighters.",
        "members": 12,
        "online": 2,
        "channels_count": 10,
        "voice_count": 4,
        "banner_path": "assets/communities/banner_da_vinci.png",
        "emblem_path": "assets/communities/emblem_gear.png",
        "channels": {
            "info": ["actualizaciones", "reglas-del-torneo"],
            "text": ["general", "frame-data", "estrategias", "bugs-y-feedback"],
            "voice": [
                {"name": "Practica Dojo", "users": 2, "max": 6},
                {"name": "Arena 1v1", "users": 0, "max": 2},
            ],
        },
    },
    {
        "id": "pixel_squad",
        "name": "PIXEL SQUAD",
        "badge": "🎮",
        "type": "Grupo público",
        "is_private": False,
        "description": "Comunidad retro gaming, speedruns y torneos de arcade clásicos.",
        "members": 30,
        "online": 9,
        "channels_count": 14,
        "voice_count": 5,
        "banner_path": "assets/communities/banner_pixel_squad.png",
        "emblem_path": "assets/communities/emblem_gamepad.png",
        "channels": {
            "info": ["torneos", "records"],
            "text": ["general", "speedruns", "high-scores", "capturas"],
            "voice": [
                {"name": "Arcade Room", "users": 4, "max": 12},
                {"name": "Co-Op Squad", "users": 2, "max": 4},
            ],
        },
    },
    {
        "id": "kpop_zone",
        "name": "K-POP ZONE",
        "badge": "🎵",
        "type": "Grupo público",
        "is_private": False,
        "description": "Fanáticos del K-Pop, ritmos coreanos, streams y playlists compartidas.",
        "members": 56,
        "online": 14,
        "channels_count": 9,
        "voice_count": 3,
        "banner_path": "assets/communities/banner_kpop.png",
        "emblem_path": "assets/communities/emblem_music.png",
        "channels": {
            "info": ["novedades", "lanzamientos"],
            "text": ["general", "recs-musicales", "mv-favoritos"],
            "voice": [
                {"name": "Listening Party", "users": 6, "max": 20},
                {"name": "Karaoke", "users": 3, "max": 8},
            ],
        },
    },
    {
        "id": "cosmos",
        "name": "COSMOS",
        "badge": "🪐",
        "type": "Grupo público",
        "is_private": False,
        "description": "Exploración espacial, ciencia ficción, sci-fi games y astronomía.",
        "members": 20,
        "online": 4,
        "channels_count": 11,
        "voice_count": 4,
        "banner_path": "assets/communities/banner_cosmos.png",
        "emblem_path": "assets/communities/emblem_cosmos.png",
        "channels": {
            "info": ["noticias-espaciales"],
            "text": ["general", "sci-fi-lore", "astrofotografia"],
            "voice": [
                {"name": "Estación Orbital", "users": 2, "max": 10},
                {"name": "Cabina de Vuelo", "users": 1, "max": 4},
            ],
        },
    },
]


def _load_asset_surface(rel_path: str, fallback_size=(64, 64)) -> pygame.Surface:
    full = ROOT / rel_path
    if full.exists():
        try:
            return pygame.image.load(str(full)).convert_alpha()
        except Exception:
            pass
    surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
    surf.fill((40, 45, 55, 200))
    return surf


# =============================================================================
# ESTADO 1: HUB GENERAL DE GRUPOS Y COMUNIDADES ('GROUPS')
# =============================================================================

class GroupsHubState(BaseState):
    """Pantalla general de grupos, chats privados, solicitudes y tarjetas de comunidad."""

    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()

        # Fondo base 1280x720
        bg_path = ROOT / "pantallas" / "finales_entrega" / "Interfaz_Grupos_Hub.png"
        if bg_path.exists():
            self.background = pygame.image.load(str(bg_path)).convert()
            if self.background.get_size() != (LOGICAL_W, LOGICAL_H):
                self.background = pygame.transform.smoothscale(self.background, (LOGICAL_W, LOGICAL_H))
        else:
            self.background = pygame.Surface((LOGICAL_W, LOGICAL_H))
            self.background.fill((10, 12, 16))

        # Cargar recursos cacheados
        self.banners = {}
        self.emblems = {}
        for c in COMMUNITIES_CATALOG:
            self.banners[c["id"]] = _load_asset_surface(c["banner_path"], (400, 100))
            self.emblems[c["id"]] = _load_asset_surface(c["emblem_path"], (64, 64))

        self.assistant_img = _load_asset_surface("assets/communities/assistant.png", (90, 90))
        self.avatar_alex = _load_asset_surface("assets/communities/avatar_alex.png", (48, 48))

        # Fuentes
        self.font_title = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_subtitle = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_bold = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_normal = pygame.font.SysFont("Arial", 13)
        self.font_small = pygame.font.SysFont("Arial", 11)

        # Estado interactivo
        self.selected_index = 0
        self.active_tab = 0  # 0: MIS GRUPOS, 1: CHATS PRIVADOS, 2: SOLICITUDES
        self.search_query = ""
        self.search_active = False
        self.anim_time = 0.0

        # Zonas interactivas (rectángulos lógicos)
        # Pestañas
        self.tab_rects = [
            pygame.Rect(270, 195, 170, 36),  # MIS GRUPOS
            pygame.Rect(450, 195, 170, 36),  # CHATS PRIVADOS
            pygame.Rect(630, 195, 170, 36),  # SOLICITUDES
        ]
        # Barra de búsqueda
        self.search_rect = pygame.Rect(270, 248, 270, 30)

        # Cuadrícula de 6 tarjetas de comunidades (2 columnas x 3 filas)
        # Col 1: x=270, Col 2: x=580
        # Filas: y0=300, y1=398, y2=496
        # Tarjeta: ancho=295, alto=85
        self.card_rects = [
            pygame.Rect(270, 298, 300, 88),  # 0: Night Raid
            pygame.Rect(585, 298, 300, 88),  # 1: Sakura Club
            pygame.Rect(270, 396, 300, 88),  # 2: Da Vinci Team
            pygame.Rect(585, 396, 300, 88),  # 3: Pixel Squad
            pygame.Rect(270, 494, 300, 88),  # 4: K-Pop Zone
            pygame.Rect(585, 494, 300, 88),  # 5: Cosmos
        ]

        # Botones inferiores
        self.btn_crear_rect = pygame.Rect(270, 595, 170, 36)
        self.btn_unirse_rect = pygame.Rect(455, 595, 185, 36)

        # Botón entrar al grupo (panel derecho)
        self.btn_entrar_rect = pygame.Rect(930, 528, 310, 42)

    def enter(self, **kwargs):
        self.anim_time = 0.0
        idx = kwargs.get("community_index")
        if idx is not None and 0 <= idx < len(COMMUNITIES_CATALOG):
            self.selected_index = idx

    def exit(self):
        pass

    def _play_beep(self, pitch=600):
        try:
            from states import MenuState
            MenuState._play_beep_sound(pitch=pitch, duration_ms=45, volume=0.25)
        except Exception:
            pass

    def _open_selected_community(self):
        self._play_beep(850)
        comm = COMMUNITIES_CATALOG[self.selected_index]
        self.state_machine.change_state("COMMUNITY", community_id=comm["id"])

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if event.type == pygame.KEYDOWN:
                if self.search_active:
                    if event.key == pygame.K_RETURN:
                        self.search_active = False
                    elif event.key == pygame.K_ESCAPE:
                        self.search_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.search_query = self.search_query[:-1]
                    else:
                        if event.unicode and len(self.search_query) < 25:
                            self.search_query += event.unicode
                    continue

                if event.key == pygame.K_ESCAPE:
                    self.state_machine.change_state("MENU")
                    return

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self._open_selected_community()
                    return

                # Navegación en cuadrícula 2x3
                if event.key in (pygame.K_UP, pygame.K_w):
                    if self.selected_index >= 2:
                        self.selected_index -= 2
                        self._play_beep(650)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    if self.selected_index <= 3:
                        self.selected_index += 2
                        self._play_beep(550)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if self.selected_index % 2 == 1:
                        self.selected_index -= 1
                        self._play_beep(650)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.selected_index % 2 == 0 and self.selected_index + 1 < len(COMMUNITIES_CATALOG):
                        self.selected_index += 1
                        self._play_beep(550)

                # Atajos de navegación rápida
                if event.key == pygame.K_TAB:
                    self.active_tab = (self.active_tab + 1) % 3
                    self._play_beep(700)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self._screen_to_logical(event.pos)
                if not pos:
                    continue

                # Clic en barra lateral
                if pos[0] < SIDEBAR_W:
                    dest = sidebar_destination(pos)
                    if dest == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif dest:
                        self.state_machine.change_state(dest)
                    return

                # Clic en Pestañas
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(pos):
                        self.active_tab = i
                        self._play_beep(700)
                        return

                # Clic en barra de búsqueda
                if self.search_rect.collidepoint(pos):
                    self.search_active = True
                    return
                else:
                    self.search_active = False

                # Clic en tarjetas
                for i, r in enumerate(self.card_rects):
                    if r.collidepoint(pos):
                        if self.selected_index == i:
                            self._open_selected_community()
                        else:
                            self.selected_index = i
                            self._play_beep(600)
                        return

                # Clic en botón "Entrar al grupo"
                if self.btn_entrar_rect.collidepoint(pos):
                    self._open_selected_community()
                    return

    def update(self, dt: float):
        self.anim_time += dt

    def _screen_to_logical(self, screen_pos: tuple[int, int]) -> Optional[tuple[int, int]]:
        screen = pygame.display.get_surface()
        if not screen:
            return screen_pos
        sw, sh = screen.get_size()
        scale = min(sw / LOGICAL_W, sh / LOGICAL_H)
        offset_x = (sw - LOGICAL_W * scale) / 2
        offset_y = (sh - LOGICAL_H * scale) / 2
        x = (screen_pos[0] - offset_x) / scale
        y = (screen_pos[1] - offset_y) / scale
        if 0 <= x <= LOGICAL_W and 0 <= y <= LOGICAL_H:
            return int(x), int(y)
        return None

    def draw(self, screen: pygame.Surface):
        # Dibujar base
        self.canvas.blit(self.background, (0, 0))

        # Dibujar barra lateral común con 'GRUPOS' activo
        draw_sidebar(self.canvas, self.sidebar_surface, "groups", self.sidebar_font)

        # Dibujar resaltado de tarjeta seleccionada
        if 0 <= self.selected_index < len(self.card_rects):
            sel_rect = self.card_rects[self.selected_index]
            glow_surf = pygame.Surface((sel_rect.width + 6, sel_rect.height + 6), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 255, 255, 60), glow_surf.get_rect(), border_radius=8)
            pygame.draw.rect(glow_surf, (255, 255, 255, 200), glow_surf.get_rect(), width=2, border_radius=8)
            self.canvas.blit(glow_surf, (sel_rect.x - 3, sel_rect.y - 3))

        # Si hay búsqueda activa, renderizar indicador en la barra de búsqueda
        if self.search_active or self.search_query:
            cur_txt = self.search_query + ("|" if int(self.anim_time * 2) % 2 == 0 and self.search_active else "")
            txt_surf = self.font_normal.render(cur_txt, True, (240, 240, 240))
            # Limpiar un poco el campo de búsqueda
            pygame.draw.rect(self.canvas, (20, 22, 26), self.search_rect, border_radius=4)
            pygame.draw.rect(self.canvas, (100, 110, 130), self.search_rect, width=1, border_radius=4)
            self.canvas.blit(txt_surf, (self.search_rect.x + 8, self.search_rect.y + 6))

        # Renderizar datos dinámicos del panel derecho si no es Night Raid (Night Raid ya está en el fondo base)
        comm = COMMUNITIES_CATALOG[self.selected_index]
        if self.selected_index != 0:
            # Panel derecho x: 915, y: 220, w: 340, h: 420
            panel_rect = pygame.Rect(915, 220, 340, 370)
            pygame.draw.rect(self.canvas, (12, 14, 18), panel_rect, border_radius=12)
            pygame.draw.rect(self.canvas, (45, 50, 60), panel_rect, width=1, border_radius=12)

            # Banner superior del grupo seleccionado
            banner_surf = self.banners.get(comm["id"])
            if banner_surf:
                scaled_b = pygame.transform.smoothscale(banner_surf, (320, 85))
                self.canvas.blit(scaled_b, (925, 230))

            # Emblema
            emblem_surf = self.emblems.get(comm["id"])
            if emblem_surf:
                scaled_e = pygame.transform.smoothscale(emblem_surf, (44, 44))
                self.canvas.blit(scaled_e, (930, 325))

            # Título y badge
            title = f"{comm['name']} {comm['badge']}"
            t_surf = self.font_title.render(title, True, (255, 255, 255))
            self.canvas.blit(t_surf, (985, 328))

            badge_text = f"🔒 {comm['type']}" if comm['is_private'] else f"🌐 {comm['type']}"
            b_surf = self.font_small.render(badge_text, True, (160, 165, 175))
            self.canvas.blit(b_surf, (985, 350))

            # Descripción
            desc_lines = self._wrap_text(comm["description"], self.font_small, 310)
            for li, line in enumerate(desc_lines[:3]):
                d_surf = self.font_small.render(line, True, (185, 190, 200))
                self.canvas.blit(d_surf, (930, 385 + li * 16))

            # Estadísticas
            stats_y = 440
            stats = [
                ("👤 Miembros", str(comm["members"])),
                ("🟢 En línea", str(comm["online"])),
                ("# Canales", str(comm["channels_count"])),
                ("🔊 Salas de voz", str(comm["voice_count"])),
            ]
            for s_label, s_val in stats:
                l_surf = self.font_normal.render(s_label, True, (150, 155, 165))
                v_surf = self.font_bold.render(s_val, True, (240, 240, 245))
                self.canvas.blit(l_surf, (935, stats_y))
                self.canvas.blit(v_surf, (1200, stats_y))
                stats_y += 20

            # Botón entrar al grupo
            btn_surf = pygame.Surface((self.btn_entrar_rect.width, self.btn_entrar_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, (30, 35, 45), btn_surf.get_rect(), border_radius=8)
            pygame.draw.rect(btn_surf, (200, 205, 220), btn_surf.get_rect(), width=1, border_radius=8)
            txt_btn = self.font_bold.render("💬  Entrar al grupo  >", True, (255, 255, 255))
            btn_surf.blit(txt_btn, txt_btn.get_rect(center=btn_surf.get_rect().center))
            self.canvas.blit(btn_surf, self.btn_entrar_rect.topleft)

        # Escalar al tamaño de la ventana
        sw, sh = screen.get_size()
        scale = min(sw / LOGICAL_W, sh / LOGICAL_H)
        dw, dh = int(LOGICAL_W * scale), int(LOGICAL_H * scale)
        scaled_canvas = pygame.transform.smoothscale(self.canvas, (dw, dh))
        screen.fill((0, 0, 0))
        screen.blit(scaled_canvas, ((sw - dw) // 2, (sh - dh) // 2))

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        words = text.split(" ")
        lines = []
        current = ""
        for w in words:
            test = current + (" " if current else "") + w
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines


# =============================================================================
# ESTADO 2: VISTA INTERNA DE COMUNIDAD ('COMMUNITY')
# =============================================================================

class CommunityViewState(BaseState):
    """Pantalla interactiva dentro de una comunidad: canales, chat en tiempo real y miembros."""

    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()

        # Fondo base 1280x720
        bg_path = ROOT / "pantallas" / "finales_entrega" / "Interfaz_Comunidad_Night_Raid.png"
        if bg_path.exists():
            self.background = pygame.image.load(str(bg_path)).convert()
            if self.background.get_size() != (LOGICAL_W, LOGICAL_H):
                self.background = pygame.transform.smoothscale(self.background, (LOGICAL_W, LOGICAL_H))
        else:
            self.background = pygame.Surface((LOGICAL_W, LOGICAL_H))
            self.background.fill((10, 12, 16))

        # Cargar recursos adicionales
        self.weapon_card = _load_asset_surface("assets/communities/weapon_card.png", (220, 95))
        self.emblems = {}
        for c in COMMUNITIES_CATALOG:
            self.emblems[c["id"]] = _load_asset_surface(c["emblem_path"], (40, 40))

        # Fuentes
        self.font_title = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_channel = pygame.font.SysFont("Arial", 13)
        self.font_chat_author = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_chat_time = pygame.font.SysFont("Arial", 11)
        self.font_chat_body = pygame.font.SysFont("Arial", 13)
        self.font_small = pygame.font.SysFont("Arial", 11)

        # Comunidad actual
        self.community_id = "night_raid"
        self.current_channel = "general"
        self.connected_voice = None
        self.anim_time = 0.0

        # Historial de chat dinámico para #general
        self.chat_messages: List[Dict[str, Any]] = [
            {"author": "ALEX", "badge": "👑", "time": "Hoy 18:24", "text": "¿Alguien para unas partidas esta noche? 🎮"},
            {"author": "MIRA", "badge": "", "time": "Hoy 18:26", "text": "¡Yo me sumo! Estuve probando el nuevo mapa."},
            {"author": "KAI", "badge": "", "time": "Hoy 18:27", "text": "También me copo, armamos sala en la de Gaming?"},
            {"author": "ALEX", "badge": "👑", "time": "Hoy 18:28", "text": "Dale, en 10 min la creo. 👌"},
            {"author": "MIRA", "badge": "", "time": "Hoy 18:35", "text": "Les dejo el skin que conseguí hoy 👀", "has_attachment": True},
            {"author": "KAI", "badge": "", "time": "Hoy 18:40", "text": "Está increíble 🔥"},
        ]

        # Barra de entrada de texto interactiva
        self.input_text = ""
        self.input_rect = pygame.Rect(495, 620, 480, 36)
        self.input_active = True

        # Zonas interactivas de la columna de comunidades secundarias
        self.server_icon_rects = [
            (pygame.Rect(185, 150 + i * 54, 46, 46), comm["id"])
            for i, comm in enumerate(COMMUNITIES_CATALOG)
        ]
        # Botón volver al hub (arriba del selector de comunidades)
        self.btn_back_hub_rect = pygame.Rect(185, 100, 46, 42)

        # Canales interactivos
        self.channel_rects = {
            "general": pygame.Rect(250, 275, 175, 26),
            "off-topic": pygame.Rect(250, 305, 175, 26),
            "clips-y-memes": pygame.Rect(250, 335, 175, 26),
            "busqueda-de-equipo": pygame.Rect(250, 365, 175, 26),
            "sugerencias": pygame.Rect(250, 395, 175, 26),
        }
        self.voice_rects = {
            "Sala principal": pygame.Rect(250, 455, 175, 26),
            "Gaming": pygame.Rect(250, 485, 175, 26),
            "Rankeds": pygame.Rect(250, 515, 175, 26),
            "Streaming": pygame.Rect(250, 545, 175, 26),
        }

    def enter(self, **kwargs):
        self.anim_time = 0.0
        cid = kwargs.get("community_id")
        if cid:
            self.community_id = cid

    def exit(self):
        pass

    def _play_beep(self, pitch=600):
        try:
            from states import MenuState
            MenuState._play_beep_sound(pitch=pitch, duration_ms=45, volume=0.25)
        except Exception:
            pass

    def _send_current_message(self):
        if not self.input_text.strip():
            return
        msg = self.input_text.strip()
        self.input_text = ""
        now_str = time.strftime("Hoy %H:%M")
        self.chat_messages.append({
            "author": "ALEX",
            "badge": "👑",
            "time": now_str,
            "text": msg,
        })
        self._play_beep(800)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Volver a vista general de grupos
                    self.state_machine.change_state("GROUPS")
                    return

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._send_current_message()
                    return

                if event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    if event.unicode and len(self.input_text) < 120:
                        self.input_text += event.unicode

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self._screen_to_logical(event.pos)
                if not pos:
                    continue

                # Clic en barra lateral de la consola
                if pos[0] < 180:
                    dest = sidebar_destination(pos)
                    if dest == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif dest:
                        self.state_machine.change_state(dest)
                    return

                # Clic en botón volver al Hub de grupos
                if self.btn_back_hub_rect.collidepoint(pos):
                    self.state_machine.change_state("GROUPS")
                    return

                # Clic en iconos de servidor
                for r, cid in self.server_icon_rects:
                    if r.collidepoint(pos):
                        self.community_id = cid
                        self._play_beep(650)
                        return

                # Clic en canales de texto
                for ch_name, r in self.channel_rects.items():
                    if r.collidepoint(pos):
                        self.current_channel = ch_name
                        self._play_beep(600)
                        return

                # Clic en canales de voz
                for v_name, r in self.voice_rects.items():
                    if r.collidepoint(pos):
                        if self.connected_voice == v_name:
                            self.connected_voice = None
                        else:
                            self.connected_voice = v_name
                        self._play_beep(750)
                        return

                # Clic en campo de entrada
                if self.input_rect.collidepoint(pos):
                    self.input_active = True

    def update(self, dt: float):
        self.anim_time += dt

    def _screen_to_logical(self, screen_pos: tuple[int, int]) -> Optional[tuple[int, int]]:
        screen = pygame.display.get_surface()
        if not screen:
            return screen_pos
        sw, sh = screen.get_size()
        scale = min(sw / LOGICAL_W, sh / LOGICAL_H)
        offset_x = (sw - LOGICAL_W * scale) / 2
        offset_y = (sh - LOGICAL_H * scale) / 2
        x = (screen_pos[0] - offset_x) / scale
        y = (screen_pos[1] - offset_y) / scale
        if 0 <= x <= LOGICAL_W and 0 <= y <= LOGICAL_H:
            return int(x), int(y)
        return None

    def draw(self, screen: pygame.Surface):
        # Dibujar base
        self.canvas.blit(self.background, (0, 0))

        # Dibujar barra lateral de la consola con 'GRUPOS' activo
        draw_sidebar(self.canvas, self.sidebar_surface, "groups", self.sidebar_font)

        # Si hay mensajes dinámicos agregados por el usuario, renderizarlos sobre el área de chat
        # El área de chat va desde y=180 hasta y=600 en x: 450 a 1040
        if len(self.chat_messages) > 6:
            # Renderizar mensajes extra al pie del historial
            extra_msgs = self.chat_messages[6:]
            msg_y = 530
            for m in extra_msgs[-2:]:
                author_surf = self.font_chat_author.render(m["author"], True, (255, 255, 255))
                time_surf = self.font_chat_time.render(m["time"], True, (150, 155, 165))
                text_surf = self.font_chat_body.render(m["text"], True, (230, 235, 245))
                self.canvas.blit(author_surf, (510, msg_y))
                self.canvas.blit(time_surf, (560, msg_y + 1))
                self.canvas.blit(text_surf, (510, msg_y + 18))
                msg_y += 38

        # Renderizar texto que el usuario está escribiendo en el input
        if self.input_text or self.input_active:
            cur_txt = self.input_text + ("|" if int(self.anim_time * 2) % 2 == 0 else "")
            txt_surf = self.font_chat_body.render(cur_txt, True, (245, 245, 250))
            # Dibujar sobre el input box
            input_draw_rect = pygame.Rect(500, 626, 440, 24)
            pygame.draw.rect(self.canvas, (18, 20, 24), input_draw_rect)
            self.canvas.blit(txt_surf, (504, 628))

        # Indicador de voz conectada si hay alguna activa
        if self.connected_voice:
            v_box = pygame.Rect(250, 580, 175, 28)
            pygame.draw.rect(self.canvas, (25, 45, 30), v_box, border_radius=6)
            pygame.draw.rect(self.canvas, (40, 180, 80), v_box, width=1, border_radius=6)
            v_txt = self.font_small.render(f"🟢 Voz: {self.connected_voice}", True, (220, 255, 220))
            self.canvas.blit(v_txt, (256, 586))

        # Escalar al tamaño de la pantalla
        sw, sh = screen.get_size()
        scale = min(sw / LOGICAL_W, sh / LOGICAL_H)
        dw, dh = int(LOGICAL_W * scale), int(LOGICAL_H * scale)
        scaled_canvas = pygame.transform.smoothscale(self.canvas, (dw, dh))
        screen.fill((0, 0, 0))
        screen.blit(scaled_canvas, ((sw - dw) // 2, (sh - dh) // 2))
