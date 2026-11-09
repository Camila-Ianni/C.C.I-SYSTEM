"""console_selector_ui.py - Selector Procedural de Consolas & Gestor de Plataformas para C.C.I. SYSTEM.
Renderizado 100% vectorial en código (Pygame puro, sin imágenes fijas recortadas).
Estilo: Obsidian Dark Glass, cápsulas redondeadas, iluminación sutil, telemetría y respuesta táctil/gamepad.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import math
import os
import time
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

# Paleta oficial Dark Glassmorphism
COLOR_BG = (8, 9, 12)
COLOR_PANEL = (13, 16, 23, 190)
COLOR_CARD = (18, 22, 31, 210)
COLOR_CARD_HOVER = (28, 34, 48, 240)
COLOR_BORDER = (255, 255, 255, 30)
COLOR_BORDER_FOCUS = (255, 255, 255, 90)
COLOR_WHITE = (255, 255, 255)
COLOR_MUTED = (160, 165, 175)
COLOR_DIM = (100, 105, 115)
COLOR_GREEN = (34, 197, 94)
COLOR_PILL_BG = (255, 255, 255, 20)

CONSOLES = [
    {
        "id": "snes",
        "name": "Super Nintendo",
        "badge": "16-BIT // SNES",
        "core": "snes9x_libretro.dylib",
        "rom_dir": "roms/snes",
        "extensions": [".smc", ".sfc", ".fig"],
        "desc": "Clásicos legendarios de 16-bits con Modo 7, sonido SPC700 y chips Super-FX.",
        "specs": "65C816 @ 3.58MHz · 128KB RAM · 256x224 NATIVO",
        "color_accent": (220, 225, 235),
    },
    {
        "id": "mame",
        "name": "Arcade Classics",
        "badge": "COIN-OP // MAME & NEO-GEO",
        "core": "fbneo_libretro.dylib",
        "rom_dir": "roms/mame",
        "extensions": [".zip"],
        "desc": "Obras maestras de salón recreativo: Capcom CPS-1/CPS-2, SNK Neo-Geo MVS y Midway.",
        "specs": "M68000 + Z80 · DUAL CPU · HARDWARE DEDICADO",
        "color_accent": (245, 245, 250),
    },
]


class ConsoleSelectorUI:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720):
        self.w = screen_w
        self.h = screen_h
        self.selected_idx = 0
        self.current_view = "CONSOLES"  # "CONSOLES" o "GAMES"
        self.selected_console = CONSOLES[0]
        self.game_list: list[dict] = []
        self.selected_game_idx = 0
        self.anim_t = 0.0

        # Fuentes
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Helvetica, Arial", 32, bold=True)
        self.font_name = pygame.font.SysFont("Helvetica, Arial", 22, bold=True)
        self.font_badge = pygame.font.SysFont("Courier, monospace", 12, bold=True)
        self.font_text = pygame.font.SysFont("Helvetica, Arial", 14)
        self.font_meta = pygame.font.SysFont("Courier, monospace", 11)

    def _discover_games(self, console: dict) -> list[dict]:
        games = []
        rom_dir = ROOT / console["rom_dir"]
        if not rom_dir.exists():
            return games

        exts = set(console.get("extensions", []))
        for p in sorted(rom_dir.iterdir()):
            if p.suffix.lower() in exts:
                # Limpiar nombre visual
                clean_title = p.stem.replace("[!]", "").replace("(U)", "").replace("(USA)", "").replace("(World)", "").replace("(JU)", "").replace("(J)", "").replace("_", " ").strip()
                games.append({
                    "path": str(p),
                    "filename": p.name,
                    "title": clean_title,
                    "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                    "console_id": console["id"],
                })
        return games

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """Retorna {'action': 'LAUNCH', 'game': ...} o navega."""
        if event.type == pygame.KEYDOWN:
            if self.current_view == "CONSOLES":
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_idx = max(0, self.selected_idx - 1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_idx = min(len(CONSOLES) - 1, self.selected_idx + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    self.selected_console = CONSOLES[self.selected_idx]
                    self.game_list = self._discover_games(self.selected_console)
                    self.selected_game_idx = 0
                    self.current_view = "GAMES"
            elif self.current_view == "GAMES":
                if event.key in (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE):
                    self.current_view = "CONSOLES"
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_game_idx = max(0, self.selected_game_idx - 1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_game_idx = min(len(self.game_list) - 1, self.selected_game_idx + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    if self.game_list:
                        chosen = self.game_list[self.selected_game_idx]
                        return {
                            "action": "LAUNCH",
                            "console": self.selected_console,
                            "game": chosen,
                            "core_path": str(ROOT / "cores" / self.selected_console["core"]),
                        }
        return None

    def render(self, surface: pygame.Surface):
        self.anim_t += 0.03

        # Fondo con sutil viñeta oscura
        surface.fill(COLOR_BG)

        # Destello superior procedural
        flare_surf = pygame.Surface((self.w, 220), pygame.SRCALPHA)
        for y in range(220):
            alpha = int(24 * (1.0 - y / 220.0))
            pygame.draw.line(flare_surf, (255, 255, 255, alpha), (0, y), (self.w, y))
        surface.blit(flare_surf, (0, 0))

        if self.current_view == "CONSOLES":
            self._render_consoles_view(surface)
        else:
            self._render_games_view(surface)

    def _render_consoles_view(self, surface: pygame.Surface):
        # Header
        head_txt = self.font_title.render("SISTEMAS Y PLATAFORMAS", True, COLOR_WHITE)
        surface.blit(head_txt, (80, 50))

        sub_txt = self.font_text.render("Selecciona una consola para explorar su biblioteca de títulos preservados.", True, COLOR_MUTED)
        surface.blit(sub_txt, (80, 92))

        # Tarjetas de consolas
        card_w = 520
        card_h = 440
        start_x = 80
        start_y = 140

        for idx, c in enumerate(CONSOLES):
            cx = start_x + idx * (card_w + 30)
            cy = start_y
            is_sel = (idx == self.selected_idx)

            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_col = COLOR_CARD_HOVER if is_sel else COLOR_CARD
            border_col = COLOR_WHITE if is_sel else COLOR_BORDER

            # Cuerpo de la tarjeta
            pygame.draw.rect(card_surf, bg_col, (0, 0, card_w, card_h), border_radius=22)
            pygame.draw.rect(card_surf, border_col, (0, 0, card_w, card_h), width=2 if is_sel else 1, border_radius=22)

            # Inset highlight superior
            pygame.draw.line(card_surf, (255, 255, 255, 60 if is_sel else 25), (20, 1), (card_w - 20, 1), 1)

            # Badge de consola
            badge_t = self.font_badge.render(c["badge"], True, COLOR_WHITE if is_sel else COLOR_MUTED)
            badge_rect = badge_t.get_rect(topleft=(28, 28))
            pill_pad = 8
            pygame.draw.rect(card_surf, COLOR_PILL_BG, (badge_rect.x - pill_pad, badge_rect.y - 4, badge_rect.width + pill_pad * 2, badge_rect.height + 8), border_radius=9999)
            card_surf.blit(badge_t, badge_rect)

            # Estado LED verde
            pygame.draw.circle(card_surf, COLOR_GREEN, (card_w - 36, 36), 5)
            pygame.draw.circle(card_surf, (34, 197, 94, 80), (card_w - 36, 36), 8, 1)

            # Nombre de la consola
            name_t = self.font_title.render(c["name"], True, COLOR_WHITE)
            card_surf.blit(name_t, (28, 75))

            # Descripción
            words = c["desc"].split(" ")
            lines = []
            curr_l = ""
            for w in words:
                if len(curr_l + " " + w) > 48:
                    lines.append(curr_l)
                    curr_l = w
                else:
                    curr_l = (curr_l + " " + w).strip()
            if curr_l:
                lines.append(curr_l)

            dy = 135
            for l in lines:
                lt = self.font_text.render(l, True, COLOR_MUTED)
                card_surf.blit(lt, (28, dy))
                dy += 22

            # Ficha de especificaciones
            dy = 240
            spec_box = pygame.Surface((card_w - 56, 75), pygame.SRCALPHA)
            pygame.draw.rect(spec_box, (0, 0, 0, 80), (0, 0, card_w - 56, 75), border_radius=14)
            pygame.draw.rect(spec_box, (255, 255, 255, 15), (0, 0, card_w - 56, 75), width=1, border_radius=14)

            s1 = self.font_meta.render(f"NÚCLEO: {c['core']}", True, COLOR_MUTED)
            s2 = self.font_meta.render(c["specs"], True, COLOR_DIM)
            spec_box.blit(s1, (16, 16))
            spec_box.blit(s2, (16, 42))
            card_surf.blit(spec_box, (28, dy))

            # Botón de acción inferior
            btn_box = pygame.Surface((card_w - 56, 46), pygame.SRCALPHA)
            if is_sel:
                pygame.draw.rect(btn_box, COLOR_WHITE, (0, 0, card_w - 56, 46), border_radius=9999)
                btn_txt = self.font_name.render("⌧  EXPLORAR JUEGOS", True, (0, 0, 0))
            else:
                pygame.draw.rect(btn_box, (255, 255, 255, 15), (0, 0, card_w - 56, 46), border_radius=9999)
                pygame.draw.rect(btn_box, (255, 255, 255, 30), (0, 0, card_w - 56, 46), width=1, border_radius=9999)
                btn_txt = self.font_name.render("SELECCIONAR", True, COLOR_MUTED)

            bt_rect = btn_txt.get_rect(center=((card_w - 56) // 2, 23))
            btn_box.blit(btn_txt, bt_rect)
            card_surf.blit(btn_box, (28, 350))

            surface.blit(card_surf, (cx, cy))

        # Barra inferior de ayuda
        self._render_legend(surface, [("⌧ A / ENTER", "Seleccionar"), ("⇦ ⇨", "Cambiar Consola")])

    def _render_games_view(self, surface: pygame.Surface):
        # Header de la consola
        top_txt = self.font_badge.render(f"PLATAFORMA // {self.selected_console['badge']}", True, COLOR_MUTED)
        surface.blit(top_txt, (80, 45))

        title_txt = self.font_title.render(f"BIBLIOTECA {self.selected_console['name'].upper()} ({len(self.game_list)})", True, COLOR_WHITE)
        surface.blit(title_txt, (80, 68))

        # Lista de juegos (estilo rack moderno con scroll)
        list_y = 135
        visible_rows = 9
        row_h = 50

        # Scroll window
        start_idx = max(0, min(self.selected_game_idx - 4, max(0, len(self.game_list) - visible_rows)))
        end_idx = min(len(self.game_list), start_idx + visible_rows)

        for i in range(start_idx, end_idx):
            g = self.game_list[i]
            is_active = (i == self.selected_game_idx)
            ry = list_y + (i - start_idx) * (row_h + 8)

            row_surf = pygame.Surface((self.w - 160, row_h), pygame.SRCALPHA)
            bg = (255, 255, 255, 35) if is_active else (255, 255, 255, 8)
            border = COLOR_WHITE if is_active else (255, 255, 255, 20)

            pygame.draw.rect(row_surf, bg, (0, 0, self.w - 160, row_h), border_radius=14)
            if is_active:
                pygame.draw.rect(row_surf, border, (0, 0, self.w - 160, row_h), width=1, border_radius=14)

            # Slot num
            slot_t = self.font_meta.render(f"#{i+1:02d}", True, COLOR_WHITE if is_active else COLOR_DIM)
            row_surf.blit(slot_t, (20, 18))

            # Título
            t_col = COLOR_WHITE if is_active else COLOR_MUTED
            title_t = self.font_name.render(g["title"], True, t_col)
            row_surf.blit(title_t, (65, 12))

            # Tamaño
            sz_t = self.font_meta.render(f"{g['size_mb']} MB", True, COLOR_DIM)
            row_surf.blit(sz_t, (self.w - 280, 18))

            # Pill acción
            if is_active:
                act_pill = pygame.Surface((90, 28), pygame.SRCALPHA)
                pygame.draw.rect(act_pill, COLOR_WHITE, (0, 0, 90, 28), border_radius=9999)
                at = self.font_badge.render("INICIAR", True, (0, 0, 0))
                act_pill.blit(at, at.get_rect(center=(45, 14)))
                row_surf.blit(act_pill, (self.w - 265, 11))

            surface.blit(row_surf, (80, ry))

        # Barra inferior de ayuda
        self._render_legend(surface, [("⌧ A / ENTER", "Jugar Título"), ("◯ B / ESC", "Volver a Consolas"), ("⇧ ⇩", "Navegar")])

    def _render_legend(self, surface: pygame.Surface, items: list[tuple[str, str]]):
        bar_surf = pygame.Surface((self.w, 48), pygame.SRCALPHA)
        pygame.draw.rect(bar_surf, (10, 12, 16, 220), (0, 0, self.w, 48))
        pygame.draw.line(bar_surf, (255, 255, 255, 20), (0, 0), (self.w, 0), 1)

        offset_x = 80
        for key, label in items:
            kt = self.font_badge.render(key, True, COLOR_WHITE)
            kw = kt.get_width() + 16
            pygame.draw.rect(bar_surf, (255, 255, 255, 25), (offset_x, 10, kw, 26), border_radius=9999)
            bar_surf.blit(kt, (offset_x + 8, 16))
            offset_x += kw + 10

            lt = self.font_text.render(label, True, COLOR_MUTED)
            bar_surf.blit(lt, (offset_x, 14))
            offset_x += lt.get_width() + 28

        surface.blit(bar_surf, (0, self.h - 48))
