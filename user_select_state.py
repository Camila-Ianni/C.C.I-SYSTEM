"""
user_select_state.py - Pantalla de Selección de Usuario para C.C.I. System.
Diseño 1:1 idéntico a la referencia oficial:
- Fondo limpio de bienvenida C.C.I. System sin cajas rectangulares invasivas.
- Avatares circulares grandes (diámetro 174px) con anillo blanco y 4 corchetes de enfoque cibernéticos (┌ ┐ └ ┘) en el usuario seleccionado.
- Nombre centrado y pequeño icono de gamepad debajo de cada usuario.
- Botón circular idéntico para '+ Agregar usuario'.
- Botón 'Apagar consola' en el centro inferior con icono de encendido.
- Indicadores 'ⓧ Seleccionar' y '◯ Atrás' en la esquina inferior derecha.
- Reloj digital en tiempo real e icono de configuración en la esquina superior derecha.
"""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

import pygame

from cci_rumble import hit_rumble, light_rumble
from cci_users import UserManager
from states import BaseState, SCREEN_HEIGHT, SCREEN_WIDTH

ROOT = Path(__file__).resolve().parent

LOGICAL_W, LOGICAL_H = SCREEN_WIDTH, SCREEN_HEIGHT

WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 208, 220)
MUTED_GRAY = (140, 150, 165)
DARK_GRAY = (65, 75, 90)
DARK_CIRCLE_BG = (22, 26, 32)
RED_ACCENT = (255, 75, 75)

AVATAR_RADIUS = 87       # Diámetro 174px
BRACKET_BOX = 96         # Caja 192x192px
BRACKET_ARM = 28
BRACKET_WIDTH = 3
AVATAR_CY = 410
AVATAR_SPACING = 200


def _draw_brackets(surface: pygame.Surface, cx: int, cy: int, box_size: int = BRACKET_BOX, arm_len: int = BRACKET_ARM, width: int = BRACKET_WIDTH, color=WHITE):
    """Dibuja los 4 corchetes esquineros de enfoque cyber (┌ ┐ └ ┘)."""
    # Top-Left
    pygame.draw.line(surface, color, (cx - box_size, cy - box_size), (cx - box_size + arm_len, cy - box_size), width)
    pygame.draw.line(surface, color, (cx - box_size, cy - box_size), (cx - box_size, cy - box_size + arm_len), width)
    # Top-Right
    pygame.draw.line(surface, color, (cx + box_size, cy - box_size), (cx + box_size - arm_len, cy - box_size), width)
    pygame.draw.line(surface, color, (cx + box_size, cy - box_size), (cx + box_size, cy - box_size + arm_len), width)
    # Bottom-Left
    pygame.draw.line(surface, color, (cx - box_size, cy + box_size), (cx - box_size + arm_len, cy + box_size), width)
    pygame.draw.line(surface, color, (cx - box_size, cy + box_size), (cx - box_size, cy + box_size - arm_len), width)
    # Bottom-Right
    pygame.draw.line(surface, color, (cx + box_size, cy + box_size), (cx + box_size - arm_len, cy + box_size), width)
    pygame.draw.line(surface, color, (cx + box_size, cy + box_size), (cx + box_size, cy + box_size - arm_len), width)


