"""Pantallas modulares de Grupos y Comunidad para C.C.I. System.

Construidas con las 4 bases limpias vacías y los sprites recortados de las hojas
transparentes Photoroom en 'Grupos assets ', manteniendo la barra lateral
compartida (sidebar_ui.py) idéntica en todas las pantallas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame

from sidebar_ui import draw_sidebar, load_sidebar, make_sidebar_font, sidebar_destination
from states import BaseState, SCREEN_HEIGHT, SCREEN_WIDTH


# ---------------------------------------------------------------------------
# Catálogo de comunidades y modelos de datos interactivos
# ---------------------------------------------------------------------------

COMMUNITIES_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "night_raid",
        "group_id": "grp_night_raid",
        "name": "NIGHT RAID",
        "subtitle": "COMUNIDAD DE JUEGOS • 24 MIEMBROS",
        "description": "Comunidad enfocada en juegos competitivos, eventos y proyectos de C.C.I.",
        "privacy": "Grupo privado",
        "members_count": 24,
        "online_count": 5,
        "channels_count": 12,
        "voice_count": 3,
        "is_owner": True,
        "card_sprite": "card_0_night_raid.png",
        "banner_idx": 0,
        "emblem_idx": 0,
        "recent_rank": 0,
    },
    {
        "id": "sakura_club",
        "group_id": "grp_sakura_club",
        "name": "SAKURA CLUB",
        "subtitle": "ARTE Y CULTURA • 18 MIEMBROS",
        "description": "Espacio de ilustración pixel art, estética japonesa, música lo-fi y charlas.",
        "privacy": "Grupo público",
        "members_count": 18,
        "online_count": 3,
        "channels_count": 8,
        "voice_count": 2,
        "is_owner": False,
        "card_sprite": "card_1_sakura_club.png",
        "banner_idx": 1,
        "emblem_idx": 1,
        "recent_rank": 1,
    },
    {
        "id": "da_vinci_team",
        "group_id": "grp_davinci_team",
        "name": "DA VINCI TEAM",
        "subtitle": "DESARROLLO C.C.I. • 12 MIEMBROS",
        "description": "Equipo de desarrollo de videojuegos indie, motores gráficos y torneos.",
        "privacy": "Grupo privado",
        "members_count": 12,
        "online_count": 2,
        "channels_count": 10,
        "voice_count": 2,
        "is_owner": True,
        "card_sprite": "card_2_davinci_team.png",
        "banner_idx": 2,
        "emblem_idx": 2,
        "recent_rank": 2,
    },
    {
        "id": "pixel_squad",
        "group_id": "grp_pixel_squad",
        "name": "PIXEL SQUAD",
        "subtitle": "ARCADE & RETRO • 30 MIEMBROS",
        "description": "Comunidad de speedruns, retos semanales de arcade y récords cooperativos.",
        "privacy": "Grupo público",
        "members_count": 30,
        "online_count": 9,
        "channels_count": 14,
        "voice_count": 4,
        "is_owner": False,
        "card_sprite": "card_3_pixel_squad.png",
        "banner_idx": 3,
        "emblem_idx": 3,
        "recent_rank": 3,
    },
    {
        "id": "kpop_zone",
        "group_id": "grp_kpop_zone",
        "name": "K-POP ZONE",
        "subtitle": "MÚSICA Y RITMO • 56 MIEMBROS",
        "description": "Eventos de juegos de ritmo, watch parties en vivo y listas colaborativas.",
        "privacy": "Grupo público",
        "members_count": 56,
        "online_count": 14,
        "channels_count": 16,
        "voice_count": 5,
        "is_owner": False,
        "card_sprite": "card_4_kpop_zone.png",
        "banner_idx": 4,
        "emblem_idx": 4,
        "recent_rank": 4,
    },
    {
        "id": "cosmos",
        "group_id": "grp_cosmos",
        "name": "COSMOS",
        "subtitle": "EXPLORACIÓN SCI-FI • 20 MIEMBROS",
        "description": "Simuladores espaciales, lore sci-fi y misiones nocturnas de escuadrón.",
        "privacy": "Grupo privado",
        "members_count": 20,
        "online_count": 4,
        "channels_count": 9,
        "voice_count": 2,
        "is_owner": False,
        "card_sprite": "card_5_cosmos.png",
        "banner_idx": 5,
        "emblem_idx": 5,
        "recent_rank": 5,
    },
]


@dataclass
class DirectChatContact:
    contact_id: str
    name: str
    handle: str
    status: str
    activity: str
    last_message: str
    last_time: str
    unread: int = 0
    contact_sprite: str = ""
    messages: List[Tuple[str, str, str]] = field(default_factory=list)


@dataclass
class GroupInviteItem:
    req_id: str
    group_name: str
    inviter: str
    sprite_name: str


@dataclass
class FriendRequestItem:
    req_id: str
    user_name: str
    sprite_name: str


DEFAULT_DMS: List[DirectChatContact] = [
    DirectChatContact(
        contact_id="dm_tomas",
        name="Tomás",
        handle="@tomas_dev",
        status="En línea",
        activity="Jugando: Da Vinci Fighters",
        last_message="Yo llevo soporte, tranqui.",
        last_time="22:18",
        unread=0,
        contact_sprite="dm_contact_0.png",
        messages=[
            ("Tomás", "22:14", "¿Entrás al torneo de esta noche en Night Raid?"),
            ("ALEX", "22:15", "Sí, ya casi termino de configurar el control."),
            ("Tomás", "22:16", "Joya, nos falta uno para completar el squad."),
            ("ALEX", "22:17", "Ahí le aviso a Mira que estaba conectada."),
            ("Tomás", "22:18", "Yo llevo soporte, tranqui."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_martina",
        name="Martina",
        handle="@marti_px",
        status="En línea",
        activity="En Sakura Club",
        last_message="Te pasé los nuevos sprites del menú.",
        last_time="21:40",
        unread=2,
        contact_sprite="dm_contact_1.png",
        messages=[
            ("Martina", "21:38", "¡Hola Alex! ¿Pudiste ver los bocetos del club?"),
            ("Martina", "21:40", "Te pasé los nuevos sprites del menú."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_kai",
        name="Kai",
        handle="@kai_nr",
        status="En línea",
        activity="En sala de voz: Gaming",
        last_message="Estamos en sala Gaming, sumate.",
        last_time="20:55",
        unread=0,
        contact_sprite="dm_contact_2.png",
        messages=[
            ("Kai", "20:50", "¿Sale partida rápida antes del evento?"),
            ("ALEX", "20:52", "Dame 5 minutos y entro."),
            ("Kai", "20:55", "Estamos en sala Gaming, sumate."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_luna",
        name="Luna",
        handle="@luna_craft",
        status="En línea",
        activity="Jugando: Minecraft",
        last_message="Mirá cómo quedó la base del servidor.",
        last_time="19:12",
        unread=1,
        contact_sprite="dm_contact_3.png",
        messages=[
            ("Luna", "19:12", "Mirá cómo quedó la base del servidor."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_ren",
        name="Ren",
        handle="@ren_arcade",
        status="Ausente",
        activity="Ausente",
        last_message="Mañana intento superar tu récord.",
        last_time="Ayer",
        unread=0,
        contact_sprite="dm_contact_4.png",
        messages=[
            ("Ren", "Ayer", "Mañana intento superar tu récord."),
        ],
    ),
    DirectChatContact(
        contact_id="dm_sofia",
        name="Sofía",
        handle="@sofi_kpop",
        status="Sin conexión",
        activity="Desconectada",
        last_message="¡Gracias por la invitación al grupo!",
        last_time="Lun",
        unread=0,
        contact_sprite="dm_contact_5.png",
        messages=[
            ("Sofía", "Lun", "¡Gracias por la invitación al grupo!"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Caché de bases limpias y sprites Photoroom recortados
# ---------------------------------------------------------------------------

class GruposSpritePack:
    """Carga las 4 bases limpias y todos los sprites transparentes de assets/grupos_sprites."""

    def __init__(self) -> None:
        self.loaded = False
        self.sprites: Dict[str, pygame.Surface] = {}
        self.bases: Dict[str, pygame.Surface] = {}
        self.fonts: Dict[str, pygame.font.Font] = {}

    def ensure_loaded(self) -> None:
        if self.loaded:
            return
        if not pygame.font.get_init():
            pygame.font.init()

        for key, size, bold in [
            ("title", 20, True),
            ("subtitle", 13, False),
            ("tab", 13, True),
            ("card_title", 14, True),
            ("card_sub", 12, False),
            ("body", 13, False),
            ("body_bold", 13, True),
            ("small", 11, False),
            ("small_bold", 11, True),
        ]:
            try:
                self.fonts[key] = pygame.font.SysFont("Arial", size, bold=bold)
            except Exception:
                self.fonts[key] = pygame.font.Font(None, size + 2)

        folder = Path(__file__).resolve().parent / "assets" / "grupos_sprites"
        if folder.exists():
            for png in folder.glob("*.png"):
                try:
                    surf = pygame.image.load(str(png))
                    if png.name.startswith("base_"):
                        surf = surf.convert() if pygame.display.get_surface() else surf
                        self.bases[png.name] = surf
                    else:
                        surf = surf.convert_alpha() if pygame.display.get_surface() else surf
                        self.sprites[png.name] = surf
                except Exception as exc:
                    print(f"[CCI] Error cargando sprite {png.name}: {exc}")

        self.loaded = True


_PACK = GruposSpritePack()


def _wrap_lines(text: str, font: pygame.font.Font, max_w: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        cand = f"{cur} {w}"
        if font.size(cand)[0] <= max_w:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _draw_cut_rect(
    surf: pygame.Surface,
    rect: pygame.Rect,
    bg_color: Tuple[int, int, int],
    border_color: Tuple[int, int, int],
    cut: int = 7,
    border_w: int = 1,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    pts = [
        (x + cut, y),
        (x + w - cut, y),
        (x + w, y + cut),
        (x + w, y + h - cut),
        (x + w - cut, y + h),
        (x + cut, y + h),
        (x, y + h - cut),
        (x, y + cut),
    ]
    pygame.draw.polygon(surf, bg_color, pts)
    if border_w > 0:
        pygame.draw.polygon(surf, border_color, pts, border_w)


# ---------------------------------------------------------------------------
# Pantalla 1: Hub de Grupos y Comunicación ("GROUPS")
# ---------------------------------------------------------------------------

class GroupsHubState(BaseState):
    """Pantalla principal de Grupos con las 3 pestañas reales (Mis Grupos, Chats Privados, Solicitudes)."""

    SORT_MODES = ("Actividad reciente", "Más miembros", "Alfabético")

    def __init__(self, state_machine: Optional[Any] = None) -> None:
        super().__init__(state_machine)
        self.sidebar_surface: Optional[pygame.Surface] = None
        self.sidebar_font: Optional[pygame.font.Font] = None

        # 0 = MIS GRUPOS, 1 = CHATS PRIVADOS, 2 = SOLICITUDES
        self.active_tab: int = 0
        self.selected_index: int = 0
        self.view_mode: str = "grid"  # "grid" | "list"
        self.sort_idx: int = 0

        self.search_query: str = ""
        self.search_focused: bool = False

        self.groups: List[Dict[str, Any]] = [dict(g) for g in COMMUNITIES_CATALOG]
        self.dms: List[DirectChatContact] = [
            DirectChatContact(
                contact_id=d.contact_id,
                name=d.name,
                handle=d.handle,
                status=d.status,
                activity=d.activity,
                last_message=d.last_message,
                last_time=d.last_time,
                unread=d.unread,
                contact_sprite=d.contact_sprite,
                messages=list(d.messages),
            )
            for d in DEFAULT_DMS
        ]

        self.group_invites: List[GroupInviteItem] = [
            GroupInviteItem("inv_0", "NIGHT RAID", "Kai", "sol_group_0.png"),
            GroupInviteItem("inv_1", "SAKURA CLUB", "Martina", "sol_group_1.png"),
            GroupInviteItem("inv_2", "PIXEL SQUAD", "Ren", "sol_group_2.png"),
        ]
        self.friend_requests: List[FriendRequestItem] = [
            FriendRequestItem("fr_0", "Luca", "sol_friend_0.png"),
            FriendRequestItem("fr_1", "Sofía", "sol_friend_1.png"),
        ]
        self.sent_invites: List[FriendRequestItem] = [
            FriendRequestItem("sent_0", "Tomás", "sol_sent_0.png"),
        ]

        self.dm_input_text: str = ""
        self.dm_input_focused: bool = False

        self.modal_mode: Optional[str] = None  # None | "create" | "join"
        self.modal_input: str = ""
        self.status_banner: str = ""

        # Rects interactivos en 1280x720 (alineados a las 3 bases limpias)
        self.tab_rects = [
            pygame.Rect(243, 145, 134, 34),  # MIS GRUPOS
            pygame.Rect(386, 145, 152, 34),  # CHATS PRIVADOS
            pygame.Rect(546, 145, 146, 34),  # SOLICITUDES
        ]
        self.search_rect = pygame.Rect(245, 198, 224, 29)
        self.sort_rect = pygame.Rect(558, 198, 114, 29)
        self.grid_btn_rect = pygame.Rect(682, 198, 28, 29)
        self.list_btn_rect = pygame.Rect(712, 198, 28, 29)
        self.create_btn_rect = pygame.Rect(243, 571, 142, 35)
        self.join_btn_rect = pygame.Rect(395, 571, 149, 35)
        self.enter_group_btn_rect = pygame.Rect(928, 527, 319, 35)

        self.card_rects: List[Tuple[pygame.Rect, int]] = []
        self.dm_contact_rects: List[Tuple[pygame.Rect, int]] = []
        self.dm_input_rect = pygame.Rect(610, 552, 644, 46)
        self.sol_action_rects: List[Tuple[pygame.Rect, str, str]] = []

    def enter(self, **kwargs) -> None:
        _PACK.ensure_loaded()
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()
        self.search_focused = False
        self.dm_input_focused = False
        self.modal_mode = None
        if "tab" in kwargs:
            self.active_tab = int(kwargs["tab"]) % 3

    def _change_state(self, dest: str, **kwargs) -> None:
        if self.state_machine is not None:
            self.state_machine.change_state(dest, **kwargs)

    def _filtered_groups(self) -> List[Dict[str, Any]]:
        items = list(self.groups)
        q = self.search_query.strip().lower()
        if q:
            items = [
                g for g in items
                if q in g["name"].lower() or q in g["description"].lower()
            ]
        mode = self.SORT_MODES[self.sort_idx]
        if mode == "Más miembros":
            items.sort(key=lambda g: g["members_count"], reverse=True)
        elif mode == "Alfabético":
            items.sort(key=lambda g: g["name"])
        else:
            items.sort(key=lambda g: g["recent_rank"])
        return items

    def _open_selected_group(self) -> None:
        groups = self._filtered_groups()
        if not groups:
            return
        idx = max(0, min(self.selected_index, len(groups) - 1))
        grp = groups[idx]
        self._change_state("COMMUNITY", community_id=grp["id"])

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if self.modal_mode is not None:
                    self._handle_modal_key(e)
                    continue
                if self.search_focused:
                    if e.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        self.search_focused = False
                    elif e.key == pygame.K_BACKSPACE:
                        self.search_query = self.search_query[:-1]
                        self.selected_index = 0
                    elif e.unicode and e.unicode.isprintable() and len(self.search_query) < 26:
                        self.search_query += e.unicode
                        self.selected_index = 0
                    continue
                if self.dm_input_focused and self.active_tab == 1:
                    if e.key == pygame.K_ESCAPE:
                        self.dm_input_focused = False
                    elif e.key == pygame.K_RETURN:
                        self._send_dm_message()
                    elif e.key == pygame.K_BACKSPACE:
                        self.dm_input_text = self.dm_input_text[:-1]
                    elif e.unicode and e.unicode.isprintable() and len(self.dm_input_text) < 75:
                        self.dm_input_text += e.unicode
                    continue

                if e.key == pygame.K_ESCAPE:
                    self._change_state("MENU")
                elif e.key == pygame.K_TAB:
                    self.active_tab = (self.active_tab + 1) % 3
                    self.selected_index = 0
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.active_tab = e.key - pygame.K_1
                    self.selected_index = 0
                elif self.active_tab == 0:
                    groups = self._filtered_groups()
                    count = len(groups)
                    if count > 0:
                        cols = 2 if self.view_mode == "grid" else 1
                        if e.key in (pygame.K_DOWN, pygame.K_s):
                            self.selected_index = min(count - 1, self.selected_index + cols)
                        elif e.key in (pygame.K_UP, pygame.K_w):
                            self.selected_index = max(0, self.selected_index - cols)
                        elif e.key in (pygame.K_RIGHT, pygame.K_d):
                            self.selected_index = min(count - 1, self.selected_index + 1)
                        elif e.key in (pygame.K_LEFT, pygame.K_a):
                            self.selected_index = max(0, self.selected_index - 1)
                        elif e.key == pygame.K_RETURN:
                            self._open_selected_group()
                elif self.active_tab == 1:
                    if e.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected_index = min(len(self.dms) - 1, self.selected_index + 1)
                        self.dms[self.selected_index].unread = 0
                    elif e.key in (pygame.K_UP, pygame.K_w):
                        self.selected_index = max(0, self.selected_index - 1)
                        self.dms[self.selected_index].unread = 0
                    elif e.key == pygame.K_RETURN:
                        self.dm_input_focused = True

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = self._to_logical_pos(e.pos)
                if self.modal_mode is not None:
                    self._handle_modal_click(pos)
                    continue

                # 1. Sidebar compartida (x < 228)
                dest = sidebar_destination(pos, max_x=228)
                if dest is not None:
                    if dest == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif dest != "GROUPS":
                        self._change_state(dest)
                    continue

                # 2. Pestañas superiores
                hit_tab = False
                for idx, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(pos):
                        self.active_tab = idx
                        self.selected_index = 0
                        self.search_focused = False
                        self.dm_input_focused = False
                        hit_tab = True
                        break
                if hit_tab:
                    continue

                # 3. Interacciones según pestaña activa
                if self.active_tab == 0:
                    self._handle_mis_grupos_click(pos)
                elif self.active_tab == 1:
                    self._handle_chats_privados_click(pos)
                elif self.active_tab == 2:
                    self._handle_solicitudes_click(pos)

    def _to_logical_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        surf = pygame.display.get_surface()
        if surf is None:
            return pos
        sw, sh = surf.get_size()
        if (sw, sh) == (SCREEN_WIDTH, SCREEN_HEIGHT) or sw <= 0 or sh <= 0:
            return pos
        return int(pos[0] * SCREEN_WIDTH / sw), int(pos[1] * SCREEN_HEIGHT / sh)

    def _handle_mis_grupos_click(self, pos: Tuple[int, int]) -> None:
        if self.search_rect.collidepoint(pos):
            self.search_focused = True
            return
        self.search_focused = False

        if self.sort_rect.collidepoint(pos):
            self.sort_idx = (self.sort_idx + 1) % len(self.SORT_MODES)
            self.selected_index = 0
            return

        if self.grid_btn_rect.collidepoint(pos):
            self.view_mode = "grid"
            return

        if self.list_btn_rect.collidepoint(pos):
            self.view_mode = "list"
            return

        if self.create_btn_rect.collidepoint(pos):
            self.modal_mode = "create"
            self.modal_input = ""
            return

        if self.join_btn_rect.collidepoint(pos):
            self.modal_mode = "join"
            self.modal_input = ""
            return

        if self.enter_group_btn_rect.collidepoint(pos):
            self._open_selected_group()
            return

        for rect, idx in self.card_rects:
            if rect.collidepoint(pos):
                if self.selected_index == idx:
                    self._open_selected_group()
                else:
                    self.selected_index = idx
                return

    def _handle_chats_privados_click(self, pos: Tuple[int, int]) -> None:
        if self.dm_input_rect.collidepoint(pos):
            self.dm_input_focused = True
            if pos[0] >= self.dm_input_rect.right - 48 and self.dm_input_text.strip():
                self._send_dm_message()
            return
        self.dm_input_focused = False

        for rect, idx in self.dm_contact_rects:
            if rect.collidepoint(pos):
                self.selected_index = idx
                self.dms[idx].unread = 0
                return

    def _send_dm_message(self) -> None:
        txt = self.dm_input_text.strip()
        if not txt or not self.dms:
            return
        idx = max(0, min(self.selected_index, len(self.dms) - 1))
        dm = self.dms[idx]
        dm.messages.append(("ALEX", "Ahora", txt))
        dm.last_message = txt
        dm.last_time = "Ahora"
        self.dm_input_text = ""

    def _handle_solicitudes_click(self, pos: Tuple[int, int]) -> None:
        for rect, req_id, action in self.sol_action_rects:
            if rect.collidepoint(pos):
                for inv in list(self.group_invites):
                    if inv.req_id == req_id:
                        self.group_invites.remove(inv)
                        self.status_banner = (
                            f"Te uniste a {inv.group_name}"
                            if action == "accept"
                            else f"Invitación a {inv.group_name} rechazada"
                        )
                        return
                for fr in list(self.friend_requests):
                    if fr.req_id == req_id:
                        self.friend_requests.remove(fr)
                        self.status_banner = (
                            f"Ahora sos amigo de {fr.user_name}"
                            if action == "accept"
                            else f"Solicitud de {fr.user_name} rechazada"
                        )
                        return
                for st in list(self.sent_invites):
                    if st.req_id == req_id:
                        self.sent_invites.remove(st)
                        self.status_banner = f"Invitación a {st.user_name} cancelada"
                        return

    def _handle_modal_key(self, e: pygame.event.Event) -> None:
        if e.key == pygame.K_ESCAPE:
            self.modal_mode = None
        elif e.key == pygame.K_RETURN:
            self._confirm_modal()
        elif e.key == pygame.K_BACKSPACE:
            self.modal_input = self.modal_input[:-1]
        elif e.unicode and e.unicode.isprintable() and len(self.modal_input) < 26:
            self.modal_input += e.unicode

    def _handle_modal_click(self, pos: Tuple[int, int]) -> None:
        confirm_rect = pygame.Rect(520, 410, 115, 34)
        cancel_rect = pygame.Rect(645, 410, 115, 34)
        if confirm_rect.collidepoint(pos):
            self._confirm_modal()
        elif cancel_rect.collidepoint(pos):
            self.modal_mode = None

    def _confirm_modal(self) -> None:
        val = self.modal_input.strip()
        if not val:
            self.modal_mode = None
            return
        if self.modal_mode == "create":
            new_grp = {
                "id": f"grp_{len(self.groups) + 1}",
                "group_id": f"grp_{len(self.groups) + 1}",
                "name": val.upper(),
                "subtitle": "NUEVA COMUNIDAD • 1 MIEMBRO",
                "description": "Comunidad creada desde la consola C.C.I. System.",
                "privacy": "Grupo privado",
                "members_count": 1,
                "online_count": 1,
                "channels_count": 4,
                "voice_count": 1,
                "is_owner": True,
                "card_sprite": "card_0_night_raid.png",
                "banner_idx": 0,
                "emblem_idx": 0,
                "recent_rank": -1,
            }
            self.groups.insert(0, new_grp)
            self.selected_index = 0
        elif self.modal_mode == "join":
            new_grp = {
                "id": f"grp_join_{val.lower()}",
                "group_id": f"grp_join_{val.lower()}",
                "name": f"SQUAD {val.upper()[:10]}",
                "subtitle": "CÓDIGO DE INVITACIÓN • 8 MIEMBROS",
                "description": f"Comunidad vinculada mediante código '{val.upper()}'.",
                "privacy": "Grupo privado",
                "members_count": 8,
                "online_count": 3,
                "channels_count": 6,
                "voice_count": 2,
                "is_owner": False,
                "card_sprite": "card_3_pixel_squad.png",
                "banner_idx": 3,
                "emblem_idx": 3,
                "recent_rank": -1,
            }
            self.groups.insert(0, new_grp)
            self.selected_index = 0
        self.modal_mode = None

    def update(self, dt: float) -> None:
        pass

    # -----------------------------------------------------------------------
    # Renderizado por pestaña usando las Bases Limpias + Sprites Photoroom
    # -----------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        _PACK.ensure_loaded()
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # 1. Seleccionar la base limpia correspondiente a la pestaña activa
        base_key = (
            "base_mis_grupos.png"
            if self.active_tab == 0
            else ("base_chats_privados.png" if self.active_tab == 1 else "base_solicitudes.png")
        )
        base_surf = _PACK.bases.get(base_key)
        if base_surf is not None:
            canvas.blit(base_surf, (0, 0))
        else:
            canvas.fill((8, 9, 12))

        # 2. Dibujar los elementos recortados sobre los contenedores vacíos de la base
        if self.active_tab == 0:
            self._draw_tab_mis_grupos(canvas)
        elif self.active_tab == 1:
            self._draw_tab_chats_privados(canvas)
        else:
            self._draw_tab_solicitudes(canvas)

        # 3. Dibujar SIEMPRE la barra lateral compartida idéntica a todas las pantallas
        if self.sidebar_surface is not None and self.sidebar_font is not None:
            draw_sidebar(canvas, self.sidebar_surface, "groups", self.sidebar_font)

        # 4. Modal si está activo
        if self.modal_mode is not None:
            self._draw_modal(canvas)

        if screen.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        else:
            screen.blit(canvas, (0, 0))

    def _draw_tab_mis_grupos(self, surface: pygame.Surface) -> None:
        f_sub = _PACK.fonts["card_sub"]
        f_title = _PACK.fonts["card_title"]
        f_body = _PACK.fonts["body"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        # Si el usuario buscó texto o cambió el orden, actualizar la barra de búsqueda/orden
        if self.search_focused or self.search_query:
            pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(268, 202, 196, 21))
            if self.search_focused:
                pygame.draw.rect(surface, (235, 238, 245), self.search_rect, 1, border_radius=4)
            q_txt = self.search_query + ("|" if self.search_focused else "")
            s_surf = f_sub.render(q_txt or "Buscar grupo...", True, (238, 240, 246))
            surface.blit(s_surf, (270, 205))

        if self.sort_idx != 0:
            pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(562, 202, 106, 21))
            m_surf = f_small.render(f"{self.SORT_MODES[self.sort_idx]} v", True, (220, 224, 232))
            surface.blit(m_surf, (565, 206))

        # Grilla de 6 tarjetas recortadas dentro del contenedor central vacío (x=250..891, y=240..560)
        groups = self._filtered_groups()
        self.card_rects.clear()
        if groups:
            self.selected_index = max(0, min(self.selected_index, len(groups) - 1))

        default_ids = {g["id"] for g in COMMUNITIES_CATALOG}

        if self.view_mode == "grid":
            col_x = [254, 574]
            row_y = [244, 349, 454]
            for i, grp in enumerate(groups[:6]):
                c = i % 2
                r = i // 2
                x, y = col_x[c], row_y[r]
                rect = pygame.Rect(x, y, 310, 98)
                self.card_rects.append((rect, i))

                sp = _PACK.sprites.get(grp["card_sprite"])
                if sp is not None:
                    surface.blit(sp, (x, y))
                else:
                    _draw_cut_rect(surface, rect, (18, 20, 25), (90, 95, 108), cut=6, border_w=1)

                if grp["id"] not in default_ids:
                    pygame.draw.rect(surface, (16, 18, 22), pygame.Rect(x + 56, y + 54, 210, 36))
                    t_s = f_title.render(grp["name"], True, (242, 244, 248))
                    s_s = f_small.render(
                        f"{grp['members_count']} miembros • {grp['online_count']} en línea",
                        True,
                        (175, 180, 190),
                    )
                    surface.blit(t_s, (x + 60, y + 55))
                    surface.blit(s_s, (x + 60, y + 73))

                if i == self.selected_index:
                    pts = [
                        (rect.x + 6, rect.y),
                        (rect.right - 6, rect.y),
                        (rect.right, rect.y + 6),
                        (rect.right, rect.bottom - 6),
                        (rect.right - 6, rect.bottom),
                        (rect.x + 6, rect.bottom),
                        (rect.x, rect.bottom - 6),
                        (rect.x, rect.y + 6),
                    ]
                    pygame.draw.polygon(surface, (245, 247, 252), pts, 2)
        else:
            for i, grp in enumerate(groups[:6]):
                y = 246 + i * 50
                rect = pygame.Rect(256, y, 626, 45)
                self.card_rects.append((rect, i))
                sel = i == self.selected_index
                _draw_cut_rect(
                    surface,
                    rect,
                    (22, 25, 31) if sel else (14, 16, 20),
                    (242, 244, 248) if sel else (75, 80, 92),
                    cut=5,
                    border_w=2 if sel else 1,
                )
                emb = _PACK.sprites.get(f"emblem_{grp['emblem_idx']}.png")
                if emb is not None:
                    emb_sm = pygame.transform.smoothscale(emb, (34, 34))
                    surface.blit(emb_sm, (rect.x + 8, rect.y + 5))
                t_s = f_title.render(grp["name"], True, (244, 246, 250))
                m_s = f_sub.render(
                    f"{grp['members_count']} miembros • {grp['online_count']} en línea   ({grp['privacy']})",
                    True,
                    (175, 180, 190),
                )
                surface.blit(t_s, (rect.x + 52, rect.y + 6))
                surface.blit(m_s, (rect.x + 52, rect.y + 24))

        # Panel derecho de detalle sobre la base limpia (x=913..1262, y=188..588)
        if groups:
            sel_grp = groups[self.selected_index]
            if sel_grp["id"] == "night_raid":
                det_sp = _PACK.sprites.get("detail_night_raid.png")
                if det_sp is not None:
                    surface.blit(det_sp, (921, 185))
            else:
                ban = _PACK.sprites.get(f"banner_{sel_grp['banner_idx']}.png")
                if ban is not None:
                    surface.blit(ban, (925, 188))
                emb = _PACK.sprites.get(f"emblem_{sel_grp['emblem_idx']}.png")
                if emb is not None:
                    surface.blit(emb, (928, 252))

                n_s = _PACK.fonts["title"].render(sel_grp["name"], True, (245, 247, 252))
                surface.blit(n_s, (996, 264))
                p_s = f_sub.render(f"🔒 {sel_grp['privacy']}", True, (175, 180, 190))
                surface.blit(p_s, (996, 288))

                lines = _wrap_lines(sel_grp["description"], f_sub, 316)
                for li, line in enumerate(lines[:2]):
                    l_s = f_sub.render(line, True, (205, 210, 220))
                    surface.blit(l_s, (928, 326 + li * 18))

                stats = [
                    ("Miembros", str(sel_grp["members_count"]), 384),
                    ("En línea", str(sel_grp["online_count"]), 416),
                    ("# Canales", str(sel_grp["channels_count"]), 449),
                    ("Salas de voz", str(sel_grp["voice_count"]), 482),
                ]
                for lbl, val, sy in stats:
                    ls = f_body.render(lbl, True, (205, 210, 220))
                    vs = f_small_b.render(val, True, (244, 246, 250))
                    surface.blit(ls, (946, sy))
                    surface.blit(vs, (1244 - vs.get_width(), sy))

    def _draw_tab_chats_privados(self, surface: pygame.Surface) -> None:
        f_title = _PACK.fonts["card_title"]
        f_body = _PACK.fonts["body"]
        f_small = _PACK.fonts["small"]

        # 1. Lista izquierda de contactos recortados (x=252..576, y=238..600)
        self.dm_contact_rects.clear()
        self.selected_index = max(0, min(self.selected_index, len(self.dms) - 1))

        cur_y = 238
        for i, dm in enumerate(self.dms):
            sp = _PACK.sprites.get(dm.contact_sprite)
            h = sp.get_height() if sp is not None else 56
            rect = pygame.Rect(252, cur_y, 324, h)
            self.dm_contact_rects.append((rect, i))

            if sp is not None:
                surface.blit(sp, (252, cur_y))

            if i == self.selected_index:
                pygame.draw.rect(surface, (242, 244, 248), rect, 2, border_radius=5)

            cur_y += h + 3

        # 2. Panel derecho de conversación (x=606..1256, y=188..604)
        active_dm = self.dms[self.selected_index]

        if active_dm.contact_id == "dm_tomas" and len(active_dm.messages) == 5:
            hdr = _PACK.sprites.get("dm_header_tomas.png")
            msgs = _PACK.sprites.get("dm_messages_tomas.png")
            inp = _PACK.sprites.get("dm_input_bar.png")
            if hdr is not None:
                surface.blit(hdr, (610, 190))
            if msgs is not None:
                surface.blit(msgs, (610, 246))
            if inp is not None:
                surface.blit(inp, (610, 552))
        else:
            hdr = _PACK.sprites.get("dm_header_tomas.png")
            if hdr is not None:
                surface.blit(hdr, (610, 190))
                pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(666, 194, 280, 42))
                n_s = f_title.render(f"{active_dm.name}   {active_dm.handle}", True, (242, 244, 248))
                s_s = f_small.render(f"● {active_dm.status} • {active_dm.activity}", True, (175, 185, 195))
                surface.blit(n_s, (670, 197))
                surface.blit(s_s, (670, 216))

            msg_y = 252
            for sender, ts, text in active_dm.messages[-5:]:
                is_me = sender.upper() == "ALEX"
                bw = min(460, max(190, f_body.size(text)[0] + 36))
                bx = 1236 - bw if is_me else 624
                brect = pygame.Rect(bx, msg_y, bw, 48)
                _draw_cut_rect(
                    surface,
                    brect,
                    (28, 31, 38) if is_me else (18, 20, 25),
                    (150, 156, 170) if is_me else (80, 85, 98),
                    cut=6,
                    border_w=1,
                )
                meta = f_small.render(f"{sender}   {ts}", True, (165, 170, 182))
                body = f_body.render(text, True, (242, 244, 248))
                surface.blit(meta, (brect.x + 12, brect.y + 6))
                surface.blit(body, (brect.x + 12, brect.y + 24))
                msg_y += 56

            inp = _PACK.sprites.get("dm_input_bar.png")
            if inp is not None:
                surface.blit(inp, (610, 552))

        if self.dm_input_focused or self.dm_input_text:
            pygame.draw.rect(surface, (14, 16, 20), pygame.Rect(652, 560, 460, 30))
            if self.dm_input_focused:
                pygame.draw.rect(surface, (238, 240, 248), self.dm_input_rect, 1, border_radius=5)
            txt = self.dm_input_text + ("|" if self.dm_input_focused else "")
            t_s = f_body.render(txt or f"Escribir mensaje a {active_dm.name}...", True, (240, 242, 248))
            surface.blit(t_s, (658, 567))

        # 3. Asistente inferior recortado de la hoja Photoroom
        ast = _PACK.sprites.get("dm_assistant_bar.png")
        if ast is not None:
            surface.blit(ast, (38, 636))

    def _draw_tab_solicitudes(self, surface: pygame.Surface) -> None:
        self.sol_action_rects.clear()

        # 1. Invitaciones a grupos en el contenedor izquierdo (x=256..788, y=246..584)
        gy = 248
        for inv in self.group_invites:
            sp = _PACK.sprites.get(inv.sprite_name)
            if sp is not None:
                surface.blit(sp, (256, gy))
            acc_rect = pygame.Rect(256 + 335, gy + 58, 88, 34)
            rej_rect = pygame.Rect(256 + 430, gy + 58, 92, 34)
            self.sol_action_rects.append((acc_rect, inv.req_id, "accept"))
            self.sol_action_rects.append((rej_rect, inv.req_id, "reject"))
            gy += 110

        # 2. Solicitudes de amistad en el contenedor superior derecho (x=822..1254, y=244..364)
        fy = 246
        for fr in self.friend_requests:
            sp = _PACK.sprites.get(fr.sprite_name)
            if sp is not None:
                surface.blit(sp, (824, fy))
            acc_rect = pygame.Rect(824 + 245, fy + 12, 84, 34)
            rej_rect = pygame.Rect(824 + 334, fy + 12, 88, 34)
            self.sol_action_rects.append((acc_rect, fr.req_id, "accept"))
            self.sol_action_rects.append((rej_rect, fr.req_id, "reject"))
            fy += 60

        # 3. Invitaciones enviadas en el contenedor medio derecho (x=822..1254, y=442..508)
        sy = 444
        for st in self.sent_invites:
            sp = _PACK.sprites.get(st.sprite_name)
            if sp is not None:
                surface.blit(sp, (824, sy))
            can_rect = pygame.Rect(824 + 318, sy + 12, 102, 34)
            self.sol_action_rects.append((can_rect, st.req_id, "cancel"))
            sy += 60

    def _draw_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(440, 260, 400, 200)
        _draw_cut_rect(surface, box, (15, 17, 22), (240, 242, 248), cut=10, border_w=2)

        f_title = _PACK.fonts["title"]
        f_body = _PACK.fonts["body"]
        f_sub = _PACK.fonts["card_sub"]

        header = "CREAR NUEVO GRUPO" if self.modal_mode == "create" else "UNIRSE CON CÓDIGO"
        prompt = "Nombre de la comunidad:" if self.modal_mode == "create" else "Código de invitación:"

        surface.blit(f_title.render(header, True, (244, 246, 250)), (box.x + 24, box.y + 22))
        surface.blit(f_sub.render(prompt, True, (185, 190, 200)), (box.x + 24, box.y + 62))

        inp = pygame.Rect(box.x + 24, box.y + 90, 352, 36)
        _draw_cut_rect(surface, inp, (10, 12, 15), (220, 224, 232), cut=5, border_w=1)
        surface.blit(f_body.render(self.modal_input + "|", True, (244, 246, 250)), (inp.x + 12, inp.y + 9))

        ok_btn = pygame.Rect(520, 410, 115, 34)
        no_btn = pygame.Rect(645, 410, 115, 34)
        _draw_cut_rect(surface, ok_btn, (238, 240, 246), (255, 255, 255), cut=5, border_w=1)
        _draw_cut_rect(surface, no_btn, (22, 25, 32), (130, 135, 148), cut=5, border_w=1)

        surface.blit(_PACK.fonts["tab"].render("Confirmar", True, (12, 14, 18)), (ok_btn.x + 22, ok_btn.y + 9))
        surface.blit(_PACK.fonts["tab"].render("Cancelar", True, (220, 224, 232)), (no_btn.x + 26, no_btn.y + 9))


# ---------------------------------------------------------------------------
# Pantalla 2: Vista Interna de Comunidad ("COMMUNITY" - Night Raid)
# ---------------------------------------------------------------------------

class CommunityViewState(BaseState):
    """Vista interna de servidor/comunidad (Night Raid) construida sobre la Base Limpia 4 + Sprites Photoroom."""

    TEXT_CHANNELS = [
        ("anuncios", "Información y comunicados oficiales."),
        ("reglas", "Normas de convivencia de la comunidad."),
        ("bienvenidas", "Nuevos miembros que se unen al servidor."),
        ("general", "Conversación general de la comunidad."),
        ("off-topic", "Charlas libres, música y otros temas."),
        ("clips-y-memes", "Capturas, jugadas destacadas y humor."),
        ("busqueda-de-equipo", "Coordinación de squads y partidas competitivas."),
        ("sugerencias", "Ideas y mejoras para la comunidad."),
    ]

    VOICE_CHANNELS = [
        ("Sala principal", "5/16"),
        ("Gaming", "3/8"),
        ("Rankeds", "0/5"),
        ("Streaming", "1/4"),
    ]

    DEFAULT_GENERAL_MESSAGES: List[Dict[str, str]] = [
        {"author": "ALEX", "time": "Hoy 18:24", "text": "¿Alguien para unas partidas esta noche? 🎮"},
        {"author": "MIRA", "time": "Hoy 18:26", "text": "¡Yo me sumo! Estuve probando el nuevo mapa."},
        {"author": "KAI", "time": "Hoy 18:27", "text": "También me copo, ¿armamos sala en la de Gaming?"},
        {"author": "ALEX", "time": "Hoy 18:28", "text": "Dale, en 10 min la creo. 👌"},
        {"author": "MIRA", "time": "Hoy 18:35", "text": "Les dejo el skin que conseguí hoy 👀"},
        {"author": "KAI", "time": "Hoy 18:40", "text": "Está increíble 🔥"},
    ]

    def __init__(self, state_machine: Optional[Any] = None) -> None:
        super().__init__(state_machine)
        self.sidebar_surface: Optional[pygame.Surface] = None
        self.sidebar_font: Optional[pygame.font.Font] = None

        self.community_id: str = "night_raid"
        self.active_group_idx: int = 0
        self.current_channel: str = "general"
        self.active_voice: Optional[str] = "Gaming"

        self.reaction_heart: int = 8
        self.reaction_fire: int = 3
        self.user_hearted: bool = False
        self.user_fired: bool = False

        self.chat_messages: List[Dict[str, str]] = [dict(m) for m in self.DEFAULT_GENERAL_MESSAGES]
        self.input_text: str = ""
        self.input_focused: bool = False

        # Rects interactivos sobre la Base Limpia 4 (1280x720)
        self.server_icon_rects: List[Tuple[pygame.Rect, int]] = []
        self.channel_rects: List[Tuple[pygame.Rect, str]] = []
        self.voice_rects: List[Tuple[pygame.Rect, str]] = []
        self.input_rect = pygame.Rect(500, 580, 535, 36)
        self.heart_rect = pygame.Rect(528, 502, 46, 22)
        self.fire_rect = pygame.Rect(578, 502, 46, 22)

    def enter(self, **kwargs) -> None:
        _PACK.ensure_loaded()
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()
        self.input_focused = False

        if "community_id" in kwargs and kwargs["community_id"]:
            self.community_id = str(kwargs["community_id"])
        for i, g in enumerate(COMMUNITIES_CATALOG):
            if g["id"] == self.community_id or g["group_id"] == self.community_id:
                self.active_group_idx = i
                break

        self.current_channel = "general"
        self.chat_messages = [dict(m) for m in self.DEFAULT_GENERAL_MESSAGES]
        self.input_text = ""

    def _change_state(self, dest: str, **kwargs) -> None:
        if self.state_machine is not None:
            self.state_machine.change_state(dest, **kwargs)

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN and self.input_text.strip():
                    self._send_message()
                    continue

                if self.input_focused:
                    if e.key == pygame.K_ESCAPE:
                        self.input_focused = False
                    elif e.key == pygame.K_RETURN:
                        self._send_message()
                    elif e.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif e.unicode and e.unicode.isprintable() and len(self.input_text) < 72:
                        self.input_text += e.unicode
                    continue

                if e.key == pygame.K_ESCAPE:
                    self._change_state("GROUPS")
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    names = [c[0] for c in self.TEXT_CHANNELS]
                    idx = names.index(self.current_channel) if self.current_channel in names else 3
                    self.current_channel = names[(idx + 1) % len(names)]
                elif e.key in (pygame.K_UP, pygame.K_w):
                    names = [c[0] for c in self.TEXT_CHANNELS]
                    idx = names.index(self.current_channel) if self.current_channel in names else 3
                    self.current_channel = names[(idx - 1) % len(names)]
                elif e.key == pygame.K_RETURN:
                    self.input_focused = True

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = self._to_logical_pos(e.pos)

                # 1. Sidebar compartida (x < 170)
                dest = sidebar_destination(pos, max_x=170)
                if dest is not None:
                    if dest == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    else:
                        self._change_state(dest)
                    continue

                # 2. Columna de iconos de comunidades (x = 175..235)
                for rect, idx in self.server_icon_rects:
                    if rect.collidepoint(pos):
                        if idx == -1:
                            self._change_state("GROUPS")
                        else:
                            self.active_group_idx = idx
                            self.community_id = COMMUNITIES_CATALOG[idx]["id"]
                        return

                # 3. Canales de texto (x = 245..440)
                for rect, ch_name in self.channel_rects:
                    if rect.collidepoint(pos):
                        self.current_channel = ch_name
                        return

                # 4. Salas de voz
                for rect, vc_name in self.voice_rects:
                    if rect.collidepoint(pos):
                        self.active_voice = None if self.active_voice == vc_name else vc_name
                        return

                # 5. Reacciones en el mensaje del rifle
                if self.current_channel == "general":
                    if self.heart_rect.collidepoint(pos):
                        self.user_hearted = not self.user_hearted
                        self.reaction_heart += 1 if self.user_hearted else -1
                        return
                    if self.fire_rect.collidepoint(pos):
                        self.user_fired = not self.user_fired
                        self.reaction_fire += 1 if self.user_fired else -1
                        return

                # 6. Barra de entrada de mensaje
                if self.input_rect.collidepoint(pos):
                    self.input_focused = True
                    if pos[0] >= self.input_rect.right - 36 and self.input_text.strip():
                        self._send_message()
                    return
                self.input_focused = False

    def _to_logical_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        surf = pygame.display.get_surface()
        if surf is None:
            return pos
        sw, sh = surf.get_size()
        if (sw, sh) == (SCREEN_WIDTH, SCREEN_HEIGHT) or sw <= 0 or sh <= 0:
            return pos
        return int(pos[0] * SCREEN_WIDTH / sw), int(pos[1] * SCREEN_HEIGHT / sh)

    def _send_message(self) -> None:
        txt = self.input_text.strip()
        if not txt:
            return
        self.chat_messages.append({"author": "ALEX", "time": "Hoy 18:42", "text": txt})
        self.input_text = ""

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        _PACK.ensure_loaded()
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # 1. Pintar la Base Limpia 4 ("Panel de Comunidad Night Raid.png")
        base_surf = _PACK.bases.get("base_community.png")
        if base_surf is not None:
            canvas.blit(base_surf, (0, 0))
        else:
            canvas.fill((8, 9, 12))

        f_title = _PACK.fonts["title"]
        f_sub = _PACK.fonts["card_sub"]
        f_body = _PACK.fonts["body"]
        f_body_b = _PACK.fonts["body_bold"]
        f_small = _PACK.fonts["small"]
        f_small_b = _PACK.fonts["small_bold"]

        grp = COMMUNITIES_CATALOG[self.active_group_idx % len(COMMUNITIES_CATALOG)]

        # 2. Registrar los rects interactivos de la columna de servidores (x=180..232)
        self.server_icon_rects = [
            (pygame.Rect(184, 108, 44, 42), -1),
            (pygame.Rect(180, 160, 52, 54), 0),
            (pygame.Rect(180, 222, 52, 52), 1),
            (pygame.Rect(180, 282, 52, 52), 2),
            (pygame.Rect(180, 342, 52, 52), 3),
            (pygame.Rect(180, 402, 52, 52), 4),
            (pygame.Rect(180, 462, 52, 52), 5),
        ]

        if self.active_group_idx != 0:
            r_sel = self.server_icon_rects[self.active_group_idx + 1][0]
            pygame.draw.rect(canvas, (242, 244, 248), r_sel, 2, border_radius=6)
            pygame.draw.rect(canvas, (12, 14, 18), pygame.Rect(278, 90, 360, 46))
            emb = _PACK.sprites.get(f"emblem_{grp['emblem_idx']}.png")
            if emb is not None:
                canvas.blit(pygame.transform.smoothscale(emb, (42, 42)), (222, 92))
            canvas.blit(f_title.render(grp["name"], True, (245, 247, 252)), (280, 92))
            canvas.blit(f_sub.render(grp["subtitle"], True, (180, 185, 196)), (280, 116))

        # 3. Registrar rects de canales de texto y salas de voz
        self.channel_rects = [
            (pygame.Rect(246, 198, 192, 22), "anuncios"),
            (pygame.Rect(246, 221, 192, 22), "reglas"),
            (pygame.Rect(246, 244, 192, 22), "bienvenidas"),
            (pygame.Rect(246, 297, 192, 26), "general"),
            (pygame.Rect(246, 326, 192, 22), "off-topic"),
            (pygame.Rect(246, 350, 192, 22), "clips-y-memes"),
            (pygame.Rect(246, 374, 192, 22), "busqueda-de-equipo"),
            (pygame.Rect(246, 398, 192, 22), "sugerencias"),
        ]
        self.voice_rects = [
            (pygame.Rect(246, 462, 192, 22), "Sala principal"),
            (pygame.Rect(246, 486, 192, 22), "Gaming"),
            (pygame.Rect(246, 510, 192, 22), "Rankeds"),
            (pygame.Rect(246, 534, 192, 22), "Streaming"),
        ]

        if self.current_channel != "general":
            for rect, ch_name in self.channel_rects:
                if ch_name == self.current_channel:
                    pygame.draw.rect(canvas, (242, 244, 248), rect, 1, border_radius=4)
            pygame.draw.rect(canvas, (14, 16, 20), pygame.Rect(462, 150, 380, 28))
            ch_desc = dict(self.TEXT_CHANNELS).get(self.current_channel, "")
            canvas.blit(f_body_b.render(f"#  {self.current_channel}", True, (245, 247, 252)), (466, 155))
            canvas.blit(f_small.render(ch_desc, True, (175, 180, 192)), (590, 158))

        # 4. Área central de mensajes (x=456..1040, y=186..574)
        extra = self.chat_messages[len(self.DEFAULT_GENERAL_MESSAGES):]

        if self.current_channel == "general" and not extra:
            msg_layout = [
                ("nr_msg_0_alex.png", 464, 194),
                ("nr_msg_1_mira.png", 464, 244),
                ("nr_msg_2_kai.png", 464, 292),
                ("nr_msg_3_alex.png", 464, 340),
                ("nr_msg_4_mira_skin.png", 464, 384),
                ("nr_msg_5_kai.png", 464, 526),
            ]
            for sp_name, mx, my in msg_layout:
                sp = _PACK.sprites.get(sp_name)
                if sp is not None:
                    canvas.blit(sp, (mx, my))

            if self.user_hearted:
                pygame.draw.rect(canvas, (36, 40, 50), self.heart_rect, border_radius=4)
                pygame.draw.rect(canvas, (242, 244, 248), self.heart_rect, 1, border_radius=4)
                canvas.blit(f_small_b.render(f"♥ {self.reaction_heart}", True, (245, 247, 252)), (self.heart_rect.x + 10, self.heart_rect.y + 4))
            if self.user_fired:
                pygame.draw.rect(canvas, (36, 40, 50), self.fire_rect, border_radius=4)
                pygame.draw.rect(canvas, (242, 244, 248), self.fire_rect, 1, border_radius=4)
                canvas.blit(f_small_b.render(f"🔥 {self.reaction_fire}", True, (245, 247, 252)), (self.fire_rect.x + 10, self.fire_rect.y + 4))
        else:
            cur_y = 194
            if self.current_channel == "general":
                base_msgs = [
                    ("nr_msg_2_kai.png", 48),
                    ("nr_msg_3_alex.png", 42),
                    ("nr_msg_4_mira_skin.png", 140),
                    ("nr_msg_5_kai.png", 48),
                ]
                for sp_name, mh in base_msgs[max(0, len(extra) - 1):]:
                    sp = _PACK.sprites.get(sp_name)
                    if sp is not None and cur_y + mh <= 515:
                        canvas.blit(sp, (464, cur_y))
                        cur_y += mh + 4
            else:
                info_rect = pygame.Rect(468, cur_y, 540, 48)
                _draw_cut_rect(canvas, info_rect, (16, 18, 23), (80, 86, 100), cut=5, border_w=1)
                canvas.blit(f_body_b.render(f"Bienvenido a #{self.current_channel}", True, (242, 244, 248)), (482, cur_y + 7))
                canvas.blit(f_sub.render(dict(self.TEXT_CHANNELS).get(self.current_channel, ""), True, (175, 180, 192)), (482, cur_y + 26))
                cur_y += 58

            for msg in extra[-4:]:
                if cur_y > 530:
                    break
                m_rect = pygame.Rect(468, cur_y, 540, 44)
                _draw_cut_rect(canvas, m_rect, (20, 23, 29), (110, 116, 130), cut=5, border_w=1)
                canvas.blit(f_body_b.render(msg["author"], True, (244, 246, 250)), (482, cur_y + 5))
                canvas.blit(f_small.render(msg["time"], True, (155, 160, 172)), (532, cur_y + 7))
                canvas.blit(f_body.render(msg["text"], True, (232, 235, 242)), (482, cur_y + 23))
                cur_y += 50

        # 5. Barra de entrada de texto inferior (y=578..619)
        if self.input_focused or self.input_text:
            pygame.draw.rect(canvas, (14, 16, 20), pygame.Rect(504, 586, 370, 24))
            if self.input_focused:
                pygame.draw.rect(canvas, (240, 242, 248), pygame.Rect(460, 579, 578, 38), 1, border_radius=5)
            txt = self.input_text + ("|" if self.input_focused else "")
            canvas.blit(f_body.render(txt or f"Enviar un mensaje a #{self.current_channel}...", True, (242, 244, 248)), (508, 590))

        # 6. Columna derecha de miembros recortada de la hoja Photoroom (x=1066..1267)
        mem_on = _PACK.sprites.get("nr_members_online.png")
        mem_aw = _PACK.sprites.get("nr_members_away.png")
        if mem_on is not None:
            canvas.blit(mem_on, (1068, 190))
        if mem_aw is not None:
            canvas.blit(mem_aw, (1068, 444))

        # 7. Dibujar SIEMPRE la barra lateral compartida idéntica a todas las pantallas
        if self.sidebar_surface is not None and self.sidebar_font is not None:
            draw_sidebar(canvas, self.sidebar_surface, "community", self.sidebar_font)

        if screen.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        else:
            screen.blit(canvas, (0, 0))
