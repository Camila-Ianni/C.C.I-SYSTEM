"""ps4_profile_ui.py - Pantalla de Perfil de Usuario estilo PlayStation 4 / OmniDash.
100% Python puro con Pygame.
Incluye:
- Banner de perfil, avatar interactivo y nivel del jugador.
- Vitrina de Trofeos oficiales (Platino, Oro, Plata, Bronce) y Gamerscore C.C.I.
- Selector interactivo de avatares (8 avatares disponibles).
- Historial de juegos recientes con tiempo de juego y barras de progreso.
- Estadísticas del sistema y hardware.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import datetime
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

# Colores PS4 / Dark Glass
COLOR_PS_BLUE = (14, 108, 196)
COLOR_PANEL_BG = (15, 24, 38, 235)
COLOR_CARD_BG = (22, 34, 52, 220)
COLOR_CARD_HOVER = (32, 50, 78, 240)
COLOR_WHITE = (255, 255, 255)
COLOR_MUTED = (180, 205, 235)
COLOR_DIM = (110, 135, 170)
COLOR_ACCENT = (0, 162, 255)
COLOR_SUCCESS = (34, 197, 94)
COLOR_GOLD = (255, 204, 0)
COLOR_SILVER = (200, 210, 225)
COLOR_BRONZE = (205, 127, 50)
COLOR_PLATINUM = (110, 210, 255)


class PS4ProfileUI:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720, user_data=None):
        self.w = screen_w
        self.h = screen_h
        self.user_data = user_data

        # Fuentes
        font_path = ROOT / "assets_ps4" / "font" / "sst.ttf"
        font_file = str(font_path) if font_path.exists() else None
        pygame.font.init()
        try:
            self.font_title = pygame.font.Font(font_file, 26)
            self.font_name = pygame.font.Font(font_file, 24)
            self.font_sub = pygame.font.Font(font_file, 14)
            self.font_bold = pygame.font.Font(font_file, 15)
            self.font_stat = pygame.font.Font(font_file, 18)
            self.font_btn = pygame.font.Font(font_file, 13)
        except Exception:
            self.font_title = pygame.font.SysFont("Helvetica, Arial", 26, bold=True)
            self.font_name = pygame.font.SysFont("Helvetica, Arial", 24, bold=True)
            self.font_sub = pygame.font.SysFont("Helvetica, Arial", 14)
            self.font_bold = pygame.font.SysFont("Helvetica, Arial", 15, bold=True)
            self.font_stat = pygame.font.SysFont("Helvetica, Arial", 18, bold=True)
            self.font_btn = pygame.font.SysFont("Helvetica, Arial", 13, bold=True)

        # Sonidos
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

        # Cargar iconos
        self.icons = {}
        for name in ("trophy", "user", "friends", "plus"):
            ip = ROOT / "assets_ps4" / "icons" / f"{name}.png"
            if ip.exists():
                try:
                    self.icons[name] = pygame.image.load(str(ip)).convert_alpha()
                except Exception:
                    pass

        # Datos del jugador
        self.player_name = "Alex"
        self.level = 12
        self.current_avatar = 0
        if self.user_data and hasattr(self.user_data, "data"):
            self.player_name = self.user_data.data.get("player_name", self.player_name)
            self.current_avatar = self.user_data.data.get("avatar", 0)

        # Juegos recientes simulados / reales
        self.recent_games = [
            {"title": "Super Mario World", "platform": "Super Nintendo", "time": "14h 20m", "progress": 95, "icon": "start.png"},
            {"title": "Metal Slug 2", "platform": "Arcade Classics", "time": "6h 45m", "progress": 80, "icon": "battle.png"},
            {"title": "Crash Bandicoot 3", "platform": "PlayStation", "time": "5h 10m", "progress": 62, "icon": "ps.png"},
            {"title": "Pokémon White 2", "platform": "Nintendo DS", "time": "8h 30m", "progress": 45, "icon": "destiny.png"},
        ]

        self.back_btn_rect = pygame.Rect(40, 24, 110, 36)
        self.avatar_rects: list[pygame.Rect] = []

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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.back_btn_rect.collidepoint(mx, my):
                self._play_sfx(self.sfx_nav)
                return {"action": "BACK"}

            # Clic en avatares
            for idx, r in enumerate(self.avatar_rects):
                if r.collidepoint(mx, my):
                    self.current_avatar = idx
                    if self.user_data and hasattr(self.user_data, "data"):
                        self.user_data.data["avatar"] = idx
                        if hasattr(self.user_data, "save"):
                            self.user_data.save()
                    self._play_sfx(self.sfx_reward)
                    return None

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._play_sfx(self.sfx_nav)
                return {"action": "BACK"}

            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.current_avatar = (self.current_avatar + 1) % 8
                self._play_sfx(self.sfx_nav)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.current_avatar = (self.current_avatar - 1) % 8
                self._play_sfx(self.sfx_nav)

        return None

    def render(self, surface: pygame.Surface):
        # 1. Fondo
        if self.bg_surf:
            surface.blit(self.bg_surf, (0, 0))
        else:
            surface.fill(COLOR_PS_BLUE)

        # 2. Botón Volver
        is_back_hover = self.back_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (255, 255, 255, 60 if is_back_hover else 30), self.back_btn_rect, border_radius=18)
        pygame.draw.rect(surface, COLOR_WHITE if is_back_hover else COLOR_MUTED, self.back_btn_rect, width=1, border_radius=18)
        back_txt = self.font_btn.render("⇦ VOLVER", True, COLOR_WHITE)
        surface.blit(back_txt, back_txt.get_rect(center=self.back_btn_rect.center))

        title_txt = self.font_title.render("PERFIL DE USUARIO", True, COLOR_WHITE)
        surface.blit(title_txt, (170, 26))

        # 3. Banner Superior del Jugador
        self._render_header_card(surface)

        # 4. Fila de Trofeos y Gamerscore
        self._render_trophies_row(surface)

        # 5. Dos Columnas Inferiores: Juegos Recientes y Selector de Avatar
        self._render_recent_games(surface)
        self._render_avatar_picker(surface)

    def _render_header_card(self, surface: pygame.Surface):
        bx, by = 40, 75
        bw, bh = 1200, 110

        panel = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(panel, COLOR_PANEL_BG, (0, 0, bw, bh), border_radius=12)
        surface.blit(panel, (bx, by))

        # Avatar circular
        av_center = (bx + 60, by + bh // 2)
        pygame.draw.circle(surface, (30, 60, 95), av_center, 40)
        pygame.draw.circle(surface, COLOR_ACCENT, av_center, 40, width=3)
        av_txt = self.font_name.render(str(self.current_avatar + 1), True, COLOR_WHITE)
        surface.blit(av_txt, av_txt.get_rect(center=av_center))

        # Nombre y Nivel
        name_t = self.font_name.render(f"{self.player_name}", True, COLOR_WHITE)
        surface.blit(name_t, (bx + 120, by + 24))

        lvl_pill = pygame.Rect(bx + 120 + name_t.get_width() + 16, by + 26, 70, 24)
        pygame.draw.rect(surface, COLOR_ACCENT, lvl_pill, border_radius=12)
        lvl_t = self.font_btn.render(f"NVL {self.level}", True, COLOR_WHITE)
        surface.blit(lvl_t, lvl_t.get_rect(center=lvl_pill.center))

        # Estado en línea
        status_t = self.font_sub.render("🟢 En Línea — C.C.I. SYSTEM Virtual Console", True, (74, 222, 128))
        surface.blit(status_t, (bx + 120, by + 60))

        # Badge C.C.I. PLUS a la derecha
        plus_rect = pygame.Rect(bx + bw - 160, by + 34, 130, 38)
        pygame.draw.rect(surface, (255, 204, 0, 40), plus_rect, border_radius=19)
        pygame.draw.rect(surface, COLOR_GOLD, plus_rect, width=2, border_radius=19)
        plus_t = self.font_bold.render("+ C.C.I. PLUS", True, COLOR_GOLD)
        surface.blit(plus_t, plus_t.get_rect(center=plus_rect.center))

    def _render_trophies_row(self, surface: pygame.Surface):
        rx, ry = 40, 200
        rw, rh = 1200, 85

        panel = pygame.Surface((rw, rh), pygame.SRCALPHA)
        pygame.draw.rect(panel, COLOR_PANEL_BG, (0, 0, rw, rh), border_radius=12)
        surface.blit(panel, (rx, ry))

        # Gamerscore Total
        gs_lbl = self.font_sub.render("PUNTUACIÓN GAMERSCORE", True, COLOR_MUTED)
        surface.blit(gs_lbl, (rx + 30, ry + 18))
        gs_val = self.font_title.render("12,450 G", True, COLOR_WHITE)
        surface.blit(gs_val, (rx + 30, ry + 42))

        # Trofeos
        trophies = [
            ("PLATINO", "3", COLOR_PLATINUM),
            ("ORO", "14", COLOR_GOLD),
            ("PLATA", "28", COLOR_SILVER),
            ("BRONCE", "65", COLOR_BRONZE),
        ]

        tx_base = rx + 450
        spacing = 180
        for idx, (kind, count, color) in enumerate(trophies):
            tx = tx_base + idx * spacing
            pygame.draw.circle(surface, color, (tx, ry + rh // 2), 16)
            pygame.draw.circle(surface, COLOR_WHITE, (tx, ry + rh // 2), 16, width=1)

            t_val = self.font_stat.render(count, True, COLOR_WHITE)
            surface.blit(t_val, (tx + 26, ry + 22))

            t_lbl = self.font_btn.render(kind, True, color)
            surface.blit(t_lbl, (tx + 26, ry + 46))

    def _render_recent_games(self, surface: pygame.Surface):
        gx, gy = 40, 305
        gw, gh = 720, 380

        panel = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.rect(panel, COLOR_PANEL_BG, (0, 0, gw, gh), border_radius=12)
        surface.blit(panel, (gx, gy))

        head_t = self.font_bold.render("ACTIVIDAD RECIENTE & HORAS JUGADAS", True, COLOR_WHITE)
        surface.blit(head_t, (gx + 24, gy + 18))

        row_y = gy + 55
        row_h = 70
        for idx, game in enumerate(self.recent_games):
            ry = row_y + idx * (row_h + 8)
            card = pygame.Rect(gx + 20, ry, gw - 40, row_h)
            pygame.draw.rect(surface, COLOR_CARD_BG, card, border_radius=8)

            # Icono
            pygame.draw.circle(surface, (40, 60, 90), (card.x + 35, card.centery), 22)
            sym = self.font_bold.render(game["platform"][:2].upper(), True, COLOR_WHITE)
            surface.blit(sym, sym.get_rect(center=(card.x + 35, card.centery)))

            # Títulos
            t_txt = self.font_bold.render(game["title"], True, COLOR_WHITE)
            surface.blit(t_txt, (card.x + 75, card.y + 14))

            p_txt = self.font_sub.render(f"{game['platform']} • {game['time']}", True, COLOR_MUTED)
            surface.blit(p_txt, (card.x + 75, card.y + 38))

            # Barra de progreso
            bw = 140
            bx = card.right - bw - 20
            by = card.y + 28
            pygame.draw.rect(surface, (50, 65, 85), (bx, by, bw, 8), border_radius=4)
            fill_w = int(bw * (game["progress"] / 100.0))
            pygame.draw.rect(surface, COLOR_ACCENT, (bx, by, fill_w, 8), border_radius=4)

            pct_txt = self.font_btn.render(f"{game['progress']}%", True, COLOR_WHITE)
            surface.blit(pct_txt, pct_txt.get_rect(right=bx - 12, centery=by + 4))

    def _render_avatar_picker(self, surface: pygame.Surface):
        px, py = 780, 305
        pw, ph = 460, 380

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, COLOR_PANEL_BG, (0, 0, pw, ph), border_radius=12)
        surface.blit(panel, (px, py))

        head_t = self.font_bold.render("CAMBIAR AVATAR DE USUARIO", True, COLOR_WHITE)
        surface.blit(head_t, (px + 24, py + 18))

        sub_t = self.font_sub.render("Haz clic o navega para seleccionar tu avatar:", True, COLOR_MUTED)
        surface.blit(sub_t, (px + 24, py + 44))

        self.avatar_rects = []
        cols, rows = 4, 2
        av_size = 72
        spacing_x = 24
        spacing_y = 30
        start_x = px + 40
        start_y = py + 85

        for i in range(8):
            r = i // cols
            c = i % cols
            ax = start_x + c * (av_size + spacing_x)
            ay = start_y + r * (av_size + spacing_y)
            rect = pygame.Rect(ax, ay, av_size, av_size)
            self.avatar_rects.append(rect)

            is_sel = (i == self.current_avatar)
            bg_col = (40, 80, 130) if is_sel else (30, 45, 65)

            pygame.draw.rect(surface, bg_col, rect, border_radius=14)
            if is_sel:
                pygame.draw.rect(surface, COLOR_ACCENT, rect, width=3, border_radius=14)
                pygame.draw.circle(surface, COLOR_SUCCESS, (rect.right - 8, rect.y + 8), 6)
            else:
                pygame.draw.rect(surface, (255, 255, 255, 20), rect, width=1, border_radius=14)

            num_t = self.font_title.render(str(i + 1), True, COLOR_WHITE)
            surface.blit(num_t, num_t.get_rect(center=rect.center))

        # Nota al pie
        foot_t = self.font_sub.render("Los avatares se guardan en tu perfil local de C.C.I.", True, COLOR_DIM)
        surface.blit(foot_t, (px + 24, py + ph - 40))


class PS4ProfileState:
    """Estado de StateMachine para PS4ProfileUI."""
    def __init__(self, state_machine, user_data=None):
        self.state_machine = state_machine
        self.user_data = user_data
        self.ui = PS4ProfileUI(1280, 720, user_data=user_data)

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
