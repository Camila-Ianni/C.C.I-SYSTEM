"""
groups_ui.py - Pantallas modulares y funcionales de Grupos y Comunidades para C.C.I. SYSTEM.

Construcción completa mediante recorte de assets, composición procedimental y elementos interactivos:
1. GroupsHubState ('GROUPS'):
   - Pestañas funcionales: 'MIS GRUPOS' (con 6 tarjetas modulares), 'CHATS PRIVADOS' y 'SOLICITUDES'.
   - Tarjetas de comunidad renderizadas individualmente con banner, viñeta, marco biselado,
     emblema recortado, tipografía nativa, contador de miembros/en línea y estado activo.
   - Búsqueda en tiempo real, selector de ordenación y alternador de vista (cuadrícula/lista).
   - Panel lateral derecho sincronizado dinámicamente con el grupo seleccionado y botón 'Entrar al grupo'.
   - Barra lateral nativa con 'GRUPOS' seleccionado e interacción directa sin desalineaciones.
   - Diálogo inferior de la asistente Cami con pistas de navegación.

2. CommunityViewState ('COMMUNITY'):
   - Selector lateral de comunidades con íconos circulares/redondeados e indicador activo blanco.
   - Columna interactiva de canales categorizados (# general, off-topic, voz con conteo de usuarios).
   - Canal de voz interactivo con estado de conexión en vivo y controles de audio.
   - Chat en tiempo real con lista de mensajes desplazable, avatares pixel art, tarjeta de arma
     y chips de reacciones interactivas (corazón, pulgar, chispas) con incremento al clic.
   - Barra de entrada de texto interactiva con escritura en vivo, cursor parpadeante y botón enviar.
   - Lista derecha de miembros por estado (En línea, Ausente, Desconectado) con avatares y actividades.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame

from sidebar_ui import (
    LOGICAL_H,
    LOGICAL_W,
    SIDEBAR_W,
    sidebar_destination,
)
from states import BaseState

ROOT = Path(__file__).resolve().parent

# Catálogo completo de comunidades con datos, banners y emblemas
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
        "banner": "assets/communities/banner_night_raid.png",
        "emblem": "assets/communities/emblem_wolf.png",
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
        "banner": "assets/communities/banner_sakura_club.png",
        "emblem": "assets/communities/emblem_sakura.png",
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
        "description": "Desarrolladores, modders y competidores oficiales de Da Vinci Fighters.",
        "members": 12,
        "online": 2,
        "channels_count": 10,
        "voice_count": 4,
        "banner": "assets/communities/banner_da_vinci.png",
        "emblem": "assets/communities/emblem_gear.png",
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
        "banner": "assets/communities/banner_pixel_squad.png",
        "emblem": "assets/communities/emblem_gamepad.png",
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
        "banner": "assets/communities/banner_kpop.png",
        "emblem": "assets/communities/emblem_music.png",
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
        "banner": "assets/communities/banner_cosmos.png",
        "emblem": "assets/communities/emblem_cosmos.png",
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

# Lista de chats privados
PRIVATE_CHATS_DATA = [
    {"name": "MIRA", "avatar": "avatar_mira.png", "status": "En llamada Gaming", "status_dot": (60, 220, 100), "last_msg": "¡Yo me sumo! Estuve probando el nuevo mapa.", "time": "18:26"},
    {"name": "KAI", "avatar": "avatar_guy_glasses.png", "status": "En línea", "status_dot": (60, 220, 100), "last_msg": "También me copo, armamos sala en la de Gaming?", "time": "18:27"},
    {"name": "ALEX", "avatar": "avatar_alex.png", "badge": "👑", "status": "Jugando: Da Vinci Fighters", "status_dot": (60, 220, 100), "last_msg": "Dale, en 10 min la creo. 👌", "time": "18:28"},
    {"name": "LUNA", "avatar": "avatar_girl_hoodie.png", "status": "Jugando: Minecraft", "status_dot": (60, 220, 100), "last_msg": "Subí los nuevos shaders al server.", "time": "17:40"},
    {"name": "ZERO", "avatar": "avatar_guy_blonde.png", "status": "Transmitiendo 🔴", "status_dot": (180, 80, 240), "last_msg": "¡Miren el stream, nueva build!", "time": "16:15"},
]

# Solicitudes pendientes
INVITATIONS_DATA = [
    {"type": "friend", "user": "KAI", "text": "KAI quiere ser tu amigo en C.C.I. SYSTEM", "time": "Hace 10 min"},
    {"type": "community", "user": "LUNA", "community": "SAKURA CLUB", "text": "LUNA te invitó a unirte a SAKURA CLUB", "time": "Hace 1 hora"},
]


def _safe_load_img(path: str, size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
    """Carga imagen de manera segura o crea superficie de respaldo si falta."""
    p = ROOT / path
    if p.exists():
        try:
            surf = pygame.image.load(str(p)).convert_alpha()
            if size:
                return pygame.transform.smoothscale(surf, size)
            return surf
        except Exception:
            pass
    fallback_w, fallback_h = size or (64, 64)
    res = pygame.Surface((fallback_w, fallback_h), pygame.SRCALPHA)
    res.fill((35, 40, 50, 220))
    return res


# =============================================================================
# ESTADO 1: HUB DE GRUPOS Y COMUNIDADES ('GROUPS')
# =============================================================================

class GroupsHubState(BaseState):
    """Pantalla interactiva de gestión de comunidades, chats privados y solicitudes."""

    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))

        # Base del chasis limpia 1280x720
        self.base_bg = _safe_load_img("assets/ui_sliced/hub_base_720.png", (LOGICAL_W, LOGICAL_H))
        self.assistant_img = _safe_load_img("assets/ui_sliced/asst_portrait_main.png", (78, 78))

        # Precargar banners y emblemas
        self.banners: Dict[str, pygame.Surface] = {}
        self.emblems: Dict[str, pygame.Surface] = {}
        for c in COMMUNITIES_CATALOG:
            self.banners[c["id"]] = _safe_load_img(c["banner"], (640, 102))
            self.emblems[c["id"]] = _safe_load_img(c["emblem"], (64, 64))

        # Precargar avatares
        self.avatars: Dict[str, pygame.Surface] = {}
        for fn in ["avatar_alex.png", "avatar_mira.png", "avatar_guy_glasses.png", "avatar_girl_hoodie.png", "avatar_guy_blonde.png"]:
            self.avatars[fn] = _safe_load_img(f"assets/communities/{fn}", (48, 48))

        # Fuentes
        self.font_header = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_bold = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_normal = pygame.font.SysFont("Arial", 13)
        self.font_small = pygame.font.SysFont("Arial", 11)
        self.font_dialog = pygame.font.SysFont("Arial", 12)

        # Estado interno interactivo
        self.selected_index = 0
        self.active_tab = 0  # 0: MIS GRUPOS, 1: CHATS PRIVADOS, 2: SOLICITUDES
        self.search_query = ""
        self.search_active = False
        self.sort_mode = 0  # 0: Actividad reciente, 1: Miembros, 2: Alfabético
        self.sort_labels = ["Actividad reciente", "Más miembros", "Alfabético"]
        self.view_mode = "grid"  # 'grid' o 'list'
        self.anim_time = 0.0

        # Modal interactivo (crear grupo / unirse con código)
        self.modal_active: Optional[str] = None
        self.modal_input = ""

        # Rectángulos interactivos
        self.tab_rects = [
            pygame.Rect(265, 195, 170, 36),   # MIS GRUPOS
            pygame.Rect(445, 195, 170, 36),   # CHATS PRIVADOS
            pygame.Rect(625, 195, 170, 36),   # SOLICITUDES
        ]
        self.search_rect = pygame.Rect(268, 246, 240, 30)
        self.sort_rect = pygame.Rect(520, 246, 200, 30)
        self.btn_grid_rect = pygame.Rect(730, 246, 32, 30)
        self.btn_list_rect = pygame.Rect(768, 246, 32, 30)

        # Cuadrícula de tarjetas de comunidades (2 columnas x 3 filas)
        self.card_rects = [
            pygame.Rect(268, 296, 295, 86),  # 0: Night Raid
            pygame.Rect(578, 296, 295, 86),  # 1: Sakura Club
            pygame.Rect(268, 394, 295, 86),  # 2: Da Vinci Team
            pygame.Rect(578, 394, 295, 86),  # 3: Pixel Squad
            pygame.Rect(268, 492, 295, 86),  # 4: K-Pop Zone
            pygame.Rect(578, 492, 295, 86),  # 5: Cosmos
        ]

        # Botones de acción inferiores
        self.btn_crear_rect = pygame.Rect(268, 595, 160, 34)
        self.btn_unirse_rect = pygame.Rect(440, 595, 175, 34)

        # Botón entrar al grupo (panel derecho)
        self.btn_entrar_rect = pygame.Rect(930, 532, 305, 40)

        # Opciones de barra lateral
        self.sidebar_buttons = [
            ("INICIO", "MENU", pygame.Rect(40, 125, 140, 36)),
            ("JUEGOS", "LIBRARY", pygame.Rect(40, 170, 140, 36)),
            ("GRUPOS", "GROUPS", pygame.Rect(40, 215, 140, 36)),
            ("PERFIL", "PROFILE", pygame.Rect(40, 260, 140, 36)),
            ("LOGROS", "ACHIEVEMENTS", pygame.Rect(40, 305, 140, 36)),
            ("CONFIGURACIÓN", "SETTINGS", pygame.Rect(40, 350, 140, 36)),
            ("APAGAR", "QUIT", pygame.Rect(40, 395, 140, 36)),
        ]

    def enter(self, **kwargs):
        self.anim_time = 0.0
        self.modal_active = None
        self.modal_input = ""
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

    def _get_filtered_communities(self) -> List[Tuple[int, Dict[str, Any]]]:
        items = list(enumerate(COMMUNITIES_CATALOG))
        if self.search_query.strip():
            q = self.search_query.strip().lower()
            items = [(i, c) for i, c in items if q in c["name"].lower() or q in c["description"].lower()]

        if self.sort_mode == 1:
            items.sort(key=lambda x: x[1]["members"], reverse=True)
        elif self.sort_mode == 2:
            items.sort(key=lambda x: x[1]["name"])
        return items

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
                # Modal abierto
                if self.modal_active:
                    if event.key == pygame.K_ESCAPE:
                        self.modal_active = None
                        self.modal_input = ""
                    elif event.key == pygame.K_RETURN:
                        self._play_beep(800)
                        self.modal_active = None
                        self.modal_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.modal_input = self.modal_input[:-1]
                    else:
                        if event.unicode and len(self.modal_input) < 25:
                            self.modal_input += event.unicode
                    continue

                # Búsqueda activa
                if self.search_active:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
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
                    if self.active_tab == 0:
                        self._open_selected_community()
                    return

                # Navegación por teclado en cuadrícula
                if self.active_tab == 0:
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

                # Cambio rápido de pestaña con TAB
                if event.key == pygame.K_TAB:
                    self.active_tab = (self.active_tab + 1) % 3
                    self._play_beep(700)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self._screen_to_logical(event.pos)
                if not pos:
                    continue

                # Clic dentro de modal si está activo
                if self.modal_active:
                    modal_rect = pygame.Rect(400, 240, 480, 200)
                    if not modal_rect.collidepoint(pos):
                        self.modal_active = None
                        self.modal_input = ""
                    return

                # Clic en opciones de la barra lateral izquierda
                if pos[0] < 185:
                    for _label, dest, rect in self.sidebar_buttons:
                        if rect.collidepoint(pos):
                            if dest == "QUIT":
                                pygame.event.post(pygame.event.Event(pygame.QUIT))
                            elif dest != "GROUPS":
                                self._play_beep(700)
                                self.state_machine.change_state(dest)
                            return

                # Clic en Pestañas
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(pos):
                        self.active_tab = i
                        self._play_beep(700)
                        return

                # Clic en Búsqueda
                if self.search_rect.collidepoint(pos):
                    self.search_active = True
                    return
                else:
                    self.search_active = False

                # Clic en Ordenación
                if self.sort_rect.collidepoint(pos):
                    self.sort_mode = (self.sort_mode + 1) % len(self.sort_labels)
                    self._play_beep(600)
                    return

                # Clic en alternador de vista
                if self.btn_grid_rect.collidepoint(pos):
                    self.view_mode = "grid"
                    self._play_beep(600)
                    return
                if self.btn_list_rect.collidepoint(pos):
                    self.view_mode = "list"
                    self._play_beep(600)
                    return

                # Clic en tarjetas si estamos en pestaña 0
                if self.active_tab == 0:
                    filtered = self._get_filtered_communities()
                    for idx, (real_idx, _c) in enumerate(filtered):
                        if idx < len(self.card_rects) and self.card_rects[idx].collidepoint(pos):
                            if self.selected_index == real_idx:
                                self._open_selected_community()
                            else:
                                self.selected_index = real_idx
                                self._play_beep(600)
                            return

                    # Clic en botón "Entrar al grupo" del panel derecho
                    if self.btn_entrar_rect.collidepoint(pos):
                        self._open_selected_community()
                        return

                # Clic en botones inferiores
                if self.btn_crear_rect.collidepoint(pos):
                    self.modal_active = "CREAR GRUPO"
                    self.modal_input = ""
                    self._play_beep(750)
                    return
                if self.btn_unirse_rect.collidepoint(pos):
                    self.modal_active = "UNIRSE CON CÓDIGO"
                    self.modal_input = ""
                    self._play_beep(750)
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
        # 1. Dibujar chasis de base
        self.canvas.blit(self.base_bg, (0, 0))

        # 2. Resaltar pestaña activa de barra lateral 'GRUPOS'
        pill_rect = pygame.Rect(40, 215, 140, 36)
        pygame.draw.rect(self.canvas, (24, 27, 34), pill_rect, border_radius=6)
        pygame.draw.rect(self.canvas, (255, 255, 255), pygame.Rect(40, 218, 5, 30), border_radius=3)
        txt_grp = self.font_bold.render("GRUPOS", True, (255, 255, 255))
        self.canvas.blit(txt_grp, (58, 224))

        # 3. Limpiar zonas dinámicas para renderizado modular y sin solapamiento
        # Zona pestañas
        pygame.draw.rect(self.canvas, (11, 13, 17), pygame.Rect(260, 190, 560, 45))
        # Zona cuadrícula / lista
        pygame.draw.rect(self.canvas, (11, 13, 17), pygame.Rect(260, 290, 630, 298))
        # Zona panel lateral derecho
        pygame.draw.rect(self.canvas, (11, 13, 17), pygame.Rect(915, 215, 335, 365))
        # Zona texto diálogo asistente inferior
        pygame.draw.rect(self.canvas, (14, 16, 21), pygame.Rect(210, 635, 540, 55))

        # 4. Renderizar Pestañas Superiores
        tabs = [("MIS GRUPOS", "6"), ("CHATS PRIVADOS", "5"), ("SOLICITUDES", "2")]
        for i, (t_name, badge) in enumerate(tabs):
            r = self.tab_rects[i]
            is_active = (self.active_tab == i)
            bg_col = (28, 32, 42) if is_active else (18, 20, 26)
            border_col = (110, 120, 145) if is_active else (40, 44, 55)
            pygame.draw.rect(self.canvas, bg_col, r, border_radius=6)
            pygame.draw.rect(self.canvas, border_col, r, width=1, border_radius=6)

            txt_col = (255, 255, 255) if is_active else (160, 165, 178)
            label_surf = self.font_bold.render(t_name, True, txt_col)
            self.canvas.blit(label_surf, (r.x + 16, r.y + 9))

            # Badge pill
            badge_rect = pygame.Rect(r.right - 34, r.y + 8, 22, 18)
            b_bg = (55, 65, 85) if is_active else (30, 34, 44)
            pygame.draw.rect(self.canvas, b_bg, badge_rect, border_radius=4)
            b_txt = self.font_small.render(badge, True, (240, 240, 245))
            self.canvas.blit(b_txt, b_txt.get_rect(center=badge_rect.center))

        # 5. Barra de búsqueda y ordenación
        # Input búsqueda
        pygame.draw.rect(self.canvas, (16, 18, 24), self.search_rect, border_radius=5)
        b_border = (120, 135, 165) if self.search_active else (45, 50, 62)
        pygame.draw.rect(self.canvas, b_border, self.search_rect, width=1, border_radius=5)
        cur_q = self.search_query + ("|" if int(self.anim_time * 2) % 2 == 0 and self.search_active else "")
        q_show = cur_q if cur_q else "🔍 Buscar grupo o conversación..."
        q_col = (240, 240, 245) if cur_q else (120, 125, 135)
        self.canvas.blit(self.font_small.render(q_show, True, q_col), (self.search_rect.x + 10, self.search_rect.y + 7))

        # Selector ordenación
        pygame.draw.rect(self.canvas, (18, 20, 26), self.sort_rect, border_radius=5)
        pygame.draw.rect(self.canvas, (45, 50, 62), self.sort_rect, width=1, border_radius=5)
        sort_txt = f"ORDENAR: {self.sort_labels[self.sort_mode]} ▾"
        self.canvas.blit(self.font_small.render(sort_txt, True, (190, 195, 205)), (self.sort_rect.x + 10, self.sort_rect.y + 7))

        # Botones vista cuadrícula / lista
        for btn_r, is_sel, icon_t in [(self.btn_grid_rect, self.view_mode == "grid", "::"), (self.btn_list_rect, self.view_mode == "list", "≡")]:
            bg_c = (35, 42, 55) if is_sel else (18, 20, 26)
            pygame.draw.rect(self.canvas, bg_c, btn_r, border_radius=4)
            pygame.draw.rect(self.canvas, (65, 75, 95) if is_sel else (40, 44, 55), btn_r, width=1, border_radius=4)
            self.canvas.blit(self.font_bold.render(icon_t, True, (240, 240, 245) if is_sel else (140, 145, 155)), (btn_r.x + 8, btn_r.y + 5))

        # 6. Renderizado de Contenido según Pestaña Activa
        if self.active_tab == 0:
            # PESTAÑA: MIS GRUPOS
            filtered = self._get_filtered_communities()
            for idx, (real_idx, comm) in enumerate(filtered):
                if idx >= len(self.card_rects):
                    break
                r = self.card_rects[idx]
                is_selected = (self.selected_index == real_idx)

                # Superficie de tarjeta modular
                card_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)

                # Banner con viñeta
                b_surf = self.banners.get(comm["id"])
                if b_surf:
                    scaled_b = pygame.transform.smoothscale(b_surf, (r.width, r.height))
                    card_surf.blit(scaled_b, (0, 0))

                vignette = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                vignette.fill((8, 10, 14, 150))
                card_surf.blit(vignette, (0, 0))

                # Marco biselado y resaltado activo
                border_color = (255, 255, 255) if is_selected else (60, 68, 80)
                border_width = 2 if is_selected else 1
                pygame.draw.rect(card_surf, border_color, card_surf.get_rect(), width=border_width, border_radius=8)

                # Emblema en caja redondeada
                e_surf = self.emblems.get(comm["id"])
                e_box = pygame.Rect(8, 16, 54, 54)
                pygame.draw.rect(card_surf, (16, 20, 26, 230), e_box, border_radius=6)
                pygame.draw.rect(card_surf, (80, 90, 105), e_box, width=1, border_radius=6)
                if e_surf:
                    card_surf.blit(pygame.transform.smoothscale(e_surf, (46, 46)), (12, 20))

                # Nombre y badge
                title_txt = f"{comm['name']} {comm['badge']}"
                card_surf.blit(self.font_title.render(title_txt, True, (255, 255, 255)), (70, 22))

                # Estadísticas
                sub_txt = f"{comm['members']} miembros • {comm['online']} en línea"
                card_surf.blit(self.font_small.render(sub_txt, True, (185, 190, 200)), (70, 48))

                # Botón tres puntos
                card_surf.blit(self.font_title.render("⋮", True, (160, 165, 175)), (r.width - 20, 32))

                self.canvas.blit(card_surf, r.topleft)

            # Renderizado del Panel Derecho de Detalle
            sel_comm = COMMUNITIES_CATALOG[self.selected_index]
            panel_r = pygame.Rect(915, 218, 335, 362)
            pygame.draw.rect(self.canvas, (14, 16, 22), panel_r, border_radius=10)
            pygame.draw.rect(self.canvas, (50, 58, 72), panel_r, width=1, border_radius=10)

            # Banner superior
            b_det = self.banners.get(sel_comm["id"])
            if b_det:
                scaled_det = pygame.transform.smoothscale(b_det, (315, 80))
                self.canvas.blit(scaled_det, (925, 228))

            # Emblema, título y privacidad
            e_det = self.emblems.get(sel_comm["id"])
            if e_det:
                self.canvas.blit(pygame.transform.smoothscale(e_det, (42, 42)), (930, 318))
            self.canvas.blit(self.font_title.render(f"{sel_comm['name']} {sel_comm['badge']}", True, (255, 255, 255)), (980, 320))
            badge_str = f"🔒 {sel_comm['type']}" if sel_comm['is_private'] else f"🌐 {sel_comm['type']}"
            self.canvas.blit(self.font_small.render(badge_str, True, (155, 160, 172)), (980, 342))

            # Descripción
            lines = self._wrap_text(sel_comm["description"], self.font_small, 305)
            for li, l_str in enumerate(lines[:3]):
                self.canvas.blit(self.font_small.render(l_str, True, (190, 195, 205)), (930, 375 + li * 16))

            # Métricas
            stats_y = 432
            for s_name, s_val in [
                ("👤 Miembros", str(sel_comm["members"])),
                ("🟢 En línea", str(sel_comm["online"])),
                ("# Canales", str(sel_comm["channels_count"])),
                ("🔊 Salas de voz", str(sel_comm["voice_count"])),
            ]:
                self.canvas.blit(self.font_small.render(s_name, True, (150, 155, 165)), (932, stats_y))
                self.canvas.blit(self.font_bold.render(s_val, True, (245, 245, 250)), (1205, stats_y))
                stats_y += 21

            # Botón interactivo "Entrar al grupo >"
            pygame.draw.rect(self.canvas, (32, 38, 50), self.btn_entrar_rect, border_radius=8)
            pygame.draw.rect(self.canvas, (230, 235, 245), self.btn_entrar_rect, width=1, border_radius=8)
            btn_txt = self.font_bold.render("💬  Entrar al grupo  >", True, (255, 255, 255))
            self.canvas.blit(btn_txt, btn_txt.get_rect(center=self.btn_entrar_rect.center))

        elif self.active_tab == 1:
            # PESTAÑA: CHATS PRIVADOS (DMs)
            for di, dm in enumerate(PRIVATE_CHATS_DATA):
                dm_r = pygame.Rect(268, 296 + di * 56, 605, 50)
                pygame.draw.rect(self.canvas, (18, 21, 28), dm_r, border_radius=8)
                pygame.draw.rect(self.canvas, (45, 52, 65), dm_r, width=1, border_radius=8)

                av = self.avatars.get(dm["avatar"])
                if av:
                    self.canvas.blit(pygame.transform.smoothscale(av, (38, 38)), (dm_r.x + 8, dm_r.y + 6))

                # Dot de estado
                pygame.draw.circle(self.canvas, dm["status_dot"], (dm_r.x + 42, dm_r.y + 40), 5)

                name_txt = dm["name"] + (" " + dm.get("badge", "") if "badge" in dm else "")
                self.canvas.blit(self.font_title.render(name_txt, True, (255, 255, 255)), (dm_r.x + 55, dm_r.y + 8))
                self.canvas.blit(self.font_small.render(dm["status"], True, (150, 155, 165)), (dm_r.x + 55, dm_r.y + 28))
                self.canvas.blit(self.font_normal.render(f'"{dm["last_msg"]}"', True, (200, 205, 215)), (dm_r.x + 220, dm_r.y + 16))
                self.canvas.blit(self.font_small.render(dm["time"], True, (130, 135, 145)), (dm_r.right - 55, dm_r.y + 16))

            # Panel derecho en DMs
            panel_r = pygame.Rect(915, 218, 335, 362)
            pygame.draw.rect(self.canvas, (14, 16, 22), panel_r, border_radius=10)
            pygame.draw.rect(self.canvas, (50, 58, 72), panel_r, width=1, border_radius=10)
            self.canvas.blit(self.font_header.render("CHATS DIRECTOS", True, (255, 255, 255)), (935, 235))
            self.canvas.blit(self.font_small.render("Conversa de forma privada con tus contactos.", True, (160, 165, 175)), (935, 265))

        elif self.active_tab == 2:
            # PESTAÑA: SOLICITUDES
            for si, inv in enumerate(INVITATIONS_DATA):
                inv_r = pygame.Rect(268, 296 + si * 70, 605, 62)
                pygame.draw.rect(self.canvas, (18, 21, 28), inv_r, border_radius=8)
                pygame.draw.rect(self.canvas, (45, 52, 65), inv_r, width=1, border_radius=8)

                icon = "👤" if inv["type"] == "friend" else "🏰"
                self.canvas.blit(self.font_header.render(icon, True, (255, 255, 255)), (inv_r.x + 12, inv_r.y + 16))
                self.canvas.blit(self.font_bold.render(inv["text"], True, (240, 240, 250)), (inv_r.x + 48, inv_r.y + 12))
                self.canvas.blit(self.font_small.render(inv["time"], True, (140, 145, 155)), (inv_r.x + 48, inv_r.y + 36))

                # Botones Aceptar / Rechazar
                btn_ok = pygame.Rect(inv_r.right - 170, inv_r.y + 15, 75, 30)
                btn_no = pygame.Rect(inv_r.right - 85, inv_r.y + 15, 75, 30)
                pygame.draw.rect(self.canvas, (35, 95, 50), btn_ok, border_radius=5)
                pygame.draw.rect(self.canvas, (90, 35, 35), btn_no, border_radius=5)
                self.canvas.blit(self.font_small.render("Aceptar", True, (255, 255, 255)), (btn_ok.x + 16, btn_ok.y + 7))
                self.canvas.blit(self.font_small.render("Rechazar", True, (255, 255, 255)), (btn_no.x + 14, btn_no.y + 7))

        # 7. Diálogo de la Asistente Cami (inferior)
        dialog_texts = [
            "Gestiona tus grupos, chats privados y nuevas comunidades.",
            "Mensajería privada cifrada en tiempo real con amigos de C.C.I.",
            "Revisa tus invitaciones a comunidades y solicitudes de amistad.",
        ]
        self.canvas.blit(self.font_dialog.render(dialog_texts[self.active_tab], True, (240, 242, 248)), (215, 650))

        # 8. Modal Interactivo si está activo
        if self.modal_active:
            overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            self.canvas.blit(overlay, (0, 0))

            m_box = pygame.Rect(400, 240, 480, 200)
            pygame.draw.rect(self.canvas, (20, 24, 32), m_box, border_radius=10)
            pygame.draw.rect(self.canvas, (200, 210, 230), m_box, width=2, border_radius=10)

            self.canvas.blit(self.font_header.render(self.modal_active, True, (255, 255, 255)), (m_box.x + 25, m_box.y + 20))
            self.canvas.blit(self.font_normal.render("Introduce el nombre o código de acceso:", True, (170, 175, 185)), (m_box.x + 25, m_box.y + 55))

            in_box = pygame.Rect(m_box.x + 25, m_box.y + 90, 430, 36)
            pygame.draw.rect(self.canvas, (10, 12, 16), in_box, border_radius=5)
            pygame.draw.rect(self.canvas, (80, 90, 110), in_box, width=1, border_radius=5)

            inp_str = self.modal_input + ("|" if int(self.anim_time * 2) % 2 == 0 else "")
            self.canvas.blit(self.font_bold.render(inp_str, True, (255, 255, 255)), (in_box.x + 12, in_box.y + 9))

            self.canvas.blit(self.font_small.render("Presiona ENTER para confirmar o ESC para cancelar", True, (130, 135, 145)), (m_box.x + 25, m_box.y + 150))

        # Escalar al tamaño de pantalla del usuario
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
# ESTADO 2: VISTA INTERNA DEL GRUPO / COMUNIDAD ('COMMUNITY')
# =============================================================================

class CommunityViewState(BaseState):
    """Pantalla interactiva dentro de una comunidad: canales, chat en tiempo real y miembros."""

    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))

        # Base del chasis limpia 1280x720
        self.base_bg = _safe_load_img("assets/ui_sliced/nr_base_720.png", (LOGICAL_W, LOGICAL_H))
        self.weapon_card = _safe_load_img("assets/ui_sliced/card_weapon.png", (280, 155))

        # Precargar emblemas
        self.emblems: Dict[str, pygame.Surface] = {}
        for c in COMMUNITIES_CATALOG:
            self.emblems[c["id"]] = _safe_load_img(c["emblem"], (40, 40))

        # Precargar avatares
        self.avatars: Dict[str, pygame.Surface] = {}
        for fn in ["avatar_alex.png", "avatar_mira.png", "avatar_guy_glasses.png", "avatar_girl_hoodie.png", "avatar_guy_blonde.png"]:
            self.avatars[fn] = _safe_load_img(f"assets/communities/{fn}", (42, 42))

        # Fuentes
        self.font_header = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_cat = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_ch = pygame.font.SysFont("Arial", 13)
        self.font_ch_bold = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_author = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_time = pygame.font.SysFont("Arial", 11)
        self.font_chat = pygame.font.SysFont("Arial", 13)
        self.font_small = pygame.font.SysFont("Arial", 11)

        # Estado del grupo activo
        self.community_id = "night_raid"
        self.current_channel = "general"
        self.connected_voice: Optional[str] = None
        self.anim_time = 0.0

        # Historial de chat por canal
        self.channel_chats: Dict[str, List[Dict[str, Any]]] = {
            "general": [
                {"author": "ALEX", "badge": "👑", "avatar": "avatar_alex.png", "color": (245, 200, 70), "time": "Hoy 18:24", "text": "¿Alguien para unas partidas esta noche? 🎮"},
                {"author": "MIRA", "badge": "", "avatar": "avatar_mira.png", "color": (210, 170, 240), "time": "Hoy 18:26", "text": "¡Yo me sumo! Estuve probando el nuevo mapa."},
                {"author": "KAI", "badge": "", "avatar": "avatar_guy_glasses.png", "color": (120, 185, 255), "time": "Hoy 18:27", "text": "También me copo, armamos sala en la de Gaming?"},
                {"author": "ALEX", "badge": "👑", "avatar": "avatar_alex.png", "color": (245, 200, 70), "time": "Hoy 18:28", "text": "Dale, en 10 min la creo. 👌"},
                {"author": "MIRA", "badge": "", "avatar": "avatar_mira.png", "color": (210, 170, 240), "time": "Hoy 18:35", "text": "Les dejo el skin que conseguí hoy 👀", "has_weapon": True},
                {"author": "KAI", "badge": "", "avatar": "avatar_guy_glasses.png", "color": (120, 185, 255), "time": "Hoy 18:40", "text": "Está increíble 🔥"},
            ],
            "off-topic": [
                {"author": "LUNA", "badge": "", "avatar": "avatar_girl_hoodie.png", "color": (160, 220, 160), "time": "Hoy 15:10", "text": "¿Vieron el nuevo tráiler de anime retro?"},
                {"author": "ALEX", "badge": "👑", "avatar": "avatar_alex.png", "color": (245, 200, 70), "time": "Hoy 15:14", "text": "Sí, la animación en pixel art quedó tremenda."},
            ],
            "clips-y-memes": [
                {"author": "ZERO", "badge": "", "avatar": "avatar_guy_blonde.png", "color": (255, 140, 140), "time": "Hoy 14:02", "text": "Clip del combo de 99 hits en Da Vinci Fighters!"},
            ],
        }

        # Reacciones interactivas para la tarjeta de arma
        self.weapon_reactions = {"❤️": 8, "👍": 3, "✨": 1}

        # Desplazamiento de chat
        self.scroll_y = 0

        # Entrada de texto interactiva
        self.input_text = ""
        self.input_rect = pygame.Rect(495, 622, 480, 36)
        self.btn_send_rect = pygame.Rect(1005, 622, 34, 36)

        # Selector lateral de comunidades (columna estrecha x: 180 a 230)
        self.server_switch_rects = [
            (pygame.Rect(185, 145 + i * 52, 44, 44), comm["id"])
            for i, comm in enumerate(COMMUNITIES_CATALOG)
        ]
        self.btn_back_hub = pygame.Rect(185, 96, 44, 42)

        # Botones de barra lateral izquierda principal
        self.sidebar_buttons = [
            ("INICIO", "MENU", pygame.Rect(40, 125, 140, 36)),
            ("JUEGOS", "LIBRARY", pygame.Rect(40, 170, 140, 36)),
            ("GRUPOS", "GROUPS", pygame.Rect(40, 215, 140, 36)),
            ("PERFIL", "PROFILE", pygame.Rect(40, 260, 140, 36)),
            ("LOGROS", "ACHIEVEMENTS", pygame.Rect(40, 305, 140, 36)),
            ("CONFIGURACIÓN", "SETTINGS", pygame.Rect(40, 350, 140, 36)),
            ("APAGAR", "QUIT", pygame.Rect(40, 395, 140, 36)),
        ]

    @property
    def chat_messages(self) -> List[Dict[str, Any]]:
        return self.channel_chats.get(self.current_channel, [])

    def enter(self, **kwargs):
        self.anim_time = 0.0
        self.scroll_y = 0
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

    def _send_message(self):
        txt = self.input_text.strip()
        if not txt:
            return
        self.input_text = ""
        msgs = self.channel_chats.setdefault(self.current_channel, [])
        msgs.append({
            "author": "ALEX",
            "badge": "👑",
            "avatar": "avatar_alex.png",
            "color": (245, 200, 70),
            "time": time.strftime("Hoy %H:%M"),
            "text": txt,
        })
        self._play_beep(800)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state_machine.change_state("GROUPS")
                    return

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._send_message()
                    return

                if event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    if event.unicode and len(self.input_text) < 140:
                        self.input_text += event.unicode

            elif event.type == pygame.MOUSEWHEEL:
                self.scroll_y = max(0, self.scroll_y - event.y * 25)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = self._screen_to_logical(event.pos)
                if not pos:
                    continue

                # Clic en barra lateral izquierda principal
                if pos[0] < 180:
                    for _label, dest, rect in self.sidebar_buttons:
                        if rect.collidepoint(pos):
                            if dest == "QUIT":
                                pygame.event.post(pygame.event.Event(pygame.QUIT))
                            else:
                                self._play_beep(700)
                                self.state_machine.change_state(dest)
                            return

                # Clic en botón volver al Hub
                if self.btn_back_hub.collidepoint(pos):
                    self.state_machine.change_state("GROUPS")
                    return

                # Clic en selector de comunidad (columna 1)
                for r, cid in self.server_switch_rects:
                    if r.collidepoint(pos):
                        self.community_id = cid
                        self.current_channel = "general"
                        self._play_beep(650)
                        return

                # Clic en canales de texto
                ch_y = 265
                for ch in ["general", "off-topic", "clips-y-memes", "busqueda-de-equipo", "sugerencias"]:
                    r_ch = pygame.Rect(250, ch_y, 185, 26)
                    if r_ch.collidepoint(pos):
                        self.current_channel = ch
                        self._play_beep(600)
                        return
                    ch_y += 30

                # Clic en canales de voz
                v_y = 445
                for v_info in [
                    {"name": "Sala principal"},
                    {"name": "Gaming"},
                    {"name": "Rankeds"},
                    {"name": "Streaming"},
                ]:
                    r_v = pygame.Rect(250, v_y, 185, 26)
                    if r_v.collidepoint(pos):
                        v_name = v_info["name"]
                        if self.connected_voice == v_name:
                            self.connected_voice = None
                        else:
                            self.connected_voice = v_name
                        self._play_beep(750)
                        return
                    v_y += 30

                # Clic en chips de reacciones del arma
                # Rectángulos de reacciones dentro del chat (si estamos en general)
                if self.current_channel == "general":
                    rx = 525
                    for emo in ["❤️", "👍", "✨"]:
                        r_chip = pygame.Rect(rx, 475, 46, 24)
                        if r_chip.collidepoint(pos):
                            self.weapon_reactions[emo] += 1
                            self._play_beep(850)
                            return
                        rx += 52

                # Clic en botón enviar
                if self.btn_send_rect.collidepoint(pos):
                    self._send_message()
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
        # 1. Dibujar chasis de base
        self.canvas.blit(self.base_bg, (0, 0))

        # 2. Resaltar pestaña activa de barra lateral 'GRUPOS'
        pill_rect = pygame.Rect(40, 215, 140, 36)
        pygame.draw.rect(self.canvas, (24, 27, 34), pill_rect, border_radius=6)
        pygame.draw.rect(self.canvas, (255, 255, 255), pygame.Rect(40, 218, 5, 30), border_radius=3)
        txt_grp = self.font_header.render("GRUPOS", True, (255, 255, 255))
        self.canvas.blit(txt_grp, (58, 224))

        # 3. Limpiar zonas dinámicas para que todos los elementos sean reales
        # Selector de comunidad
        pygame.draw.rect(self.canvas, (11, 13, 17), pygame.Rect(180, 95, 55, 530))
        # Columna de canales
        pygame.draw.rect(self.canvas, (14, 16, 21), pygame.Rect(240, 95, 205, 530))
        # Columna central de chat
        pygame.draw.rect(self.canvas, (12, 14, 18), pygame.Rect(450, 95, 595, 575))
        # Columna derecha de miembros
        pygame.draw.rect(self.canvas, (14, 16, 21), pygame.Rect(1050, 95, 220, 530))
        # Diálogo inferior asistente
        pygame.draw.rect(self.canvas, (14, 16, 21), pygame.Rect(210, 635, 540, 55))

        # 4. Renderizar Selector de Comunidades (Columna 1)
        # Botón volver al Hub (arriba)
        pygame.draw.rect(self.canvas, (26, 30, 38), self.btn_back_hub, border_radius=8)
        self.canvas.blit(self.font_header.render("🧭", True, (220, 230, 245)), (self.btn_back_hub.x + 12, self.btn_back_hub.y + 10))

        for r, cid in self.server_switch_rects:
            is_active = (self.community_id == cid)
            bg_c = (35, 42, 55) if is_active else (20, 24, 30)
            pygame.draw.rect(self.canvas, bg_c, r, border_radius=10)
            if is_active:
                pygame.draw.rect(self.canvas, (255, 255, 255), r, width=2, border_radius=10)
                # Indicador blanco vertical a la izquierda
                pygame.draw.rect(self.canvas, (255, 255, 255), pygame.Rect(r.x - 4, r.y + 6, 4, 32), border_radius=2)

            e_icon = self.emblems.get(cid)
            if e_icon:
                self.canvas.blit(pygame.transform.smoothscale(e_icon, (32, 32)), (r.x + 6, r.y + 6))

        # 5. Renderizar Columna de Canales (Columna 2)
        # Cabecera del grupo activo
        cur_comm = next((c for c in COMMUNITIES_CATALOG if c["id"] == self.community_id), COMMUNITIES_CATALOG[0])
        pygame.draw.rect(self.canvas, (18, 21, 28), pygame.Rect(242, 98, 201, 56), border_radius=6)
        e_head = self.emblems.get(cur_comm["id"])
        if e_head:
            self.canvas.blit(pygame.transform.smoothscale(e_head, (36, 36)), (248, 108))
        self.canvas.blit(self.font_header.render(f"{cur_comm['name']} {cur_comm['badge']}", True, (255, 255, 255)), (292, 108))
        self.canvas.blit(self.font_small.render(f"{cur_comm['members']} MIEMBROS", True, (150, 155, 165)), (292, 130))

        # Categoría: INFORMACIÓN
        self.canvas.blit(self.font_cat.render("▾ INFORMACIÓN", True, (130, 135, 145)), (250, 166))
        for ii, info_ch in enumerate(["📢  anuncios", "#  reglas", "⭐  bienvenidas"]):
            self.canvas.blit(self.font_ch.render(info_ch, True, (170, 175, 185)), (255, 188 + ii * 24))

        # Categoría: CHATS DE TEXTO
        self.canvas.blit(self.font_cat.render("▾ CHATS DE TEXTO", True, (130, 135, 145)), (250, 270))
        ch_y = 290
        for ch_key in ["general", "off-topic", "clips-y-memes", "busqueda-de-equipo", "sugerencias"]:
            is_cur = (self.current_channel == ch_key)
            r_ch = pygame.Rect(248, ch_y, 188, 26)
            if is_cur:
                pygame.draw.rect(self.canvas, (32, 38, 52), r_ch, border_radius=6)
                pygame.draw.rect(self.canvas, (90, 105, 130), r_ch, width=1, border_radius=6)
            col = (255, 255, 255) if is_cur else (160, 165, 175)
            font_use = self.font_ch_bold if is_cur else self.font_ch
            self.canvas.blit(font_use.render(f"#  {ch_key}", True, col), (256, ch_y + 4))
            ch_y += 28

        # Categoría: SALAS DE VOZ
        self.canvas.blit(self.font_cat.render("▾ SALAS DE VOZ", True, (130, 135, 145)), (250, 442))
        v_y = 462
        for v_name, count_str in [("Sala principal", "5/16"), ("Gaming", "3/8"), ("Rankeds", "0/5"), ("Streaming", "1/4")]:
            is_conn = (self.connected_voice == v_name)
            r_v = pygame.Rect(248, v_y, 188, 26)
            if is_conn:
                pygame.draw.rect(self.canvas, (24, 48, 32), r_v, border_radius=6)
                pygame.draw.rect(self.canvas, (60, 200, 100), r_v, width=1, border_radius=6)
            col_v = (120, 255, 150) if is_conn else (160, 165, 175)
            self.canvas.blit(self.font_ch.render(f"🔊  {v_name}", True, col_v), (256, v_y + 4))
            self.canvas.blit(self.font_small.render(count_str, True, (120, 125, 135)), (395, v_y + 6))
            v_y += 28

        # Indicador de voz activa
        if self.connected_voice:
            box_v = pygame.Rect(246, 580, 192, 34)
            pygame.draw.rect(self.canvas, (18, 36, 24), box_v, border_radius=6)
            pygame.draw.rect(self.canvas, (40, 190, 80), box_v, width=1, border_radius=6)
            self.canvas.blit(self.font_small.render(f"🟢 En voz: {self.connected_voice}", True, (200, 255, 210)), (254, 588))

        # 6. Renderizar Columna Central de Chat (Columna 3)
        # Cabecera de canal
        header_rect = pygame.Rect(450, 95, 595, 46)
        pygame.draw.rect(self.canvas, (16, 18, 24), header_rect)
        pygame.draw.rect(self.canvas, (45, 50, 62), header_rect, width=1)
        self.canvas.blit(self.font_header.render(f"# {self.current_channel}", True, (255, 255, 255)), (465, 108))
        self.canvas.blit(self.font_small.render("Conversación en tiempo real de la comunidad.", True, (150, 155, 165)), (560, 112))

        # Lista de mensajes del canal
        messages = self.channel_chats.get(self.current_channel, [])
        msg_y = 150 - self.scroll_y
        for m in messages:
            if msg_y > 590:
                break
            if msg_y + 50 >= 140:
                # Avatar
                av_surf = self.avatars.get(m["avatar"])
                if av_surf:
                    self.canvas.blit(pygame.transform.smoothscale(av_surf, (36, 36)), (465, msg_y))

                # Autor y hora
                author_txt = f"{m['author']} {m.get('badge', '')}"
                self.canvas.blit(self.font_author.render(author_txt, True, m.get("color", (255, 255, 255))), (510, msg_y))
                self.canvas.blit(self.font_time.render(m["time"], True, (130, 135, 145)), (600, msg_y + 2))

                # Texto del mensaje
                self.canvas.blit(self.font_chat.render(m["text"], True, (235, 240, 250)), (510, msg_y + 20))

                # Si incluye tarjeta de arma
                if m.get("has_weapon"):
                    self.canvas.blit(self.weapon_card, (510, msg_y + 44))
                    # Chips de reacciones interactivas
                    rx = 525
                    for emo, count in self.weapon_reactions.items():
                        r_chip = pygame.Rect(rx, msg_y + 208, 46, 24)
                        pygame.draw.rect(self.canvas, (28, 34, 46), r_chip, border_radius=4)
                        pygame.draw.rect(self.canvas, (75, 85, 105), r_chip, width=1, border_radius=4)
                        self.canvas.blit(self.font_small.render(f"{emo} {count}", True, (240, 240, 250)), (rx + 6, msg_y + 212))
                        rx += 52
                    msg_y += 240
                else:
                    msg_y += 48
            else:
                msg_y += 48

        # Barra de entrada inferior de chat
        input_bg = pygame.Rect(460, 618, 575, 42)
        pygame.draw.rect(self.canvas, (20, 23, 30), input_bg, border_radius=8)
        pygame.draw.rect(self.canvas, (65, 75, 95), input_bg, width=1, border_radius=8)

        # Botón adjuntar '+'
        pygame.draw.rect(self.canvas, (32, 38, 50), pygame.Rect(468, 624, 28, 28), border_radius=5)
        self.canvas.blit(self.font_header.render("+", True, (220, 225, 235)), (476, 626))

        # Texto de input
        cur_in = self.input_text + ("|" if int(self.anim_time * 2) % 2 == 0 else "")
        show_str = cur_in if cur_in else f"Enviar un mensaje a #{self.current_channel}..."
        show_col = (255, 255, 255) if cur_in else (130, 135, 145)
        self.canvas.blit(self.font_chat.render(show_str, True, show_col), (510, 628))

        # Botón Enviar '>'
        pygame.draw.rect(self.canvas, (45, 55, 75), self.btn_send_rect, border_radius=6)
        self.canvas.blit(self.font_header.render(">", True, (255, 255, 255)), (self.btn_send_rect.x + 10, self.btn_send_rect.y + 6))

        # 7. Renderizar Columna Derecha de Miembros (Columna 4)
        m_y = 108
        self.canvas.blit(self.font_cat.render("▾ EN LÍNEA — 5", True, (130, 135, 145)), (1060, m_y))
        m_y += 24
        online_members = [
            ("ALEX 👑", "avatar_alex.png", "Jugando: Da Vinci Fighters", (60, 220, 100)),
            ("MIRA", "avatar_mira.png", "En llamada Gaming", (60, 220, 100)),
            ("KAI", "avatar_guy_glasses.png", "En línea", (60, 220, 100)),
            ("LUNA", "avatar_girl_hoodie.png", "Jugando: Minecraft", (60, 220, 100)),
            ("ZERO", "avatar_guy_blonde.png", "Transmitiendo 🔴", (180, 80, 240)),
        ]
        for name, av_fn, act, dot_c in online_members:
            av_s = self.avatars.get(av_fn)
            if av_s:
                self.canvas.blit(pygame.transform.smoothscale(av_s, (30, 30)), (1062, m_y))
            pygame.draw.circle(self.canvas, dot_c, (1090, m_y + 26), 4)
            self.canvas.blit(self.font_ch_bold.render(name, True, (245, 245, 250)), (1100, m_y))
            self.canvas.blit(self.font_small.render(act, True, (140, 145, 155)), (1100, m_y + 16))
            m_y += 38

        m_y += 10
        self.canvas.blit(self.font_cat.render("▾ AUSENTE — 2", True, (130, 135, 145)), (1060, m_y))
        m_y += 24
        for name, act in [("REN", "Ausente"), ("SORA", "AFK")]:
            pygame.draw.circle(self.canvas, (220, 180, 60), (1070, m_y + 10), 4)
            self.canvas.blit(self.font_ch.render(name, True, (180, 185, 195)), (1085, m_y))
            self.canvas.blit(self.font_small.render(act, True, (130, 135, 145)), (1085, m_y + 16))
            m_y += 34

        m_y += 10
        self.canvas.blit(self.font_cat.render("▾ SIN CONEXIÓN — 17", True, (130, 135, 145)), (1060, m_y))

        # 8. Diálogo Asistente inferior
        self.canvas.blit(self.font_small.render(f"Estás en {cur_comm['name']}. Conversa, juega y coordina con la comunidad.", True, (240, 242, 248)), (215, 650))

        # Escalar al tamaño de la pantalla
        sw, sh = screen.get_size()
        scale = min(sw / LOGICAL_W, sh / LOGICAL_H)
        dw, dh = int(LOGICAL_W * scale), int(LOGICAL_H * scale)
        scaled_canvas = pygame.transform.smoothscale(self.canvas, (dw, dh))
        screen.fill((0, 0, 0))
        screen.blit(scaled_canvas, ((sw - dw) // 2, (sh - dh) // 2))