def _make_circular_surface(source: pygame.Surface, size: int = 174) -> pygame.Surface:
    """Escala y aplica máscara circular perfecta con antialiasing."""
    scaled = pygame.transform.smoothscale(source, (size, size))
    masked = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(masked, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    masked.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return masked


class UserSelectState(BaseState):
    """Pantalla interactiva de bienvenida y selección de usuario."""

    def __init__(self, state_machine, on_user_selected: Optional[Callable] = None):
        super().__init__(state_machine)
        self.user_manager = UserManager()
        self.on_user_selected = on_user_selected

        self.background: Optional[pygame.Surface] = None
        self.circular_avatars: List[pygame.Surface] = []

        # Iconos de UI
        self.icon_gamepad: Optional[pygame.Surface] = None
        self.icon_power: Optional[pygame.Surface] = None
        self.icon_gear: Optional[pygame.Surface] = None

        # Navegación
        self.selected_index: int = 0
        self.focus_target: str = "avatars"  # 'avatars' o 'power'

        # Modales
        self.creating_user: bool = False
        self.new_user_name: str = ""
        self.new_user_avatar: int = 0
        self.cursor_timer: float = 0.0

        self.deleting_user: bool = False
        self.target_delete_uid: str = ""

        # Fuentes
        self.font_clock: Optional[pygame.font.Font] = None
        self.font_name: Optional[pygame.font.Font] = None
        self.font_small: Optional[pygame.font.Font] = None
        self.font_title: Optional[pygame.font.Font] = None

        self._load_assets()

    def _load_assets(self):
        # 1. Fondo de bienvenida C.C.I.
        bg_path = ROOT / "Bienvenida al sistema C.C.I.png"
        if bg_path.exists():
            try:
                raw_bg = pygame.image.load(str(bg_path)).convert()
                self.background = pygame.transform.smoothscale(raw_bg, (LOGICAL_W, LOGICAL_H))
            except Exception as exc:
                print(f"[UserSelect] Error al cargar fondo: {exc}")

        # 2. Avatares circulares cyberpunk (fila 0 de la plantilla sin fondo)
        sel_path = ROOT / "Selector de personajes ciberpunk en blanco-Photoroom.png"
        if sel_path.exists():
            try:
                sheet = pygame.image.load(str(sel_path)).convert_alpha()
                boxes = [
                    (46, 41, 221, 224),
                    (286, 41, 220, 224),
                    (525, 41, 219, 224),
                    (763, 41, 220, 224),
                    (1001, 41, 220, 224),
                    (1240, 41, 220, 224),
                    (1479, 41, 220, 224),
                    (1718, 41, 220, 224),
                ]
                for x, y, w, h in boxes:
                    rect = pygame.Rect(x, y, w, h).clip(sheet.get_rect())
                    if rect.w and rect.h:
                        crop = sheet.subsurface(rect).copy()
                        self.circular_avatars.append(_make_circular_surface(crop, AVATAR_RADIUS * 2))
            except Exception as exc:
                print(f"[UserSelect] Error cargando avatares: {exc}")

        # Fallback de avatares si faltasen
        if not self.circular_avatars:
            for _ in range(8):
                surf = pygame.Surface((AVATAR_RADIUS * 2, AVATAR_RADIUS * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (80, 95, 115), (AVATAR_RADIUS, AVATAR_RADIUS), AVATAR_RADIUS)
                self.circular_avatars.append(surf)

        # 3. Iconos de interfaz
        ui_dir = ROOT / "assets_ui"
        try:
            gp_p = ui_dir / "icon_gamepad.png"
            if gp_p.exists():
                self.icon_gamepad = pygame.image.load(str(gp_p)).convert_alpha()
            pw_p = ui_dir / "icon_power.png"
            if pw_p.exists():
                self.icon_power = pygame.image.load(str(pw_p)).convert_alpha()
            gr_p = ui_dir / "icon_gear.png"
            if gr_p.exists():
                self.icon_gear = pygame.image.load(str(gr_p)).convert_alpha()
        except Exception as exc:
            print(f"[UserSelect] Error cargando iconos ui: {exc}")

        # 4. Fuentes limpias
        try:
            self.font_clock = pygame.font.SysFont("Arial", 18, bold=True)
            self.font_name = pygame.font.SysFont("Arial", 18, bold=True)
            self.font_small = pygame.font.SysFont("Arial", 14)
            self.font_title = pygame.font.SysFont("Arial", 20, bold=True)
        except Exception:
            self.font_clock = pygame.font.Font(None, 20)
            self.font_name = pygame.font.Font(None, 20)
            self.font_small = pygame.font.Font(None, 16)
            self.font_title = pygame.font.Font(None, 22)

    def _play_beep(self, pitch: int = 650):
        try:
            sample_rate = 44100
            duration = 0.035
            samples = int(duration * sample_rate)
            buf = bytearray()
            for i in range(samples):
                val = int(math.sin(2.0 * math.pi * pitch * (i / sample_rate)) * 127 + 128)
                buf.append(max(0, min(255, val)))
            snd = pygame.mixer.Sound(buffer=bytes(buf))
            snd.set_volume(0.25)
            snd.play()
        except Exception:
            pass

    def enter(self):
        self.user_manager.load_users()
        users = self.user_manager.get_users_list()
        active_id = self.user_manager.active_user_id
        self.selected_index = 0
        for i, u in enumerate(users):
            if u["id"] == active_id:
                self.selected_index = i
                break
        self.focus_target = "avatars"
        self.creating_user = False
        self.deleting_user = False
        pygame.key.stop_text_input()

    def exit(self):
        pygame.key.stop_text_input()

    def _get_items(self):
        items = self.user_manager.get_users_list()
        items.append({"id": "__new__", "name": "Agregar usuario", "is_new": True})
        return items

    def _calculate_centers(self) -> List[tuple[int, int]]:
        """Calcula las posiciones horizontales de los círculos respetando la zona despejada."""
        items = self._get_items()
        count = len(items)

        if count >= 4:
            start_cx = 445
        elif count == 3:
            start_cx = 540
        else:
            start_cx = 540

        centers = []
        for i in range(count):
            cx = start_cx + i * AVATAR_SPACING
            centers.append((cx, AVATAR_CY))
        return centers

    def handle_events(self, events):
        items = self._get_items()
        count = len(items)

        for event in events:
            # 1. Modal Creación
            if self.creating_user:
                if self._handle_create_modal(event):
                    return
                continue

            # 2. Modal Borrado
            if self.deleting_user:
                if self._handle_delete_modal(event):
                    return
                continue

            # 3. Navegación Principal
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    if self.focus_target == "avatars":
                        self.selected_index = (self.selected_index - 1) % count
                        self._play_beep(650)
                        light_rumble()
                    else:
                        self.focus_target = "avatars"
                        self._play_beep(650)
                        light_rumble()

                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.focus_target == "avatars":
                        self.selected_index = (self.selected_index + 1) % count
                        self._play_beep(700)
                        light_rumble()
                    else:
                        self.focus_target = "avatars"
                        self._play_beep(700)
                        light_rumble()

                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    if self.focus_target == "avatars":
                        self.focus_target = "power"
                        self._play_beep(550)
                        light_rumble()

                elif event.key in (pygame.K_UP, pygame.K_w):
                    if self.focus_target == "power":
                        self.focus_target = "avatars"
                        self._play_beep(650)
                        light_rumble()

                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    if self.focus_target == "power":
                        # Apagar consola
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    else:
                        self._activate_selected()

                elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    if self.focus_target == "avatars":
                        self._trigger_delete()

                elif event.key == pygame.K_ESCAPE:
                    # '◯ Atrás' -> si hay usuario activo, entrar al Menú
                    ud = self.user_manager.active_user
                    if self.on_user_selected:
                        self.on_user_selected(ud)
                    self.state_machine.change_state("MENU")

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _activate_selected(self):
        items = self._get_items()
        if not (0 <= self.selected_index < len(items)):
            return
        item = items[self.selected_index]
        if item.get("is_new"):
            self.creating_user = True
            self.new_user_name = ""
            self.new_user_avatar = 0
            pygame.key.start_text_input()
            self._play_beep(800)
            light_rumble()
        else:
            self._select_user(item["id"])

    def _select_user(self, user_id: str):
        selected_ud = self.user_manager.select_user(user_id)
        if selected_ud and self.on_user_selected:
            self.on_user_selected(selected_ud)
        self._play_beep(900)
        hit_rumble()
        self.state_machine.change_state("MENU")

    def _trigger_delete(self):
        items = self._get_items()
        if not (0 <= self.selected_index < len(items)):
            return
        item = items[self.selected_index]
        if item.get("is_new") or len(self.user_manager.users) <= 1:
            return
        self.target_delete_uid = item["id"]
        self.deleting_user = True
        self._play_beep(450)

    def _handle_click(self, pos):
        mx, my = pos
        centers = self._calculate_centers()

        # Clic en avatares o en el '+'
        for i, (cx, cy) in enumerate(centers):
            dist = math.hypot(mx - cx, my - cy)
            if dist <= AVATAR_RADIUS + 10:
                if self.focus_target == "avatars" and self.selected_index == i:
                    self._activate_selected()
                else:
                    self.focus_target = "avatars"
                    self.selected_index = i
                    self._play_beep(650)
                    light_rumble()
                return

        # Clic en Apagar consola (x=640, y=628, r=26)
        if math.hypot(mx - 640, my - 628) <= 32 or pygame.Rect(580, 615, 120, 55).collidepoint(mx, my):
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        # Clic en engranaje de configuración (x=1235, y=24, r=18)
        if math.hypot(mx - 1235, my - 24) <= 22:
            self.state_machine.change_state("SETTINGS")
            return

    def _handle_create_modal(self, event) -> bool:
        if event.type == pygame.TEXTINPUT:
            if len(self.new_user_name) < 14:
                self.new_user_name += event.text
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.creating_user = False
                pygame.key.stop_text_input()
                self._play_beep(400)
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.new_user_name:
                    self.new_user_name = self.new_user_name[:-1]
                return True
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.new_user_avatar = (self.new_user_avatar - 1) % len(self.circular_avatars)
                self._play_beep(600)
                return True
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.new_user_avatar = (self.new_user_avatar + 1) % len(self.circular_avatars)
                self._play_beep(650)
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._submit_create_user()
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Clic en los 8 avatares
            for i in range(len(self.circular_avatars)):
                ax = 415 + i * 58
                ay = 345
                if math.hypot(mx - (ax + 25), my - (ay + 25)) <= 28:
                    self.new_user_avatar = i
                    self._play_beep(700)
                    return True
            # Botón Confirmar
            if pygame.Rect(450, 435, 180, 40).collidepoint(mx, my):
                self._submit_create_user()
                return True
            # Botón Cancelar
            if pygame.Rect(650, 435, 180, 40).collidepoint(mx, my):
                self.creating_user = False
                pygame.key.stop_text_input()
                return True
        return False

    def _submit_create_user(self):
        clean_name = self.new_user_name.strip()
        if not clean_name:
            clean_name = f"JUGADOR {len(self.user_manager.users) + 1}"
        new_uid = self.user_manager.create_user(clean_name, avatar=self.new_user_avatar)
        self.creating_user = False
        pygame.key.stop_text_input()
        self._select_user(new_uid)

    def _handle_delete_modal(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_y):
                self.user_manager.delete_user(self.target_delete_uid)
                self.deleting_user = False
                self.selected_index = max(0, min(self.selected_index, len(self._get_items()) - 1))
                self._play_beep(500)
                hit_rumble()
                return True
            elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                self.deleting_user = False
                self._play_beep(400)
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if pygame.Rect(490, 415, 140, 38).collidepoint(mx, my):
                self.user_manager.delete_user(self.target_delete_uid)
                self.deleting_user = False
                self.selected_index = max(0, min(self.selected_index, len(self._get_items()) - 1))
                self._play_beep(500)
                hit_rumble()
                return True
            if pygame.Rect(650, 415, 140, 38).collidepoint(mx, my):
                self.deleting_user = False
                return True
        return False

    def update(self, dt: float):
        self.cursor_timer = (self.cursor_timer + dt) % 1.0

    def draw(self, screen: pygame.Surface):
        # 1. Fondo limpio de bienvenida C.C.I.
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((10, 12, 16))

        # 2. Reloj digital y engranaje superior derecho
        self._draw_top_bar(screen)

        # 3. Fila de avatares circulares y botón '+'
        self._draw_avatars_row(screen)

        # 4. Botón 'Apagar consola' inferior central
        self._draw_power_button(screen)

        # 5. Prompts de botones inferior derecho ('ⓧ Seleccionar', '◯ Atrás')
        self._draw_prompts(screen)

        # 6. Modales flotantes (si están activos)
        if self.creating_user:
            self._draw_create_modal(screen)
        elif self.deleting_user:
            self._draw_delete_modal(screen)

    def _draw_top_bar(self, screen: pygame.Surface):
        # Hora digital en tiempo real HH:MM
        time_str = datetime.now().strftime("%H:%M")
        t_render = self.font_clock.render(time_str, True, WHITE)
        screen.blit(t_render, (1180, 24))

        # Icono engranaje
        if self.icon_gear:
            scaled_gear = pygame.transform.smoothscale(self.icon_gear, (24, 24))
            screen.blit(scaled_gear, (1235, 22))

    def _draw_avatars_row(self, screen: pygame.Surface):
        centers = self._calculate_centers()
        items = self._get_items()
        r = AVATAR_RADIUS

        for i, (cx, cy) in enumerate(centers):
            item = items[i]
            is_selected = (self.focus_target == "avatars" and self.selected_index == i)

            if item.get("is_new"):
                # ── Botón '+' (Agregar usuario) ──
                # Círculo base oscuro
                pygame.draw.circle(screen, DARK_CIRCLE_BG, (cx, cy), r)

                # Borde circular
                b_color = WHITE if is_selected else DARK_GRAY
                b_width = 3 if is_selected else 2
                pygame.draw.circle(screen, b_color, (cx, cy), r + 1, b_width)

                # Corchetes esquineros de enfoque
                bracket_color = WHITE if is_selected else (55, 65, 78)
                _draw_brackets(screen, cx, cy, box_size=BRACKET_BOX, arm_len=BRACKET_ARM, width=3 if is_selected else 2, color=bracket_color)

                # Cruz '+' centrada
                plus_len = 20
                plus_color = WHITE if is_selected else LIGHT_GRAY
                pygame.draw.line(screen, plus_color, (cx - plus_len, cy), (cx + plus_len, cy), 4)
                pygame.draw.line(screen, plus_color, (cx, cy - plus_len), (cx, cy + plus_len), 4)

                # Rótulo inferior 'Agregar usuario'
                lbl_color = WHITE if is_selected else LIGHT_GRAY
                lbl_render = self.font_small.render("Agregar usuario", True, lbl_color)
                screen.blit(lbl_render, lbl_render.get_rect(center=(cx, cy + 106)))

            else:
                # ── Avatar de Usuario ──
                av_idx = item["avatar"] % len(self.circular_avatars)
                av_surf = self.circular_avatars[av_idx]
                screen.blit(av_surf, (cx - r, cy - r))

                # Borde circular blanco
                ring_color = WHITE if is_selected else (140, 150, 165)
                ring_width = 3 if is_selected else 2
                pygame.draw.circle(screen, ring_color, (cx, cy), r + 1, ring_width)

                # Corchetes de enfoque SOLO en el seleccionado
                if is_selected:
                    _draw_brackets(screen, cx, cy, box_size=BRACKET_BOX, arm_len=BRACKET_ARM, width=3, color=WHITE)

                # Nombre del jugador
                name_str = item["name"]
                name_color = WHITE if is_selected else LIGHT_GRAY
                name_render = self.font_name.render(name_str, True, name_color)
                screen.blit(name_render, name_render.get_rect(center=(cx, cy + 106)))

                # Icono de Gamepad centrado bajo el nombre
                if self.icon_gamepad:
                    gp_w, gp_h = self.icon_gamepad.get_size()
                    gp_x = cx - gp_w // 2
                    gp_y = cy + 125
                    if is_selected:
                        screen.blit(self.icon_gamepad, (gp_x, gp_y))
                    else:
                        tinted = self.icon_gamepad.copy()
                        tinted.set_alpha(175)
                        screen.blit(tinted, (gp_x, gp_y))

    def _draw_power_button(self, screen: pygame.Surface):
        cx, cy = 640, 628
        is_focused = (self.focus_target == "power")

        # Icono power
        if self.icon_power:
            pw_w, pw_h = self.icon_power.get_size()
            screen.blit(self.icon_power, (cx - pw_w // 2, cy - pw_h // 2))
        else:
            r = 16
            circle_color = WHITE if is_focused else (160, 170, 185)
            pygame.draw.circle(screen, circle_color, (cx, cy), r, 2)
            pygame.draw.line(screen, circle_color, (cx, cy - 14), (cx, cy - 4), 2)

        # Rótulo 'Apagar consola'
        lbl_color = WHITE if is_focused else (160, 170, 185)
        render = self.font_small.render("Apagar consola", True, lbl_color)
        screen.blit(render, render.get_rect(center=(cx, cy + 32)))

    def _draw_prompts(self, screen: pygame.Surface):
        base_y = 660

        # Botón ⓧ Seleccionar
        x1 = 1040
        pygame.draw.circle(screen, WHITE, (x1, base_y), 10)
        pygame.draw.line(screen, (10, 12, 16), (x1 - 4, base_y - 4), (x1 + 4, base_y + 4), 2)
        pygame.draw.line(screen, (10, 12, 16), (x1 - 4, base_y + 4), (x1 + 4, base_y - 4), 2)

        t1 = self.font_small.render("Seleccionar", True, WHITE)
        screen.blit(t1, (x1 + 16, base_y - 8))

        # Botón ◯ Atrás
        x2 = 1170
        pygame.draw.circle(screen, WHITE, (x2, base_y), 10, 2)
        t2 = self.font_small.render("Atrás", True, WHITE)
        screen.blit(t2, (x2 + 16, base_y - 8))

    def _draw_create_modal(self, screen: pygame.Surface):
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        mw, mh = 560, 390
        mx, my = (LOGICAL_W - mw) // 2, (LOGICAL_H - mh) // 2
        modal_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        modal_surf.fill((16, 20, 28, 250))
        pygame.draw.rect(modal_surf, WHITE, (0, 0, mw, mh), 2, border_radius=8)
        screen.blit(modal_surf, (mx, my))

        t_render = self.font_title.render("AGREGAR USUARIO", True, WHITE)
        screen.blit(t_render, t_render.get_rect(center=(LOGICAL_W // 2, my + 35)))
        pygame.draw.line(screen, (50, 60, 75), (mx + 30, my + 65), (mx + mw - 30, my + 65), 1)

        lbl_name = self.font_small.render("NOMBRE DE USUARIO:", True, LIGHT_GRAY)
        screen.blit(lbl_name, (mx + 45, my + 85))

        inp_rect = pygame.Rect(mx + 45, my + 110, mw - 90, 40)
        pygame.draw.rect(screen, (24, 30, 42), inp_rect, border_radius=4)
        pygame.draw.rect(screen, WHITE, inp_rect, 1, border_radius=4)

        cur_str = self.new_user_name
        if self.cursor_timer < 0.5:
            cur_str += "_"
        disp = self.font_name.render(cur_str or "Escribe tu nombre...", True, WHITE if self.new_user_name else MUTED_GRAY)
        screen.blit(disp, (inp_rect.x + 12, inp_rect.y + 10))

        lbl_av = self.font_small.render("SELECCIONA TU AVATAR:", True, LIGHT_GRAY)
        screen.blit(lbl_av, (mx + 45, my + 175))

        av_size = 50
        gap = 12
        total_w = 8 * av_size + 7 * gap
        start_x = mx + (mw - total_w) // 2
        av_y = my + 205

        for i in range(len(self.circular_avatars)):
            ax = start_x + i * (av_size + gap)
            scaled = pygame.transform.smoothscale(self.circular_avatars[i], (av_size, av_size))
            screen.blit(scaled, (ax, av_y))

            if i == self.new_user_avatar:
                pygame.draw.circle(screen, WHITE, (ax + av_size // 2, av_y + av_size // 2), av_size // 2 + 3, 3)
                _draw_brackets(screen, ax + av_size // 2, av_y + av_size // 2, box_size=av_size // 2 + 8, arm_len=10, width=2, color=WHITE)
            else:
                pygame.draw.circle(screen, DARK_GRAY, (ax + av_size // 2, av_y + av_size // 2), av_size // 2 + 2, 1)

        btn_y = my + 315
        btn_ok = pygame.Rect(mx + 55, btn_y, 210, 42)
        pygame.draw.rect(screen, (25, 40, 35), btn_ok, border_radius=6)
        pygame.draw.rect(screen, WHITE, btn_ok, 1, border_radius=6)
        ok_txt = self.font_name.render("✓ Confirmar", True, WHITE)
        screen.blit(ok_txt, ok_txt.get_rect(center=btn_ok.center))

        btn_cancel = pygame.Rect(mx + mw - 265, btn_y, 210, 42)
        pygame.draw.rect(screen, (40, 25, 30), btn_cancel, border_radius=6)
        pygame.draw.rect(screen, (180, 100, 110), btn_cancel, 1, border_radius=6)
        cancel_txt = self.font_name.render("✕ Cancelar", True, LIGHT_GRAY)
        screen.blit(cancel_txt, cancel_txt.get_rect(center=btn_cancel.center))

    def _draw_delete_modal(self, screen: pygame.Surface):
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        mw, mh = 480, 240
        mx, my = (LOGICAL_W - mw) // 2, (LOGICAL_H - mh) // 2
        modal_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        modal_surf.fill((16, 20, 28, 250))
        pygame.draw.rect(modal_surf, WHITE, (0, 0, mw, mh), 2, border_radius=8)
        screen.blit(modal_surf, (mx, my))

        ud = self.user_manager.users.get(self.target_delete_uid)
        user_name = ud.data.get("player_name", self.target_delete_uid) if ud else self.target_delete_uid

        t_render = self.font_title.render("ELIMINAR PERFIL", True, WHITE)
        screen.blit(t_render, t_render.get_rect(center=(LOGICAL_W // 2, my + 35)))

        msg = f"¿Eliminar a '{user_name}'?"
        sub = "Se perderán permanentemente sus datos y logros."
        m_render = self.font_name.render(msg, True, LIGHT_GRAY)
        s_render = self.font_small.render(sub, True, MUTED_GRAY)
        screen.blit(m_render, m_render.get_rect(center=(LOGICAL_W // 2, my + 85)))
        screen.blit(s_render, s_render.get_rect(center=(LOGICAL_W // 2, my + 112)))

        btn_y = my + 160
        b_yes = pygame.Rect(mx + 50, btn_y, 170, 40)
        pygame.draw.rect(screen, (60, 25, 30), b_yes, border_radius=6)
        pygame.draw.rect(screen, RED_ACCENT, b_yes, 1, border_radius=6)
        y_txt = self.font_small.render("Sí, eliminar", True, WHITE)
        screen.blit(y_txt, y_txt.get_rect(center=b_yes.center))

        b_no = pygame.Rect(mx + mw - 220, btn_y, 170, 40)
        pygame.draw.rect(screen, (24, 30, 42), b_no, border_radius=6)
        pygame.draw.rect(screen, WHITE, b_no, 1, border_radius=6)
        n_txt = self.font_small.render("Cancelar (ESC)", True, LIGHT_GRAY)
        screen.blit(n_txt, n_txt.get_rect(center=b_no.center))
