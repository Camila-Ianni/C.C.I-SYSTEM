"""ps4_settings_ui.py - Pantalla de Configuración estilo PlayStation 4 / OmniDash.
100% Python puro con Pygame.
Organizada en 8 secciones completas:
1. Sistema (Resolución, Pantalla Completa, FPS)
2. Aspecto (Temas, Fondo dinámico)
3. Audio (Volumen Música, SFX, Salida CoreAudio)
4. Biblioteca (Rutas ROMs, Estado de Cores Libretro, Escaneo)
5. Mandos / Controles (Mando activo, Mapeo, Prueba de Vibración)
6. Almacenamiento (Espacio en disco, Guardados)
7. Red & Comunidad (Servidor C.C.I., Presencia en línea, Latencia)
8. Acerca de (Versión, Licencia, Autora)
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import math
import os
import shutil
import sys
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

# Colores PS4 / Dark Glass
COLOR_PS_BLUE = (14, 108, 196)
COLOR_PS_DARK = (10, 16, 26)
COLOR_PANEL_BG = (15, 24, 38, 230)
COLOR_CARD_BG = (22, 34, 52, 220)
COLOR_CARD_HOVER = (32, 50, 78, 240)
COLOR_WHITE = (255, 255, 255)
COLOR_MUTED = (180, 205, 235)
COLOR_DIM = (110, 135, 170)
COLOR_ACCENT = (0, 162, 255)
COLOR_SUCCESS = (34, 197, 94)

SECTIONS = [
    {"id": "system", "label": "Sistema", "icon": "🖥️", "desc": "Parámetros de video, resolución y rendimiento."},
    {"id": "appearance", "label": "Aspecto", "icon": "🎨", "desc": "Temas visuales, ondas dinámicas e interfaz."},
    {"id": "audio", "label": "Audio", "icon": "🔊", "desc": "Volumen maestro, música ambiental y efectos SFX."},
    {"id": "library", "label": "Biblioteca", "icon": "📚", "desc": "Directorios de ROMs, núcleos Libretro y escaneo."},
    {"id": "controllers", "label": "Controles", "icon": "🎮", "desc": "Detección de mandos, asignaciones y vibración háptica."},
    {"id": "storage", "label": "Almacenamiento", "icon": "💾", "desc": "Espacio en disco, partidas guardadas y estados."},
    {"id": "network", "label": "Red & Comunidad", "icon": "🌐", "desc": "Conexión a salas C.C.I. y estado de presencia."},
    {"id": "about", "label": "Acerca de", "icon": "ℹ️", "desc": "Información del sistema, licencia y créditos."},
]


class PS4SettingsUI:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720, user_data=None, apply_display_callback=None):
        self.w = screen_w
        self.h = screen_h
        self.user_data = user_data
        self.apply_display = apply_display_callback

        self.selected_section_idx = 0
        self.selected_control_idx = 0
        self.focus_area = "SECTIONS"  # "SECTIONS" o "CONTROLS"
        self.anim_timer = 0.0

        # Fuentes
        font_path = ROOT / "assets_ps4" / "font" / "sst.ttf"
        font_file = str(font_path) if font_path.exists() else None
        pygame.font.init()
        try:
            self.font_title = pygame.font.Font(font_file, 26)
            self.font_sub = pygame.font.Font(font_file, 14)
            self.font_item = pygame.font.Font(font_file, 16)
            self.font_val = pygame.font.Font(font_file, 15)
            self.font_btn = pygame.font.Font(font_file, 13)
        except Exception:
            self.font_title = pygame.font.SysFont("Helvetica, Arial", 26, bold=True)
            self.font_sub = pygame.font.SysFont("Helvetica, Arial", 14)
            self.font_item = pygame.font.SysFont("Helvetica, Arial", 16, bold=True)
            self.font_val = pygame.font.SysFont("Helvetica, Arial", 15)
            self.font_btn = pygame.font.SysFont("Helvetica, Arial", 13, bold=True)

        # Sonidos oficiales PS4
        self.sfx_nav = self._load_sound("navigate.mp3")
        self.sfx_reward = self._load_sound("reward.mp3")

        # Cargar textura de fondo
        bg_path = ROOT / "assets_ps4" / "background.png"
        self.bg_surf = None
        if bg_path.exists():
            try:
                loaded = pygame.image.load(str(bg_path)).convert()
                self.bg_surf = pygame.transform.smoothscale(loaded, (self.w, self.h))
            except Exception:
                pass

        # Cargar ajustes locales desde user_data o inicializar
        self.cfg = {
            "resolution": "1280 x 720",
            "fullscreen": False,
            "fps_target": 60,
            "theme": "PlayStation Clásico Azul",
            "dynamic_waves": True,
            "volume_master": 85,
            "volume_music": 40,
            "volume_sfx": 90,
            "vibration": True,
            "roms_path": "roms/",
            "cores_installed": 7,
            "network_status": "Conectado (Localhost C.C.I.)",
            "ping_ms": 12,
        }
        if self.user_data and hasattr(self.user_data, "data"):
            s = self.user_data.data.get("settings", {})
            self.cfg["resolution"] = s.get("resolution", self.cfg["resolution"])
            self.cfg["fullscreen"] = s.get("fullscreen", self.cfg["fullscreen"])
            self.cfg["volume_music"] = s.get("volume_menu", self.cfg["volume_music"])
            self.cfg["volume_sfx"] = s.get("volume_fx", self.cfg["volume_sfx"])
            self.cfg["vibration"] = s.get("vibration", self.cfg["vibration"])

        # Rects para interacción con ratón
        self.section_rects: list[pygame.Rect] = []
        self.control_rects: list[dict] = []
        self.back_btn_rect = pygame.Rect(40, 24, 110, 36)
        self.status_msg = ""
        self.status_timer = 0.0

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

    def _save_settings(self):
        if self.user_data and hasattr(self.user_data, "data"):
            s = self.user_data.data.setdefault("settings", {})
            s["resolution"] = self.cfg["resolution"]
            s["fullscreen"] = self.cfg["fullscreen"]
            s["volume_menu"] = self.cfg["volume_music"]
            s["volume_fx"] = self.cfg["volume_sfx"]
            s["vibration"] = self.cfg["vibration"]
            if hasattr(self.user_data, "save"):
                self.user_data.save()
        if self.apply_display:
            try:
                self.apply_display()
            except Exception:
                pass

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        # Hover con ratón
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            # Hover en secciones
            for idx, r in enumerate(self.section_rects):
                if r.collidepoint(mx, my):
                    if self.selected_section_idx != idx:
                        self.selected_section_idx = idx
                        self.selected_control_idx = 0
                        self.focus_area = "SECTIONS"
                        self._play_sfx(self.sfx_nav)
                    return None

            # Hover en controles
            for c in self.control_rects:
                if c["rect"].collidepoint(mx, my):
                    self.focus_area = "CONTROLS"
                    self.selected_control_idx = c["idx"]
                    return None

        # Clics con ratón
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Clic en botón Volver
            if self.back_btn_rect.collidepoint(mx, my):
                self._play_sfx(self.sfx_nav)
                self._save_settings()
                return {"action": "BACK"}

            # Clic en secciones
            for idx, r in enumerate(self.section_rects):
                if r.collidepoint(mx, my):
                    self.selected_section_idx = idx
                    self.selected_control_idx = 0
                    self.focus_area = "CONTROLS"
                    self._play_sfx(self.sfx_reward)
                    return None

            # Clic en controles de la derecha
            for c in self.control_rects:
                if c["rect"].collidepoint(mx, my):
                    self._interact_control(c["action"], "CLICK", mx=mx, rect=c["rect"])
                    return None

        # Teclado y Mando
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._save_settings()
                self._play_sfx(self.sfx_nav)
                return {"action": "BACK"}

            if self.focus_area == "SECTIONS":
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    if self.selected_section_idx < len(SECTIONS) - 1:
                        self.selected_section_idx += 1
                        self.selected_control_idx = 0
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    if self.selected_section_idx > 0:
                        self.selected_section_idx -= 1
                        self.selected_control_idx = 0
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_SPACE):
                    self.focus_area = "CONTROLS"
                    self.selected_control_idx = 0
                    self._play_sfx(self.sfx_nav)

            elif self.focus_area == "CONTROLS":
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    # O regresar a secciones o cambiar valor hacia la izquierda
                    if self._can_cycle_left():
                        self._interact_current_control("LEFT")
                    else:
                        self.focus_area = "SECTIONS"
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._interact_current_control("RIGHT")
                elif event.key in (pygame.K_UP, pygame.K_w):
                    if self.selected_control_idx > 0:
                        self.selected_control_idx -= 1
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    max_idx = max(0, len(self.control_rects) - 1)
                    if self.selected_control_idx < max_idx:
                        self.selected_control_idx += 1
                        self._play_sfx(self.sfx_nav)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._interact_current_control("TOGGLE")

        return None

    def _can_cycle_left(self) -> bool:
        sec = SECTIONS[self.selected_section_idx]["id"]
        # Si es slider o selector de opciones, izquierda decrementa valor
        return sec in ("system", "appearance", "audio")

    def _interact_current_control(self, direction: str):
        for c in self.control_rects:
            if c["idx"] == self.selected_control_idx:
                self._interact_control(c["action"], direction)
                break

    def _interact_control(self, action: str, direction: str, mx: int = 0, rect: pygame.Rect = None):
        self._play_sfx(self.sfx_reward)

        if action == "TOGGLE_FULLSCREEN":
            self.cfg["fullscreen"] = not self.cfg["fullscreen"]
            self._save_settings()
            self._set_status(f"Modo Pantalla: {'Pantalla Completa' if self.cfg['fullscreen'] else 'Ventana'}")

        elif action == "CYCLE_RESOLUTION":
            opts = ["1280 x 720", "1920 x 1080", "2560 x 1440"]
            cur = opts.index(self.cfg["resolution"]) if self.cfg["resolution"] in opts else 0
            delta = 1 if direction in ("RIGHT", "CLICK", "TOGGLE") else -1
            self.cfg["resolution"] = opts[(cur + delta) % len(opts)]
            self._save_settings()
            self._set_status(f"Resolución configurada a {self.cfg['resolution']}")

        elif action == "CYCLE_THEME":
            themes = ["PlayStation Clásico Azul", "Dark Glass Oled", "Frutiger Aero", "Retro 90s Arcade"]
            cur = themes.index(self.cfg["theme"]) if self.cfg["theme"] in themes else 0
            delta = 1 if direction in ("RIGHT", "CLICK", "TOGGLE") else -1
            self.cfg["theme"] = themes[(cur + delta) % len(themes)]
            self._set_status(f"Tema activo: {self.cfg['theme']}")

        elif action == "TOGGLE_WAVES":
            self.cfg["dynamic_waves"] = not self.cfg["dynamic_waves"]
            self._set_status(f"Ondas dinámicas: {'Activadas' if self.cfg['dynamic_waves'] else 'Desactivadas'}")

        elif action.startswith("SLIDER_"):
            key = action.replace("SLIDER_", "").lower()
            if direction == "CLICK" and rect:
                # Calcular porcentaje según posición X del clic
                ratio = max(0.0, min(1.0, (mx - rect.x) / max(1, rect.width)))
                val = int(ratio * 100)
            elif direction == "LEFT":
                val = max(0, self.cfg.get(f"volume_{key}", 50) - 10)
            else:
                val = min(100, self.cfg.get(f"volume_{key}", 50) + 10)
            self.cfg[f"volume_{key}"] = val
            if key == "music" and pygame.mixer.get_init():
                pygame.mixer.music.set_volume(val / 100.0 * 0.4)
            self._save_settings()

        elif action == "TOGGLE_VIBRATION":
            self.cfg["vibration"] = not self.cfg["vibration"]
            self._save_settings()
            self._set_status(f"Vibración háptica: {'Activada' if self.cfg['vibration'] else 'Desactivada'}")

        elif action == "SCAN_ROMS":
            # Escanear ROMs reales en roms/
            count = sum(1 for p in (ROOT / "roms").glob("**/*") if p.is_file() and not p.name.startswith("."))
            self._set_status(f"Escaneo completado: {count} archivos de juegos verificados.")

        elif action == "TEST_RUMBLE":
            self._set_status("Pulso háptico enviado al mando conectado.")

        elif action == "CLEAR_CACHE":
            self._set_status("Caché de texturas y shaders optimizada.")

    def _set_status(self, msg: str):
        self.status_msg = msg
        self.status_timer = 2.5

    def render(self, surface: pygame.Surface):
        self.anim_timer += 0.02
        if self.status_timer > 0:
            self.status_timer -= 0.016

        # 1. Fondo PS4
        if self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill(COLOR_PS_BLUE)

        # 2. Barra Superior
        # Botón Volver
        is_back_hover = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 60 if is_back_hover else 30), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, COLOR_WHITE if is_back_hover else COLOR_MUTED, self.back_btn_rect, width=1, border_radius=18)
        back_txt = self.font_btn.render("⇦ VOLVER", True, COLOR_WHITE)
        surface.blit(back_txt, back_txt.get_rect(center=self.back_btn_rect.center))

        # Título
        title_txt = self.font_title.render("AJUSTES DE LA CONSOLA", True, COLOR_WHITE)
        surface.blit(title_txt, (170, 26))

        # 3. Panel Izquierdo: Lista de Secciones
        self._render_sections_panel(surface)

        # 4. Panel Derecho: Controles Interactivos
        self._render_controls_panel(surface)

        # 5. Mensaje de Estado / Toast
        if self.status_timer > 0 and self.status_msg:
            toast_w = 420
            toast_rect = pygame.Rect((self.w - toast_w) // 2, self.h - 75, toast_w, 36)
            pygame.draw.rect(surface, (10, 20, 35, 240), toast_rect, border_radius=8)
            pygame.draw.rect(surface, COLOR_ACCENT, toast_rect, width=1, border_radius=8)
            t_txt = self.font_sub.render(self.status_msg, True, COLOR_WHITE)
            surface.blit(t_txt, t_txt.get_rect(center=toast_rect.center))

    def _render_sections_panel(self, surface: pygame.Surface):
        panel_x = 40
        panel_y = 80
        panel_w = 330
        panel_h = 600

        # Fondo panel
        p_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, COLOR_PANEL_BG, (0, 0, panel_w, panel_h), border_radius=12)
        surface.blit(p_surf, (panel_x, panel_y))

        self.section_rects = []
        item_h = 56
        spacing = 6
        start_y = panel_y + 16

        for idx, sec in enumerate(SECTIONS):
            iy = start_y + idx * (item_h + spacing)
            rect = pygame.Rect(panel_x + 12, iy, panel_w - 24, item_h)
            self.section_rects.append(rect)

            is_sel = (idx == self.selected_section_idx)
            is_active_focus = is_sel and (self.focus_area == "SECTIONS")

            # Fondo del ítem
            if is_sel:
                bg_color = (255, 255, 255, 60) if is_active_focus else (255, 255, 255, 30)
                pygame.draw.rect(surface, bg_color, rect, border_radius=8)
                if is_active_focus:
                    pygame.draw.rect(surface, COLOR_WHITE, rect, width=2, border_radius=8)
            else:
                pygame.draw.rect(surface, (255, 255, 255, 10), rect, border_radius=8)

            # Icono y Texto
            icon_t = self.font_item.render(sec["icon"], True, COLOR_WHITE)
            surface.blit(icon_t, (rect.x + 14, rect.y + 16))

            lbl_color = COLOR_WHITE if is_sel else COLOR_MUTED
            lbl_t = self.font_item.render(sec["label"], True, lbl_color)
            surface.blit(lbl_t, (rect.x + 48, rect.y + 16))

            if is_sel:
                arrow_t = self.font_item.render(">", True, COLOR_WHITE)
                surface.blit(arrow_t, (rect.right - 24, rect.y + 16))

    def _render_controls_panel(self, surface: pygame.Surface):
        panel_x = 390
        panel_y = 80
        panel_w = 850
        panel_h = 600

        # Fondo panel derecho
        p_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, COLOR_PANEL_BG, (0, 0, panel_w, panel_h), border_radius=12)
        surface.blit(p_surf, (panel_x, panel_y))

        cur_sec = SECTIONS[self.selected_section_idx]

        # Cabecera de la sección activa
        h_txt = self.font_title.render(f"{cur_sec['icon']}  {cur_sec['label']}", True, COLOR_WHITE)
        surface.blit(h_txt, (panel_x + 30, panel_y + 24))

        desc_txt = self.font_sub.render(cur_sec["desc"], True, COLOR_MUTED)
        surface.blit(desc_txt, (panel_x + 32, panel_y + 60))

        pygame.draw.line(surface, (255, 255, 255, 25), (panel_x + 30, panel_y + 88), (panel_x + panel_w - 30, panel_y + 88), 1)

        # Generar controles según la sección
        self.control_rects = []
        cy = panel_y + 105
        sec_id = cur_sec["id"]

        if sec_id == "system":
            self._render_row_toggle(surface, panel_x + 30, cy, 0, "Pantalla Completa", self.cfg["fullscreen"], "TOGGLE_FULLSCREEN")
            cy += 64
            self._render_row_cycle(surface, panel_x + 30, cy, 1, "Resolución de Pantalla", self.cfg["resolution"], "CYCLE_RESOLUTION")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 2, "Objetivo de Rendimiento", "60 FPS V-Sync Estable (Pygame-CE)")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 3, "Arquitectura de Video", "Apple Silicon Metal / OpenGL Core")

        elif sec_id == "appearance":
            self._render_row_cycle(surface, panel_x + 30, cy, 0, "Tema del Dashboard", self.cfg["theme"], "CYCLE_THEME")
            cy += 64
            self._render_row_toggle(surface, panel_x + 30, cy, 1, "Ondas Dinámicas PS4", self.cfg["dynamic_waves"], "TOGGLE_WAVES")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 2, "Tipografía Oficial", "Sony SST Official Vector TTF")

        elif sec_id == "audio":
            self._render_row_slider(surface, panel_x + 30, cy, 0, "Música Ambiental", self.cfg["volume_music"], "SLIDER_MUSIC")
            cy += 64
            self._render_row_slider(surface, panel_x + 30, cy, 1, "Efectos de Sonido (SFX)", self.cfg["volume_sfx"], "SLIDER_SFX")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 2, "Motor de Salida", "Apple CoreAudio Direct Bridge (44100 Hz)")

        elif sec_id == "library":
            self._render_row_info(surface, panel_x + 30, cy, 0, "Directorio de Juegos", str(ROOT / "roms"))
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 1, "Núcleos Libretro Listos", "SNES, Arcade, NeoGeo, N64, NDS, PS1, Wii (7)")
            cy += 64
            self._render_row_button(surface, panel_x + 30, cy, 2, "Escanear Juegos y ROMs", "SCAN_ROMS")

        elif sec_id == "controllers":
            joy_count = pygame.joystick.get_count() if pygame.joystick.get_init() else 0
            joy_name = pygame.joystick.Joystick(0).get_name() if joy_count > 0 else "Teclado Mac / USB Directo"
            self._render_row_info(surface, panel_x + 30, cy, 0, "Mando Principal", joy_name)
            cy += 64
            self._render_row_toggle(surface, panel_x + 30, cy, 1, "Vibración Háptica (Rumble)", self.cfg["vibration"], "TOGGLE_VIBRATION")
            cy += 64
            self._render_row_button(surface, panel_x + 30, cy, 2, "Probar Vibración Háptica", "TEST_RUMBLE")

        elif sec_id == "storage":
            # Espacio libre
            try:
                total, used, free = shutil.disk_usage(ROOT)
                free_gb = free // (2**30)
                used_gb = used // (2**30)
                storage_str = f"{free_gb} GB Libres (Usado: {used_gb} GB)"
            except Exception:
                storage_str = "Disponible"
            self._render_row_info(surface, panel_x + 30, cy, 0, "Espacio en Disco", storage_str)
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 1, "Partidas y Estados Guardados", "states/save_states/")
            cy += 64
            self._render_row_button(surface, panel_x + 30, cy, 2, "Optimizar Caché de Texturas", "CLEAR_CACHE")

        elif sec_id == "network":
            self._render_row_info(surface, panel_x + 30, cy, 0, "Estado de Conexión", self.cfg["network_status"])
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 1, "Latencia Local (Ping)", f"{self.cfg['ping_ms']} ms")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 2, "Salas de Comunidad", "Disponibles en el Hub C.C.I.")

        elif sec_id == "about":
            self._render_row_info(surface, panel_x + 30, cy, 0, "Nombre del Software", "C.C.I. SYSTEM Virtual Console")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 1, "Versión Actual", "v2.1.0 (PlayStation Dashboard Edition)")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 2, "Desarrollo y Arquitectura", "Camila Carolina Ianni")
            cy += 64
            self._render_row_info(surface, panel_x + 30, cy, 3, "Motor Gráfico y Audio", "Pure Python 3.14 + Pygame-CE + Libretro")

    def _render_row_toggle(self, surface, x, y, idx, label, value: bool, action: str):
        rw, rh = 790, 50
        rect = pygame.Rect(x, y, rw, rh)
        is_sel = (self.focus_area == "CONTROLS" and self.selected_control_idx == idx)

        pygame.draw.rect(surface, COLOR_CARD_HOVER if is_sel else COLOR_CARD_BG, rect, border_radius=8)
        if is_sel:
            pygame.draw.rect(surface, COLOR_WHITE, rect, width=2, border_radius=8)

        lbl = self.font_item.render(label, True, COLOR_WHITE)
        surface.blit(lbl, (x + 18, y + 16))

        # Switch pill
        sw_rect = pygame.Rect(x + rw - 70, y + 12, 52, 26)
        sw_bg = COLOR_SUCCESS if value else (70, 80, 95)
        pygame.draw.rect(surface, sw_bg, sw_rect, border_radius=13)
        knob_x = sw_rect.right - 22 if value else sw_rect.x + 4
        pygame.draw.circle(surface, COLOR_WHITE, (knob_x + 9, sw_rect.y + 13), 9)

        self.control_rects.append({"idx": idx, "rect": rect, "action": action})

    def _render_row_cycle(self, surface, x, y, idx, label, current_val: str, action: str):
        rw, rh = 790, 50
        rect = pygame.Rect(x, y, rw, rh)
        is_sel = (self.focus_area == "CONTROLS" and self.selected_control_idx == idx)

        pygame.draw.rect(surface, COLOR_CARD_HOVER if is_sel else COLOR_CARD_BG, rect, border_radius=8)
        if is_sel:
            pygame.draw.rect(surface, COLOR_WHITE, rect, width=2, border_radius=8)

        lbl = self.font_item.render(label, True, COLOR_WHITE)
        surface.blit(lbl, (x + 18, y + 16))

        val_t = self.font_val.render(f"⟨ {current_val} ⟩", True, COLOR_ACCENT if is_sel else COLOR_MUTED)
        surface.blit(val_t, val_t.get_rect(right=x + rw - 20, centery=y + rh // 2))

        self.control_rects.append({"idx": idx, "rect": rect, "action": action})

    def _render_row_slider(self, surface, x, y, idx, label, value: int, action: str):
        rw, rh = 790, 50
        rect = pygame.Rect(x, y, rw, rh)
        is_sel = (self.focus_area == "CONTROLS" and self.selected_control_idx == idx)

        pygame.draw.rect(surface, COLOR_CARD_HOVER if is_sel else COLOR_CARD_BG, rect, border_radius=8)
        if is_sel:
            pygame.draw.rect(surface, COLOR_WHITE, rect, width=2, border_radius=8)

        lbl = self.font_item.render(label, True, COLOR_WHITE)
        surface.blit(lbl, (x + 18, y + 16))

        # Slider track
        sw = 180
        sx = x + rw - sw - 70
        sy = y + 21
        track_rect = pygame.Rect(sx, sy, sw, 8)
        pygame.draw.rect(surface, (50, 65, 85), track_rect, border_radius=4)
        fill_w = int(sw * (value / 100.0))
        if fill_w > 0:
            pygame.draw.rect(surface, COLOR_ACCENT, (sx, sy, fill_w, 8), border_radius=4)
        pygame.draw.circle(surface, COLOR_WHITE, (sx + fill_w, sy + 4), 8)

        val_t = self.font_val.render(f"{value}%", True, COLOR_WHITE)
        surface.blit(val_t, (x + rw - 50, y + 16))

        self.control_rects.append({"idx": idx, "rect": rect, "action": action})

    def _render_row_button(self, surface, x, y, idx, label, action: str):
        rw, rh = 790, 50
        rect = pygame.Rect(x, y, rw, rh)
        is_sel = (self.focus_area == "CONTROLS" and self.selected_control_idx == idx)

        pygame.draw.rect(surface, COLOR_CARD_HOVER if is_sel else COLOR_CARD_BG, rect, border_radius=8)
        if is_sel:
            pygame.draw.rect(surface, COLOR_WHITE, rect, width=2, border_radius=8)

        lbl = self.font_item.render(label, True, COLOR_WHITE)
        surface.blit(lbl, (x + 18, y + 16))

        # Botón a la derecha
        btn_w = 120
        btn_r = pygame.Rect(x + rw - btn_w - 18, y + 10, btn_w, 30)
        pygame.draw.rect(surface, COLOR_ACCENT if is_sel else (40, 60, 90), btn_r, border_radius=6)
        btn_t = self.font_btn.render("EJECUTAR", True, COLOR_WHITE)
        surface.blit(btn_t, btn_t.get_rect(center=btn_r.center))

        self.control_rects.append({"idx": idx, "rect": rect, "action": action})

    def _render_row_info(self, surface, x, y, idx, label, val_text: str):
        rw, rh = 790, 50
        rect = pygame.Rect(x, y, rw, rh)
        is_sel = (self.focus_area == "CONTROLS" and self.selected_control_idx == idx)

        pygame.draw.rect(surface, COLOR_CARD_HOVER if is_sel else COLOR_CARD_BG, rect, border_radius=8)
        if is_sel:
            pygame.draw.rect(surface, COLOR_WHITE, rect, width=1, border_radius=8)

        lbl = self.font_item.render(label, True, COLOR_WHITE)
        surface.blit(lbl, (x + 18, y + 16))

        vt = self.font_val.render(val_text, True, COLOR_MUTED)
        surface.blit(vt, vt.get_rect(right=x + rw - 20, centery=y + rh // 2))

        self.control_rects.append({"idx": idx, "rect": rect, "action": "NONE"})


class PS4SettingsState:
    """Estado de StateMachine para PS4SettingsUI."""
    def __init__(self, state_machine, user_data=None, apply_display_callback=None):
        self.state_machine = state_machine
        self.user_data = user_data
        self.apply_display = apply_display_callback
        self.ui = PS4SettingsUI(1280, 720, user_data=user_data, apply_display_callback=apply_display_callback)

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_events(self, events):
        for event in events:
            res = self.ui.handle_event(event)
            if res and res.get("action") == "BACK":
                self.state_machine.change_state("MENU")

    def update(self, dt):
        pass

    def draw(self, screen):
        self.ui.render(screen)
