"""
user_select_state.py - Pantalla de Selección de Usuario para C.C.I. System.
Permite seleccionar perfil independiente, ver estadísticas (nivel, logros, horas)
y crear nuevos usuarios con avatares circulares cyberpunk.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Callable, List, Optional

import pygame

from cci_rumble import hit_rumble, light_rumble
from cci_users import UserManager
from states import BaseState, SCREEN_HEIGHT, SCREEN_WIDTH

ROOT = Path(__file__).resolve().parent

# Dimensiones lógicas
LOGICAL_W, LOGICAL_H = SCREEN_WIDTH, SCREEN_HEIGHT

CYAN = (0, 229, 255)
CYAN_GLOW = (0, 180, 230)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
DARK_BG = (10, 13, 18)
PANEL_BG = (14, 18, 26, 235)
PANEL_BORDER = (45, 55, 75)
MUTED = (140, 148, 162)
LIGHT = (210, 218, 230)
RED_ACCENT = (255, 75, 75)
GREEN_ACCENT = (50, 220, 130)


class UserSelectState(BaseState):
    """
    Estado de Selección de Usuario C.C.I.
    Se ejecuta tras los videos de bienvenida o al cambiar de usuario desde el perfil.
    """

    def __init__(self, state_machine, on_user_selected: Optional[Callable] = None):
        super().__init__(state_machine)
        self.user_manager = UserManager()
        self.on_user_selected = on_user_selected

        self.background: Optional[pygame.Surface] = None
        self.circular_avatars: List[pygame.Surface] = []
        self.selected_index: int = 0
        self.scroll_x: float = 0.0

        # Modal de creación de usuario
        self.creating_user: bool = False
        self.new_user_name: str = ""
        self.new_user_avatar: int = 0
        self.modal_focus: str = "name"  # 'name', 'avatar', 'confirm', 'cancel'

        # Modal de confirmación de borrado
        self.deleting_user: bool = False
        self.target_delete_uid: str = ""

        self.font_title: Optional[pygame.font.Font] = None
        self.font_name: Optional[pygame.font.Font] = None
        self.font_ui: Optional[pygame.font.Font] = None
        self.font_small: Optional[pygame.font.Font] = None

        self.cursor_timer: float = 0.0
        self.pulse_timer: float = 0.0

        self._load_assets()

    def _load_assets(self):
        # 1. Fondo de bienvenida
        bg_path = ROOT / "Bienvenida al sistema C.C.I.png"
        if bg_path.exists():
            try:
                raw_bg = pygame.image.load(str(bg_path)).convert()
                self.background = pygame.transform.smoothscale(raw_bg, (LOGICAL_W, LOGICAL_H))
            except Exception as exc:
                print(f"[UserSelect] No se pudo cargar fondo: {exc}")

        # 2. Avatares circulares cyberpunk (Row 0 de la plantilla sin fondo)
        sel_path = ROOT / "Selector de personajes ciberpunk en blanco-Photoroom.png"
        if sel_path.exists():
            try:
                sheet = pygame.image.load(str(sel_path)).convert_alpha()
                # 8 avatares circulares en la fila 0
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
                        self.circular_avatars.append(sheet.subsurface(rect).copy())
            except Exception as exc:
                print(f"[UserSelect] Error al recortar avatares circulares: {exc}")

        # Fallback de avatares si fallara la carga
        if not self.circular_avatars:
            for i in range(8):
                surf = pygame.Surface((120, 120), pygame.SRCALPHA)
                pygame.draw.circle(surf, (0, 180, 240), (60, 60), 55, 3)
                self.circular_avatars.append(surf)

        # Fuentes
        try:
            self.font_title = pygame.font.SysFont("Arial", 22, bold=True)
            self.font_name = pygame.font.SysFont("Arial", 18, bold=True)
            self.font_ui = pygame.font.SysFont("Arial", 14, bold=True)
            self.font_small = pygame.font.SysFont("Arial", 12)
        except Exception:
            self.font_title = pygame.font.Font(None, 24)
            self.font_name = pygame.font.Font(None, 20)
            self.font_ui = pygame.font.Font(None, 16)
            self.font_small = pygame.font.Font(None, 14)

    def _play_beep(self, pitch: int = 650):
        try:
            sample_rate = 44100
            duration = 0.04
            samples = int(duration * sample_rate)
            buf = bytearray()
            for i in range(samples):
                val = int(math.sin(2.0 * math.pi * pitch * (i / sample_rate)) * 127 + 128)
                buf.append(max(0, min(255, val)))
            snd = pygame.mixer.Sound(buffer=bytes(buf))
            snd.set_volume(0.3)
            snd.play()
        except Exception:
            pass

    def enter(self):
        self.user_manager.load_users()
        users = self.user_manager.get_users_list()
        # Posicionar cursor en el usuario activo actual
        active_id = self.user_manager.active_user_id
        self.selected_index = 0
        for i, u in enumerate(users):
            if u["id"] == active_id:
                self.selected_index = i
                break
        self.creating_user = False
        self.deleting_user = False
        pygame.key.stop_text_input()

    def exit(self):
        pygame.key.stop_text_input()

    def _get_cards(self):
        cards = self.user_manager.get_users_list()
        cards.append({"id": "__new__", "name": "+ NUEVO", "is_new": True})
        return cards

    def handle_events(self, events):
        cards = self._get_cards()
        total_cards = len(cards)

        for event in events:
            # 1. Modo Modal de Creación
            if self.creating_user:
                if self._handle_create_modal_event(event):
                    return
                continue

            # 2. Modo Modal de Borrado
            if self.deleting_user:
                if self._handle_delete_modal_event(event):
                    return
                continue

            # 3. Navegación en pantalla principal
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_index = (self.selected_index - 1) % total_cards
                    self._play_beep(600)
                    light_rumble()
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_index = (self.selected_index + 1) % total_cards
                    self._play_beep(650)
                    light_rumble()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self._activate_selected_card()
                elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    self._trigger_delete_current()
                elif event.key == pygame.K_ESCAPE:
                    # Si ya hay un usuario activo, ir al menú
                    self._confirm_and_enter_menu()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _activate_selected_card(self):
        cards = self._get_cards()
        if not (0 <= self.selected_index < len(cards)):
            return

        card = cards[self.selected_index]
        if card.get("is_new"):
            self.creating_user = True
            self.new_user_name = ""
            self.new_user_avatar = 0
            self.modal_focus = "name"
            pygame.key.start_text_input()
            self._play_beep(800)
            light_rumble()
        else:
            uid = card["id"]
            self._select_and_launch_user(uid)

    def _select_and_launch_user(self, user_id: str):
        selected_ud = self.user_manager.select_user(user_id)
        if selected_ud and self.on_user_selected:
            self.on_user_selected(selected_ud)
        self._play_beep(900)
        hit_rumble()
        self.state_machine.change_state("MENU")

    def _confirm_and_enter_menu(self):
        ud = self.user_manager.active_user
        if self.on_user_selected:
            self.on_user_selected(ud)
        self.state_machine.change_state("MENU")

    def _trigger_delete_current(self):
        cards = self._get_cards()
        if not (0 <= self.selected_index < len(cards)):
            return
        card = cards[self.selected_index]
        if card.get("is_new"):
            return
        if len(self.user_manager.users) <= 1:
            self._play_beep(300)
            return
        self.target_delete_uid = card["id"]
        self.deleting_user = True
        self._play_beep(450)

    def _handle_create_modal_event(self, event) -> bool:
        if event.type == pygame.TEXTINPUT:
            if self.modal_focus == "name" and len(self.new_user_name) < 12:
                self.new_user_name += event.text
                return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.creating_user = False
                pygame.key.stop_text_input()
                self._play_beep(400)
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.modal_focus == "name" and self.new_user_name:
                    self.new_user_name = self.new_user_name[:-1]
                return True
            elif event.key == pygame.K_TAB:
                # Rotar foco entre nombre y avatar
                self.modal_focus = "avatar" if self.modal_focus == "name" else "name"
                return True
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.modal_focus == "avatar" or self.modal_focus == "name":
                    self.new_user_avatar = (self.new_user_avatar - 1) % len(self.circular_avatars)
                    self._play_beep(600)
                return True
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.modal_focus == "avatar" or self.modal_focus == "name":
                    self.new_user_avatar = (self.new_user_avatar + 1) % len(self.circular_avatars)
                    self._play_beep(650)
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._submit_new_user()
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Clics dentro del modal (360, 160, 560, 400)
            if pygame.Rect(420, 240, 440, 40).collidepoint(mx, my):
                self.modal_focus = "name"
                pygame.key.start_text_input()
            # Clic en avatares
            for i in range(len(self.circular_avatars)):
                ax = 405 + i * 58
                ay = 330
                if pygame.Rect(ax, ay, 52, 52).collidepoint(mx, my):
                    self.new_user_avatar = i
                    self.modal_focus = "avatar"
                    self._play_beep(700)
            # Botón Confirmar
            if pygame.Rect(440, 470, 180, 42).collidepoint(mx, my):
                self._submit_new_user()
            # Botón Cancelar
            if pygame.Rect(660, 470, 180, 42).collidepoint(mx, my):
                self.creating_user = False
                pygame.key.stop_text_input()
            return True
        return False

    def _submit_new_user(self):
        clean_name = self.new_user_name.strip()
        if not clean_name:
            clean_name = f"JUGADOR {len(self.user_manager.users) + 1}"
        new_uid = self.user_manager.create_user(clean_name, avatar=self.new_user_avatar)
        self.creating_user = False
        pygame.key.stop_text_input()
        self._select_and_launch_user(new_uid)

    def _handle_delete_modal_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_y):
                self.user_manager.delete_user(self.target_delete_uid)
                self.deleting_user = False
                self.selected_index = max(0, min(self.selected_index, len(self._get_cards()) - 1))
                self._play_beep(500)
                hit_rumble()
                return True
            elif event.key in (pygame.K_ESCAPE, pygame.K_n):
                self.deleting_user = False
                self._play_beep(400)
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Botón Sí (480, 420, 140, 40)
            if pygame.Rect(480, 420, 140, 40).collidepoint(mx, my):
                self.user_manager.delete_user(self.target_delete_uid)
                self.deleting_user = False
                self.selected_index = max(0, min(self.selected_index, len(self._get_cards()) - 1))
                self._play_beep(500)
                hit_rumble()
                return True
            # Botón No (660, 420, 140, 40)
            if pygame.Rect(660, 420, 140, 40).collidepoint(mx, my):
                self.deleting_user = False
                return True
        return False

    def _handle_click(self, pos):
        mx, my = pos
        cards = self._get_cards()
        card_w, card_h = 190, 280
        gap = 24
        total_w = len(cards) * card_w + (len(cards) - 1) * gap
        start_x = max(180, (LOGICAL_W - total_w) // 2)

        for i, card in enumerate(cards):
            x = start_x + i * (card_w + gap)
            y = 260
            rect = pygame.Rect(x, y, card_w, card_h)
            if rect.collidepoint(mx, my):
                if self.selected_index == i:
                    self._activate_selected_card()
                else:
                    self.selected_index = i
                    self._play_beep(650)
                    light_rumble()
                return

    def update(self, dt: float):
        self.cursor_timer = (self.cursor_timer + dt) % 1.0
        self.pulse_timer += dt * 4.0

    def draw(self, screen: pygame.Surface):
        # 1. Fondo base
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill(DARK_BG)

        # 2. Render de tarjetas de usuarios
        self._draw_user_cards(screen)

        # 3. Barra inferior de atajos / ayuda
        self._draw_footer(screen)

        # 4. Modales
        if self.creating_user:
            self._draw_create_modal(screen)
        elif self.deleting_user:
            self._draw_delete_modal(screen)

    def _draw_user_cards(self, screen: pygame.Surface):
        cards = self._get_cards()
        card_w, card_h = 190, 280
        gap = 24
        total_w = len(cards) * card_w + (len(cards) - 1) * gap
        start_x = max(180, (LOGICAL_W - total_w) // 2)

        pulse = (math.sin(self.pulse_timer) + 1.0) * 0.5  # 0.0 .. 1.0

        for i, card in enumerate(cards):
            x = start_x + i * (card_w + gap)
            y = 260
            is_sel = (i == self.selected_index)
            rect = pygame.Rect(x, y, card_w, card_h)

            # Fondo de la tarjeta con transparencia
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_alpha = 240 if is_sel else 200
            card_surf.fill((16, 21, 30, bg_alpha))

            # Borde exterior
            if is_sel:
                # Borde cian resplandeciente
                glow_val = int(180 + 75 * pulse)
                b_color = (0, glow_val, 255)
                pygame.draw.rect(card_surf, b_color, (0, 0, card_w, card_h), 3, border_radius=12)
                # Decoración esquinas cyberpunk
                corner_len = 16
                pygame.draw.line(card_surf, WHITE, (0, 0), (corner_len, 0), 3)
                pygame.draw.line(card_surf, WHITE, (0, 0), (0, corner_len), 3)
                pygame.draw.line(card_surf, WHITE, (card_w - corner_len, 0), (card_w, 0), 3)
                pygame.draw.line(card_surf, WHITE, (card_w, 0), (card_w, corner_len), 3)
                pygame.draw.line(card_surf, WHITE, (0, card_h), (corner_len, card_h), 3)
                pygame.draw.line(card_surf, WHITE, (0, card_h - corner_len), (0, card_h), 3)
                pygame.draw.line(card_surf, WHITE, (card_w - corner_len, card_h), (card_w, card_h), 3)
                pygame.draw.line(card_surf, WHITE, (card_w, card_h - corner_len), (card_w, card_h), 3)
            else:
                pygame.draw.rect(card_surf, PANEL_BORDER, (0, 0, card_w, card_h), 1, border_radius=12)

            screen.blit(card_surf, (x, y))

            # Contenido de la tarjeta
            if card.get("is_new"):
                # Tarjeta de Agregar Nuevo Usuario
                cx, cy = x + card_w // 2, y + 80
                # Anillo de nuevo usuario
                ring_color = CYAN if is_sel else MUTED
                pygame.draw.circle(screen, ring_color, (cx, cy), 50, 2)
                # Signo más grande
                plus_size = 22
                pygame.draw.line(screen, ring_color, (cx - plus_size, cy), (cx + plus_size, cy), 4)
                pygame.draw.line(screen, ring_color, (cx, cy - plus_size), (cx, cy + plus_size), 4)

                self._draw_centered_text(screen, "NUEVO PERFIL", cx, y + 155, self.font_name, WHITE if is_sel else LIGHT)
                self._draw_centered_text(screen, "Crear usuario", cx, y + 185, self.font_small, MUTED)
                if is_sel:
                    self._draw_centered_text(screen, "[ CREAR + ]", cx, y + 235, self.font_ui, CYAN)
            else:
                # Tarjeta de Usuario existente
                cx = x + card_w // 2
                cy_avatar = y + 78
                av_idx = card["avatar"] % len(self.circular_avatars)
                avatar_surf = self.circular_avatars[av_idx]

                # Escalar avatar a 105x105
                target_size = 105
                scaled_av = pygame.transform.smoothscale(avatar_surf, (target_size, target_size))
                screen.blit(scaled_av, (cx - target_size // 2, cy_avatar - target_size // 2))

                # Anillo cyberpunk circular alrededor del avatar
                ring_r = target_size // 2 + 4
                ring_color = CYAN if is_sel else (70, 85, 110)
                pygame.draw.circle(screen, ring_color, (cx, cy_avatar), ring_r, 2 if not is_sel else 3)
                if is_sel:
                    # Anillo decorativo exterior punteado/fino
                    pygame.draw.circle(screen, (0, int(150 + 100 * pulse), 255), (cx, cy_avatar), ring_r + 4, 1)

                # Nombre de usuario
                name_str = card["name"][:12]
                self._draw_centered_text(screen, name_str, cx, y + 148, self.font_name, WHITE if is_sel else LIGHT)

                # Nivel y Trofeos
                lvl_str = f"NIVEL {card['level']}"
                self._draw_centered_text(screen, lvl_str, cx, y + 175, self.font_ui, CYAN if is_sel else MUTED)

                trophies_str = f"★ {card['trophies']} LOGROS"
                self._draw_centered_text(screen, trophies_str, cx, y + 198, self.font_small, GOLD)

                # Tiempo jugado
                time_str = f"⏱ {card['playtime_str']}"
                self._draw_centered_text(screen, time_str, cx, y + 220, self.font_small, MUTED)

                # Prompt de selección
                if is_sel:
                    action_str = "▶ JUGAR (A)"
                    self._draw_centered_text(screen, action_str, cx, y + 250, self.font_ui, CYAN)

    def _draw_footer(self, screen: pygame.Surface):
        footer_y = 665
        cards = self._get_cards()
        can_delete = len(self.user_manager.users) > 1 and not cards[self.selected_index].get("is_new")

        items = ["← → SELECCIONAR", "ENTER / A CONFIRMAR"]
        if can_delete:
            items.append("SUPR / Y ELIMINAR")
        items.append("ESC SALIR")

        hud_text = "   |   ".join(items)
        self._draw_centered_text(screen, hud_text, LOGICAL_W // 2, footer_y, self.font_ui, MUTED)

    def _draw_create_modal(self, screen: pygame.Surface):
        # Cortina oscura
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))

        # Cuadro modal
        mw, mh = 560, 420
        mx, my = (LOGICAL_W - mw) // 2, (LOGICAL_H - mh) // 2
        modal_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        modal_surf.fill((12, 16, 24, 250))
        pygame.draw.rect(modal_surf, CYAN, (0, 0, mw, mh), 2, border_radius=10)
        screen.blit(modal_surf, (mx, my))

        # Título
        self._draw_centered_text(screen, "CREAR NUEVO PERFIL DE USUARIO", LOGICAL_W // 2, my + 30, self.font_title, CYAN)
        pygame.draw.line(screen, (30, 45, 65), (mx + 30, my + 60), (mx + mw - 30, my + 60), 1)

        # Campo: Nombre
        self._draw_text(screen, "NOMBRE DE USUARIO:", mx + 40, my + 80, self.font_ui, LIGHT)
        input_rect = pygame.Rect(mx + 40, my + 105, mw - 80, 42)
        is_name_focused = (self.modal_focus == "name")
        pygame.draw.rect(screen, (20, 26, 38), input_rect, border_radius=6)
        pygame.draw.rect(screen, CYAN if is_name_focused else PANEL_BORDER, input_rect, 2 if is_name_focused else 1, border_radius=6)

        display_name = self.new_user_name
        if is_name_focused and self.cursor_timer < 0.5:
            display_name += "_"
        self._draw_text(screen, display_name or "Escribe tu nombre...", input_rect.x + 14, input_rect.y + 11, self.font_name, WHITE if self.new_user_name else MUTED)

        # Campo: Selector de Avatar Circular
        self._draw_text(screen, "ELIGE TU AVATAR (8 PERSONAJES CIBERPUNK):", mx + 40, my + 175, self.font_ui, LIGHT)

        # 8 avatares circulares en fila
        av_count = len(self.circular_avatars)
        av_size = 50
        gap = 10
        total_av_w = av_count * av_size + (av_count - 1) * gap
        av_start_x = mx + (mw - total_av_w) // 2
        av_y = my + 205

        for i in range(av_count):
            ax = av_start_x + i * (av_size + gap)
            scaled = pygame.transform.smoothscale(self.circular_avatars[i], (av_size, av_size))
            screen.blit(scaled, (ax, av_y))

            if i == self.new_user_avatar:
                pygame.draw.circle(screen, CYAN, (ax + av_size // 2, av_y + av_size // 2), av_size // 2 + 4, 3)
                pygame.draw.circle(screen, WHITE, (ax + av_size // 2, av_y + av_size // 2), av_size // 2 + 6, 1)
            else:
                pygame.draw.circle(screen, PANEL_BORDER, (ax + av_size // 2, av_y + av_size // 2), av_size // 2 + 3, 1)

        # Botones de Acción
        btn_y = my + 335
        # Confirmar
        btn_confirm = pygame.Rect(mx + 60, btn_y, 200, 44)
        pygame.draw.rect(screen, (15, 60, 45), btn_confirm, border_radius=6)
        pygame.draw.rect(screen, GREEN_ACCENT, btn_confirm, 2, border_radius=6)
        self._draw_centered_text(screen, "✓ CREAR PERFIL", btn_confirm.centerx, btn_confirm.centery, self.font_ui, WHITE)

        # Cancelar
        btn_cancel = pygame.Rect(mx + mw - 260, btn_y, 200, 44)
        pygame.draw.rect(screen, (40, 20, 25), btn_cancel, border_radius=6)
        pygame.draw.rect(screen, RED_ACCENT, btn_cancel, 1, border_radius=6)
        self._draw_centered_text(screen, "✕ CANCELAR (ESC)", btn_cancel.centerx, btn_cancel.centery, self.font_ui, LIGHT)

    def _draw_delete_modal(self, screen: pygame.Surface):
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        mw, mh = 480, 260
        mx, my = (LOGICAL_W - mw) // 2, (LOGICAL_H - mh) // 2
        modal_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        modal_surf.fill((16, 20, 28, 250))
        pygame.draw.rect(modal_surf, RED_ACCENT, (0, 0, mw, mh), 2, border_radius=10)
        screen.blit(modal_surf, (mx, my))

        ud = self.user_manager.users.get(self.target_delete_uid)
        user_name = ud.data.get("player_name", self.target_delete_uid) if ud else self.target_delete_uid

        self._draw_centered_text(screen, "ELIMINAR PERFIL DE USUARIO", LOGICAL_W // 2, my + 35, self.font_title, RED_ACCENT)
        msg1 = f"¿Estás seguro de que deseas eliminar a '{user_name}'?"
        msg2 = "Se perderán permanentemente sus trofeos y avances."
        self._draw_centered_text(screen, msg1, LOGICAL_W // 2, my + 85, self.font_ui, WHITE)
        self._draw_centered_text(screen, msg2, LOGICAL_W // 2, my + 115, self.font_small, MUTED)

        # Botones
        btn_y = my + 175
        # Sí
        b_yes = pygame.Rect(mx + 60, btn_y, 160, 42)
        pygame.draw.rect(screen, (70, 25, 25), b_yes, border_radius=6)
        pygame.draw.rect(screen, RED_ACCENT, b_yes, 2, border_radius=6)
        self._draw_centered_text(screen, "SÍ, ELIMINAR", b_yes.centerx, b_yes.centery, self.font_ui, WHITE)

        # No
        b_no = pygame.Rect(mx + mw - 220, btn_y, 160, 42)
        pygame.draw.rect(screen, (25, 32, 45), b_no, border_radius=6)
        pygame.draw.rect(screen, CYAN, b_no, 1, border_radius=6)
        self._draw_centered_text(screen, "CANCELAR (ESC)", b_no.centerx, b_no.centery, self.font_ui, LIGHT)

    def _draw_text(self, screen: pygame.Surface, text: str, x: int, y: int, font: pygame.font.Font, color):
        render = font.render(text, True, color)
        screen.blit(render, (x, y))

    def _draw_centered_text(self, screen: pygame.Surface, text: str, cx: int, cy: int, font: pygame.font.Font, color):
        render = font.render(text, True, color)
        rect = render.get_rect(center=(cx, cy))
        screen.blit(render, rect)
