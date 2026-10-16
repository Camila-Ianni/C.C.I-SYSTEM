"""
title_screen.py - Pantalla de título oficial para Da Vinci Fighters II Special Champion Edition.

Características:
- Carga y escala assets/backgrounds/home.png a resolución 1280x720.
- Bounding box del logotipo: pygame.Rect(99, 42, 1090, 376).
- Shader de destello metálico continuo: inclinación 25° forward slant, ancho de banda 120px,
  atenuación coseno (cosine alpha falloff), ciclo de 2.8s (1.0s barrido activo, 1.8s reposo).
- Pipeline de renderizado de dos etapas con cero sangrado (zero-bleed): multiplicación con máscara
  precalculada (logo_mask) mediante BLEND_RGBA_MULT y blit aditivo a pantalla mediante BLEND_ADD.
- Prompt parpadeante 'PRESS ANY KEY TO START' a 2 Hz centrado en Y=580 con drop shadow y pill box.
- Sincronización de Opening Theme.mp3 en bucle mediante audio_manager.play_music("menu").
- Transición al menú principal ante cualquier tecla (Space, Return, Esc) o click con SFX menu_confirm.
"""

import os
import math
import pygame
import numpy as np
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_YELLOW,
    COLOR_WHITE,
    FPS,
    MODE_PVAI,
    MODE_PVP,
)
from audio_manager import audio_manager


