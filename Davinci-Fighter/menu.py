"""
menu.py - Menú Principal y exportación de pantallas de inicio de Da Vinci Fighters.
Re-exporta TitleScreen desde title_screen.py para compatibilidad retrospectiva 100%.
"""

import os
import pygame
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_WHITE,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BG,
    MODE_PVP,
    MODE_PVAI,
)
from audio_manager import audio_manager
from title_screen import TitleScreen

__all__ = ["TitleScreen", "MainMenu"]


class MainMenu:
    """
    Menú Principal del juego Da Vinci Fighters con selección de modos (1P VS IA / 2P PVP),
    audio procedimental (navegación y confirmación) y pantalla modal de controles.
    """

    def __init__(self, screen):
        self.screen = screen
        self.font_title = pygame.font.Font(None, 84)
        self.font_sub = pygame.font.Font(None, 36)
        self.font_option = pygame.font.Font(None, 42)

        self.options = [
            "1 JUGADOR (VS IA)",
            "2 JUGADORES (PVP)",
            "CÓMO JUGAR",
            "SALIR",
        ]
        self.selected_idx = 0
        self.selected_mode = None
        self.showing_controls = False
        self.anim_timer = 0

        audio_manager.play_music("menu", loop=True)

    def handle_input(self, event):
        """Maneja la selección con teclado (flechas / WASD / Enter / Space) y SFX."""
        if self.showing_controls:
            if event.type == pygame.KEYDOWN:
                self.showing_controls = False
                audio_manager.play_sfx("select")
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_idx = (self.selected_idx - 1) % len(self.options)
                audio_manager.play_sfx("menu_navigate")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_idx = (self.selected_idx + 1) % len(self.options)
                audio_manager.play_sfx("menu_navigate")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                audio_manager.play_sfx("menu_confirm")
                if self.selected_idx == 0:
                    self.selected_mode = MODE_PVAI
                    return {"action": "start", "mode": MODE_PVAI}
                elif self.selected_idx == 1:
                    self.selected_mode = MODE_PVP
                    return {"action": "start", "mode": MODE_PVP}
                elif self.selected_idx == 2:
                    self.showing_controls = True
                    return None
                elif self.selected_idx == 3:
                    return {"action": "exit"}

        return None

    def update(self, dt=1.0 / 60):
        """Actualiza animaciones internas del cursor o temporizadores."""
        frames = max(1, int(round(dt * 60))) if dt > 0 else 1
        self.anim_timer += frames

    def draw(self, screen=None):
        """Renderiza el menú principal en pantalla (soporta parámetro screen opcional)."""
        target = screen if screen is not None else self.screen
        if target is None:
            return

        target.fill(COLOR_BG)

        for y in range(0, 500):
            r = max(0, min(255, 20 + int(y * 0.05)))
            g = max(0, min(255, 20 + int(y * 0.04)))
            b = max(0, min(255, 45 + int(y * 0.08)))
            pygame.draw.line(target, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        if self.showing_controls:
            self.draw_how_to_play(target)
            return

        title_surf = self.font_title.render("DA VINCI FIGHTERS", True, COLOR_YELLOW)
        sub_surf = self.font_sub.render("CODE. FIGHT. WIN.", True, COLOR_WHITE)

        target.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 120))
        target.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 210))

        start_y = 330
        for i, opt_text in enumerate(self.options):
            is_selected = (i == self.selected_idx)
            color = COLOR_YELLOW if is_selected else COLOR_WHITE
            prefix = "> " if is_selected else "  "

            opt_surf = self.font_option.render(f"{prefix}{opt_text}", True, color)
            target.blit(opt_surf, (SCREEN_WIDTH // 2 - opt_surf.get_width() // 2, start_y + (i * 60)))

        footer = self.font_sub.render("Presiona ENTER para seleccionar", True, (160, 160, 180))
        target.blit(footer, (SCREEN_WIDTH // 2 - footer.get_width() // 2, 640))

    def draw_how_to_play(self, screen=None):
        """Pantalla informativa de controles de combate."""
        target = screen if screen is not None else self.screen
        if target is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH - 160, SCREEN_HEIGHT - 160), pygame.SRCALPHA)
        overlay.fill((20, 20, 30, 240))
        target.blit(overlay, (80, 80))
        pygame.draw.rect(target, COLOR_YELLOW, (80, 80, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 160), 3)

        title = self.font_option.render("CONTROLES DE COMBATE", True, COLOR_YELLOW)
        target.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 110))

        controls_info = [
            "PLAYER 1:  W (Salto) | A (Izq) | S (Agachado) | D (Der) | L (Bloqueo)",
            "Ataques P1: J (Golpe Débil) | K (Golpe Fuerte) | U (Patada Débil) | I (Patada Fuerte)",
            "Especial P1: O  |  Ultimate P1: P",
            "--------------------------------------------------------------------------------",
            "PLAYER 2:  Flechas (Arriba / Izq / Abajo / Der) | Numpad 6 (Bloqueo)",
            "Ataques P2: Numpad 1 (Golpe D) | Numpad 2 (Golpe F) | Numpad 4 (Patada D) | Numpad 5 (Patada F)",
            "Especial P2: Numpad 7  |  Ultimate P2: Numpad 8",
        ]

        start_y = 200
        for i, line in enumerate(controls_info):
            txt = self.font_sub.render(line, True, COLOR_WHITE)
            target.blit(txt, (120, start_y + (i * 45)))

        back_txt = self.font_sub.render("Presiona cualquier tecla para volver", True, COLOR_YELLOW)
        target.blit(back_txt, (SCREEN_WIDTH // 2 - back_txt.get_width() // 2, 600))