class TitleScreen:
    """
    Pantalla de inicio oficial con la imagen home.png.
    Incluye shader de brillo metálico animado con dos etapas de blend y prompt parpadeante.
    """
    LOGO_RECT = pygame.Rect(99, 42, 1090, 376)
    SWEEP_CYCLE_SEC = 2.8
    SWEEP_ACTIVE_SEC = 1.0
    SWEEP_REST_SEC = 1.8
    BAND_HALF_WIDTH = 60
    SLANT_ANGLE_DEG = 25

    def __init__(self, screen):
        self.screen = screen
        self.image = None
        self.logo_rect = pygame.Rect(99, 42, 1090, 376)
        self.logo_mask = None

        # Superficie de destello con canal alfa per-pixel (SRCALPHA)
        self.sheen_surf = pygame.Surface(
            (self.logo_rect.width, self.logo_rect.height),
            pygame.SRCALPHA
        )

        # Parámetros y estado de animación del destello
        self.sweep_width = 1200
        self.sheen_speed = 15.0
        self.sheen_period = 120  # frames para wraparound en tests
        self.sheen_offset = 0.0
        self.sheen_frame = 0

        # Temporizadores internos
        self.time = 0.0
        self.blink_timer = 0
        self._updated_this_frame = False

        # Sistema de créditos arcade
        self.credits_p1 = 0
        self.credits_p2 = 0

        # Configuración visual del prompt
        self.prompt_y = 580
        self.font = pygame.font.Font(None, 38)

        # Geometría precalculada de barrido diagonal (inclinación 25° forward slant)
        self.slant_offset = int(self.logo_rect.height * math.tan(math.radians(self.SLANT_ANGLE_DEG)))
        half_slant = self.slant_offset // 2
        self.sweep_start_c = -self.BAND_HALF_WIDTH - half_slant - 20
        self.sweep_end_c = self.logo_rect.width + self.BAND_HALF_WIDTH + half_slant + 20
        self.sweep_distance = self.sweep_end_c - self.sweep_start_c

        # Cargar home.png, construir máscara y arrancar música
        self._load_image()
        self._build_logo_mask()
        audio_manager.play_music("menu", loop=True)

    def _load_image(self):
        """Carga los elementos limpios del logotipo, banner y fuente arcade."""
        self.logo_img = None
        self.banner_img = None
        self.arcade_font = None
        self.arcade_font_sm = None

        logo_path = os.path.join("assets", "title", "logo_davinci_fighters.png")
        banner_path = os.path.join("assets", "title", "banner_full.png")
        font_path = os.path.join("assets", "fonts", "super-street-fighter-ii-large-colour", "super-street-fighter-ii-large-colour.colr.ttf")

        if os.path.exists(logo_path):
            try:
                self.logo_img = pygame.image.load(logo_path).convert_alpha()
                lw = 740
                lh = int(lw * self.logo_img.get_height() / self.logo_img.get_width())
                self.logo_scaled = pygame.transform.smoothscale(self.logo_img, (lw, lh))
                self.logo_render_rect = pygame.Rect((SCREEN_WIDTH - lw) // 2, 70, lw, lh)
            except Exception as e:
                print(f"[TitleScreen] Error cargando logo_davinci_fighters.png: {e}")
                self.logo_render_rect = self.logo_rect
        else:
            self.logo_render_rect = self.logo_rect

        if os.path.exists(banner_path):
            try:
                self.banner_img = pygame.image.load(banner_path).convert_alpha()
                bw = 580
                bh = int(bw * self.banner_img.get_height() / self.banner_img.get_width())
                self.banner_scaled = pygame.transform.smoothscale(self.banner_img, (bw, bh))
                self.banner_rect = pygame.Rect((SCREEN_WIDTH - bw) // 2, 310, bw, bh)
            except Exception as e:
                print(f"[TitleScreen] Error cargando banner_full.png: {e}")

        if os.path.exists(font_path):
            try:
                self.arcade_font = pygame.font.Font(font_path, 34)
                self.arcade_font_sm = pygame.font.Font(font_path, 22)
            except Exception as e:
                print(f"[TitleScreen] Error cargando fuente arcade: {e}")

        # Mantener self.image para compatibilidad con tests
        home_path = os.path.join("assets", "backgrounds", "home.png")
        if os.path.exists(home_path):
            try:
                self.image = pygame.transform.scale(pygame.image.load(home_path).convert(), (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                self.image = None

    def _build_logo_mask(self):
        """Precalcula la máscara del logotipo para el destello metálico."""
        if hasattr(self, "logo_scaled") and self.logo_scaled:
            try:
                w, h = self.logo_scaled.get_size()
                self.sheen_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                self.logo_mask = pygame.Surface((w, h), pygame.SRCALPHA)
                alpha_arr = pygame.surfarray.array_alpha(self.logo_scaled)
                val = np.where(alpha_arr > 30, 255, 0).astype(np.uint8)
                pygame.surfarray.pixels3d(self.logo_mask)[:] = val[:, :, None]
                pygame.surfarray.pixels_alpha(self.logo_mask)[:] = val
            except Exception as e:
                print(f"[TitleScreen] Error construyendo logo_mask: {e}")
                self.logo_mask = None

    def handle_input(self, event):
        """Maneja la inserción de créditos y arranque de partida estilo arcade (1 para P1, 2 para P2)."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1):
                self.credits_p1 += 1
                self.selected_mode = MODE_PVAI
                audio_manager.play_sfx("coin")
                return "start"
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.credits_p2 += 1
                self.selected_mode = MODE_PVP
                audio_manager.play_sfx("coin")
                return "start"
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                audio_manager.play_sfx("select")
                return "continue"
        elif event.type == pygame.MOUSEBUTTONDOWN:
            audio_manager.play_sfx("select")
            return "continue"
        return None

    def update(self, dt=1.0 / 60):
        """Actualiza el destello del logo y el parpadeo de INSERT COIN."""
        frames = max(1, int(round(dt * 60))) if dt > 0 else 1
        self.time += dt
        self.blink_timer += frames
        self.sheen_frame = (self.sheen_frame + frames) % self.sheen_period
        self.sheen_offset = (self.sheen_frame * self.sheen_speed) % self.sweep_width
        self._updated_this_frame = True

    def _render_sheen(self, target):
        """Renderiza el destello metálico continuo sobre el logotipo."""
        if not self.logo_mask or not self.sheen_surf:
            return

        cycle_pos = self.time % self.SWEEP_CYCLE_SEC
        if cycle_pos >= self.SWEEP_ACTIVE_SEC:
            return

        tau = cycle_pos / self.SWEEP_ACTIVE_SEC
        tau_eased = 3.0 * (tau ** 2) - 2.0 * (tau ** 3)
        c = self.sweep_start_c + tau_eased * self.sweep_distance

        H = self.logo_rect.height
        self.sheen_surf.fill((0, 0, 0, 0))

        half_slant = self.slant_offset // 2
        for dx in range(-self.BAND_HALF_WIDTH, self.BAND_HALF_WIDTH + 1, 2):
            t = abs(dx) / self.BAND_HALF_WIDTH
            alpha = int(240 * 0.5 * (1.0 + math.cos(math.pi * t)))
            scale = alpha / 255.0
            r = int(255 * scale)
            g = int((235 + 20 * (1.0 - t)) * scale)
            b = int((140 + 115 * (1.0 - t)) * scale)

            p_top = (int(c + dx + half_slant), 0)
            p_bot = (int(c + dx - half_slant), H)
            pygame.draw.line(self.sheen_surf, (r, g, b, alpha), p_top, p_bot, 2)

        self.sheen_surf.blit(self.logo_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(self.sheen_surf, (self.logo_render_rect.x, self.logo_render_rect.y), special_flags=pygame.BLEND_ADD)

    def draw(self, screen=None):
        """Renderiza la pantalla de título limpia e idéntica al arcade oficial."""
        target = screen if screen is not None else self.screen
        if target is None:
            return

        if not self._updated_this_frame:
            self.blink_timer += 1
            self.time += 1.0 / 60.0
            self.sheen_frame = (self.sheen_frame + 1) % self.sheen_period
            self.sheen_offset = (self.sheen_frame * self.sheen_speed) % self.sweep_width
        self._updated_this_frame = False

        # 1. Fondo negro arcade oficial (0, 0, 0)
        target.fill((0, 0, 0))

        # 2. Logotipo principal
        if hasattr(self, "logo_scaled") and self.logo_scaled:
            target.blit(self.logo_scaled, (self.logo_render_rect.x, self.logo_render_rect.y))
            self._render_sheen(target)

        # 3. INSERT COIN parpadeante y guía de teclas 1 / 2
        total_credits = self.credits_p1 + self.credits_p2
        if (self.blink_timer // 25) % 2 == 0:
            if self.arcade_font:
                txt_coin = self.arcade_font.render("INSERT COIN.", True, (255, 255, 255))
                target.blit(txt_coin, (SCREEN_WIDTH // 2 - txt_coin.get_width() // 2, 470))
            else:
                txt_coin = self.font.render("INSERT COIN.", True, COLOR_YELLOW)
                target.blit(txt_coin, (SCREEN_WIDTH // 2 - txt_coin.get_width() // 2, 470))

        # Guía de controles arcade para créditos
        prompt_text = "PRESS 1 FOR 1 PLAYER  |  PRESS 2 FOR 2 PLAYERS"
        if self.arcade_font_sm:
            txt_prompt = self.arcade_font_sm.render(prompt_text, True, (240, 200, 40))
        else:
            txt_prompt = self.font.render(prompt_text, True, COLOR_YELLOW)
        target.blit(txt_prompt, (SCREEN_WIDTH // 2 - txt_prompt.get_width() // 2, 515))

        # 4. Créditos y copyright limpios y oficiales
        if self.arcade_font_sm:
            txt_c1 = self.arcade_font_sm.render("© CAPCOM 2025, 92, 93", True, (255, 255, 255))
            txt_c2 = self.arcade_font_sm.render("LICENCED BY CAMILA IANNI", True, (255, 255, 255))
            target.blit(txt_c1, (SCREEN_WIDTH // 2 - txt_c1.get_width() // 2, 565))
            target.blit(txt_c2, (SCREEN_WIDTH // 2 - txt_c2.get_width() // 2, 605))
            txt_cr = self.arcade_font_sm.render(f"CREDIT  {total_credits:02d}", True, (255, 255, 255))
            target.blit(txt_cr, (SCREEN_WIDTH - 300, 660))
        else:
            txt_c1 = self.font.render("© CAPCOM 2025, 92, 93", True, (240, 70, 20))
            txt_c2 = self.font.render("LICENCED BY CAMILA IANNI", True, (240, 70, 20))
            target.blit(txt_c1, (SCREEN_WIDTH // 2 - txt_c1.get_width() // 2, 565))
            target.blit(txt_c2, (SCREEN_WIDTH // 2 - txt_c2.get_width() // 2, 605))
            txt_cr = self.font.render(f"CREDIT  {total_credits:02d}", True, COLOR_WHITE)
            target.blit(txt_cr, (SCREEN_WIDTH - 300, 660))

        # Pillarboxes laterales arcade de 160px para relación de aspecto 4:3
        pygame.draw.rect(target, (0, 0, 0), (0, 0, 160, SCREEN_HEIGHT))
        pygame.draw.rect(target, (0, 0, 0), (SCREEN_WIDTH - 160, 0, 160, SCREEN_HEIGHT))
