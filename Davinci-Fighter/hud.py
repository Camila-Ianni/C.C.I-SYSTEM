"""
hud.py - Interfaz de Combate Arcade Oficial de Street Fighter II.
================================================================
Implementa todos los elementos visuales extraídos directamente del sprite sheet:
assets/HUD elements/SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Miscellaneous - HUD Elements.png

Incluye:
1. Puntuaciones arcade superiores (1P, HI, 2P) con dígitos y tipografía oficial.
2. Barras de vida auténticas:
   - Riel con marco blanco y extremos exteriores redondeados.
   - Caja central con logotipo 'KO'.
   - Relleno degradado amarillo auténtico de salud restante.
   - Relleno degradado rojo auténtico de daño/vida perdida.
   - Sentido de reducción arcade: P1 se vacía hacia la izquierda, P2 hacia la derecha.
3. Temporizador de combate (99s) debajo de la caja 'KO' usando los números grandes oficiales.
4. Nombres de personajes auténticos debajo de las barras de vida:
   - Sprites originales ripeados para personajes clásicos (RYU, GUILE, BLANKA, HONDA, KEN, etc.).
   - Tipografía SF2 arcade de alta fidelidad para los profesores (CARLONI, CAVASSO, ROMERO, GAMALIEL, SELLANES).
5. Medallones Capcom para victorias de Round (Round Wins).
6. Banners oficiales pre-renderizados: "ROUND 1", "ROUND 2", "ROUND 3", "FIGHT!" y "K.O.".
7. Barra de energía (Special Meter) con indicador de Ultimate cargado.
"""

import os
import pygame
from settings import SCREEN_WIDTH, COLOR_WHITE, COLOR_RED, COLOR_YELLOW, COLOR_GREEN, COLOR_BLACK
from arcade_font import get_arcade_font


class HUD:
    """
    Administrador oficial de HUD arcade con assets de Street Fighter II.
    """
    def __init__(self):
        pygame.font.init()
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 18)
        self.font_medium = pygame.font.Font(None, 40)
        self.font_timer = pygame.font.Font(None, 54)
        self.font_large = pygame.font.Font(None, 72)
        self.arcade_font = get_arcade_font()

        # Marcadores de puntuación arcade
        self.p1_score = 12000
        self.p2_score = 8500
        self.top_score = 50000

        # Temporizador interno para parpadeo de peligro / banners
        self.anim_tick = 0

        # Cargar y recortar assets de HUD
        self.sheet_loaded = False
        self.lbl_1p = None
        self.lbl_hi = None
        self.lbl_2p = None
        self.big_digits = {}
        self.small_digits = {}
        self.red_ko = None
        self.white_ko = None
        self.round_word = None
        self.fight_word = None
        self.round_nums = {}
        self.names_orange = {}

        self._init_hud_sprites()

    def _init_hud_sprites(self):
        """Carga y procesa con transparencia colorkey la hoja de sprites de HUD."""
        sheet_path = os.path.join(
            "assets",
            "HUD elements",
            "SNES - Street Fighter II_ The World Warrior _ Street Fighter II Turbo_ Hyper Fighting - Miscellaneous - HUD Elements.png"
        )
        if not os.path.exists(sheet_path):
            return

        try:
            raw_sheet = pygame.image.load(sheet_path)
            # Detectar color de fondo en la esquina o margen (0, 0, 32)
            bg_col = raw_sheet.get_at((0, 100))[:3]

            def extract(rect):
                sub = raw_sheet.subsurface(rect).copy()
                sub.set_colorkey(bg_col)
                alpha = pygame.Surface(sub.get_size(), pygame.SRCALPHA)
                alpha.blit(sub, (0, 0))
                return alpha

            # 1. Etiquetas de puntuación superiores
            self.lbl_1p = extract((9, 2, 14, 8))
            self.lbl_hi = extract((87, 2, 15, 8))
            self.lbl_2p = extract((175, 2, 16, 8))

            # 2. Números grandes (Timer)
            big_coords = [
                (108, 244, 8, 12),  # 0
                (20, 244, 6, 12),   # 1
                (28, 244, 8, 12),   # 2
                (38, 244, 8, 12),   # 3
                (48, 244, 8, 12),   # 4
                (58, 244, 8, 12),   # 5
                (68, 244, 8, 12),   # 6
                (78, 244, 8, 12),   # 7
                (88, 244, 8, 12),   # 8
                (98, 244, 8, 12),   # 9
            ]
            for d, r in enumerate(big_coords):
                self.big_digits[d] = extract(r)

            # 3. Números pequeños (Scores)
            small_coords = [
                (277, 246, 8, 8),  # 0
                (181, 246, 5, 8),  # 1
                (189, 246, 8, 8),  # 2
                (200, 246, 8, 8),  # 3
                (211, 246, 8, 8),  # 4
                (222, 246, 8, 8),  # 5
                (233, 246, 8, 8),  # 6
                (244, 246, 8, 8),  # 7
                (255, 246, 8, 8),  # 8
                (266, 246, 8, 8),  # 9
            ]
            for d, r in enumerate(small_coords):
                self.small_digits[d] = extract(r)

            # 4. Logotipos centrales de KO
            self.red_ko = extract((173, 41, 16, 14))
            self.white_ko = extract((119, 11, 16, 14))

            # 5. Banners oficiales de Round y Fight
            self.round_word = extract((353, 47, 43, 16))
            self.fight_word = extract((359, 90, 48, 15))
            self.round_nums = {
                1: extract((402, 27, 7, 16)),
                2: extract((401, 47, 9, 16)),
                3: extract((401, 67, 9, 16)),
            }

            # 6. Nombres de personajes oficiales (Paleta Naranja original)
            self.names_orange = {
                "ryu": extract((10, 46, 24, 8)),
                "honda": extract((10, 57, 56, 8)),
                "blanka": extract((10, 68, 48, 8)),
                "guile": extract((10, 79, 40, 8)),
                "ken": extract((10, 90, 24, 8)),
                "chunli": extract((10, 101, 55, 8)),
                "zangief": extract((10, 112, 56, 8)),
                "dhalsim": extract((10, 123, 56, 8)),
                "balrog": extract((10, 134, 48, 8)),
                "vega": extract((10, 145, 32, 8)),
                "sagat": extract((10, 156, 40, 8)),
                "bison": extract((10, 167, 56, 8)),
            }

            self.sheet_loaded = True
        except Exception as e:
            print(f"[HUD] Error cargando sprite sheet de HUD: {e}")
            self.sheet_loaded = False

    def draw_scores(self, screen, margin_x=76, y=10, scale=2.4):
        """Dibuja el encabezado de puntuación arcade (1P, HI, 2P) con los dígitos oficiales."""
        w = screen.get_width()
        center_x = w // 2

        if self.sheet_loaded and self.lbl_1p and self.small_digits:
            # Función auxiliar para renderizar dígitos pequeños con escala
            def render_digits(surf, start_x, start_y, number_val):
                s = f"{number_val:06d}"
                cx = start_x
                for ch in s:
                    d = int(ch)
                    spr = self.small_digits.get(d)
                    if spr:
                        sw, sh = int(spr.get_width() * scale), int(spr.get_height() * scale)
                        scaled = pygame.transform.scale(spr, (sw, sh))
                        surf.blit(scaled, (cx, start_y))
                        cx += sw + 1

            # 1P Score
            sw1, sh1 = int(14 * scale), int(8 * scale)
            screen.blit(pygame.transform.scale(self.lbl_1p, (sw1, sh1)), (margin_x, y))
            render_digits(screen, margin_x + sw1 + 8, y, self.p1_score)

            # High Score (HI)
            sw_hi, sh_hi = int(15 * scale), int(8 * scale)
            total_hi_w = sw_hi + 8 + (6 * int(8 * scale))
            hi_start_x = center_x - total_hi_w // 2
            screen.blit(pygame.transform.scale(self.lbl_hi, (sw_hi, sh_hi)), (hi_start_x, y))
            render_digits(screen, hi_start_x + sw_hi + 8, y, self.top_score)

            # 2P Score
            sw2, sh2 = int(16 * scale), int(8 * scale)
            total_2p_w = sw2 + 8 + (6 * int(8 * scale))
            p2_start_x = w - margin_x - total_2p_w
            screen.blit(pygame.transform.scale(self.lbl_2p, (sw2, sh2)), (p2_start_x, y))
            render_digits(screen, p2_start_x + sw2 + 8, y, self.p2_score)

        elif self.arcade_font and self.arcade_font.loaded:
            # Fallback a ArcadeFont
            margin = int(w * 0.04)
            self.arcade_font.render_to(screen, (margin, y), f"1P {self.p1_score:06d}", scale=0.6)
            self.arcade_font.render_to(screen, (center_x, y), f"TOP {self.top_score:06d}", scale=0.6, align="center")
            self.arcade_font.render_to(screen, (w - margin, y), f"2P {self.p2_score:06d}", scale=0.6, align="right")
        else:
            p1_s = self.font_small.render(f"1P {self.p1_score:06d}", True, COLOR_YELLOW)
            top_s = self.font_small.render(f"TOP {self.top_score:06d}", True, COLOR_WHITE)
            p2_s = self.font_small.render(f"2P {self.p2_score:06d}", True, COLOR_YELLOW)
            screen.blit(p1_s, (margin_x, y))
            screen.blit(top_s, (center_x - top_s.get_width() // 2, y))
            screen.blit(p2_s, (w - margin_x - p2_s.get_width(), y))

    def draw_health_bar(self, screen, fighter, x, y, width=370, height=24, is_p2=False):
        """
        Dibuja la barra de vida auténtica de Street Fighter II:
        - Marco exterior blanco con bordes exteriores redondeados.
        - Daño recibido en rojo degradado auténtico.
        - Salud restante en amarillo degradado brillante.
        - Vaciamiento en dirección original: P1 se vacía hacia la izquierda, P2 hacia la derecha.
        """
        ratio = max(0.0, min(1.0, fighter.health / fighter.max_health))

        # Marco exterior y fondo rojo de vida vacía
        frame_rect = pygame.Rect(x, y, width, height)
        corner_r = 4

        # Fondo rojo para salud perdida
        pygame.draw.rect(screen, (190, 0, 0), frame_rect, border_radius=corner_r)
        # Líneas de sombra y relieve del fondo rojo
        pygame.draw.line(screen, (230, 20, 20), (x + 2, y + 2), (x + width - 2, y + 2), 2)
        pygame.draw.line(screen, (90, 0, 0), (x + 2, y + height - 3), (x + width - 2, y + height - 3), 2)

        # Barra amarilla de salud restante
        fill_w = int(width * ratio)
        if fill_w > 0:
            if not is_p2:
                # P1: La salud restante queda a la izquierda, el daño rojo a la derecha
                y_rect = pygame.Rect(x, y, fill_w, height)
            else:
                # P2: La salud restante queda a la derecha, el daño rojo a la izquierda
                y_rect = pygame.Rect(x + width - fill_w, y, fill_w, height)

            # Si la salud es crítica (< 20%), parpadeo de alerta
            is_critical = ratio <= 0.20
            is_flash = is_critical and ((self.anim_tick // 6) % 2 == 1)

            if is_flash:
                y_color = (255, 60, 60)
                y_highlight = (255, 180, 180)
                y_dark = (160, 0, 0)
                y_shadow = (70, 0, 0)
            else:
                y_color = (252, 216, 0)
                y_highlight = (255, 248, 112)
                y_dark = (216, 156, 0)
                y_shadow = (80, 56, 0)

            # Relleno del color base
            radius_bar = corner_r if ((not is_p2 and fill_w == width) or (is_p2 and fill_w == width)) else 2
            pygame.draw.rect(screen, y_color, y_rect, border_radius=radius_bar)

            # Gradientes horizontales auténticos de la barra de vida SF2
            yx = y_rect.x
            yw = y_rect.width
            pygame.draw.line(screen, y_highlight, (yx, y + 2), (yx + yw, y + 2), 2)
            pygame.draw.line(screen, y_dark, (yx, y + height - 5), (yx + yw, y + height - 5), 2)
            pygame.draw.line(screen, y_shadow, (yx, y + height - 2), (yx + yw, y + height - 2), 2)

        # Riel exterior blanco con bordes redondeados
        pygame.draw.rect(screen, COLOR_WHITE, frame_rect, 3, border_radius=corner_r)

    def draw_ko_badge(self, screen, center_x, y=32, width=46, height=32):
        """Dibuja el emblema central 'KO' auténtico."""
        ko_x = center_x - width // 2
        ko_y = y

        # Fondo negro de la caja de KO
        box_rect = pygame.Rect(ko_x, ko_y, width, height)
        pygame.draw.rect(screen, (0, 0, 0), box_rect)
        pygame.draw.rect(screen, (220, 220, 220), box_rect, 2)

        # Renderizar sprite oficial de KO en rojo
        if self.sheet_loaded and self.red_ko:
            spr_scaled = pygame.transform.scale(self.red_ko, (width - 4, height - 4))
            screen.blit(spr_scaled, (ko_x + 2, ko_y + 2))
        elif self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (center_x, ko_y + height // 2 - 2), "KO", scale=0.75, align="center")
        else:
            txt = self.font_small.render("KO", True, COLOR_RED)
            screen.blit(txt, (center_x - txt.get_width() // 2, ko_y + 4))

    def draw_timer(self, screen, seconds_left, center_x, y=68, scale=2.8):
        """Dibuja el temporizador de 99s centrado debajo del KO usando los dígitos oficiales."""
        s_val = max(0, int(seconds_left))
        d_ten = (s_val // 10) % 10
        d_unit = s_val % 10

        if self.sheet_loaded and self.big_digits:
            spr_ten = self.big_digits.get(d_ten)
            spr_unit = self.big_digits.get(d_unit)

            if spr_ten and spr_unit:
                w1, h1 = spr_ten.get_size()
                w2, h2 = spr_unit.get_size()
                sw1, sh1 = int(w1 * scale), int(h1 * scale)
                sw2, sh2 = int(w2 * scale), int(h2 * scale)
                spacing = 2
                tot_w = sw1 + sw2 + spacing

                start_x = center_x - tot_w // 2
                screen.blit(pygame.transform.scale(spr_ten, (sw1, sh1)), (start_x, y))
                screen.blit(pygame.transform.scale(spr_unit, (sw2, sh2)), (start_x + sw1 + spacing, y))
                return

        # Fallback a ArcadeFont o fuente estándar
        t_str = f"{s_val:02d}"
        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (center_x, y + 14), t_str, scale=1.05, align="center")
        else:
            c = COLOR_RED if s_val <= 10 else COLOR_YELLOW
            t_s = self.font_timer.render(t_str, True, c)
            screen.blit(t_s, (center_x - t_s.get_width() // 2, y))

    def draw_character_names(self, screen, player1, player2, p1_x, p2_right_x, y=68):
        """
        Dibuja los nombres de los luchadores directamente debajo de las barras de vida:
        - Si el personaje coincide con los originales de SF2, usa el sprite oficial ripeado.
        - Para los profesores, renderiza con la auténtica tipografía arcade SF2 (ArcadeFont).
        """
        def render_fighter_name(fighter, pos_x, is_right_aligned=False):
            raw_name = getattr(fighter, "name", "PLAYER")
            char_id = getattr(fighter, "char_id", raw_name.lower())

            # Mapeo a sprites originales si aplica
            classic_keys = {
                "ryu": "ryu", "honda": "honda", "blanka": "blanka", "guile": "guile",
                "ken": "ken", "chunli": "chunli", "zangief": "zangief", "dhalsim": "dhalsim",
                "balrog": "balrog", "vega": "vega", "sagat": "sagat", "bison": "bison"
            }
            c_key = classic_keys.get(char_id.lower())

            # 1. Si existe sprite oficial de nombre en la hoja
            if self.sheet_loaded and c_key and c_key in self.names_orange:
                spr = self.names_orange[c_key]
                sw = int(spr.get_width() * 2.8)
                sh = int(spr.get_height() * 2.8)
                scaled = pygame.transform.scale(spr, (sw, sh))
                draw_x = (pos_x - sw) if is_right_aligned else pos_x
                screen.blit(scaled, (draw_x, y))
                return

            # 2. Nombre del profesor en tipografía arcade SF2 (solo apellido o nombre corto)
            parts = raw_name.split()
            short_name = parts[-1].upper() if parts else raw_name.upper()

            if self.arcade_font and self.arcade_font.loaded:
                align = "right" if is_right_aligned else "left"
                self.arcade_font.render_to(screen, (pos_x, y), short_name, scale=0.85, align=align)
            else:
                ns = self.font_medium.render(short_name, True, COLOR_YELLOW)
                draw_x = (pos_x - ns.get_width()) if is_right_aligned else pos_x
                screen.blit(ns, (draw_x, y))

        # Jugador 1 a la izquierda
        render_fighter_name(player1, p1_x, is_right_aligned=False)
        # Jugador 2 a la derecha
        render_fighter_name(player2, p2_right_x, is_right_aligned=True)

    def draw_round_wins(self, screen, p1_wins, p2_wins, p1_x, p2_right_x, y=104):
        """Dibuja los medallones dorados Capcom de victorias por round."""
        radius = 7
        spacing = 20

        # P1 Wins
        for i in range(2):
            cx = p1_x + radius + (i * spacing)
            cy = y
            if i < p1_wins:
                pygame.draw.circle(screen, (255, 215, 0), (cx, cy), radius)
                pygame.draw.circle(screen, COLOR_WHITE, (cx, cy), radius, 2)
                pygame.draw.circle(screen, (255, 255, 200), (cx - 2, cy - 2), 2)
            else:
                pygame.draw.circle(screen, (40, 40, 50), (cx, cy), radius)
                pygame.draw.circle(screen, (120, 120, 130), (cx, cy), radius, 1)

        # P2 Wins (alineados a la derecha)
        for i in range(2):
            cx = p2_right_x - radius - (i * spacing)
            cy = y
            if i < p2_wins:
                pygame.draw.circle(screen, (255, 215, 0), (cx, cy), radius)
                pygame.draw.circle(screen, COLOR_WHITE, (cx, cy), radius, 2)
                pygame.draw.circle(screen, (255, 255, 200), (cx - 2, cy - 2), 2)
            else:
                pygame.draw.circle(screen, (40, 40, 50), (cx, cy), radius)
                pygame.draw.circle(screen, (120, 120, 130), (cx, cy), radius, 1)

    def draw_special_meter(self, screen, fighter, x, y, width=280, height=12, is_p2=False):
        """Dibuja la barra de energía para Ultimate (Special Meter)."""
        ratio = max(0.0, min(1.0, fighter.special_meter / fighter.max_special_meter))

        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (25, 25, 35), bg_rect)
        pygame.draw.rect(screen, (200, 200, 220), bg_rect, 2)

        fill_w = int(width * ratio)
        if fill_w > 0:
            if not is_p2:
                fill_rect = pygame.Rect(x + 1, y + 1, fill_w - 2, height - 2)
            else:
                fill_rect = pygame.Rect(x + width - fill_w + 1, y + 1, fill_w - 2, height - 2)

            color = (255, 215, 0) if ratio >= 1.0 else (40, 180, 255)
            pygame.draw.rect(screen, color, fill_rect)

        if ratio >= 1.0:
            msg = "MAX - SPECIAL READY!"
            if self.arcade_font and self.arcade_font.loaded:
                align = "right" if is_p2 else "left"
                self.arcade_font.render_to(screen, (x + width if is_p2 else x, y + height + 4), msg, scale=0.55, align=align)
            else:
                lbl = self.font_tiny.render(msg, True, (255, 220, 50))
                if not is_p2:
                    screen.blit(lbl, (x, y + height + 2))
                else:
                    screen.blit(lbl, (x + width - lbl.get_width(), y + height + 2))

    def draw_banner(self, screen, text, subtext=None, color=COLOR_YELLOW):
        """
        Dibuja los banners de combate ("ROUND 1", "FIGHT!", "K.O.", etc.):
        - Usa los sprites oficiales extraídos de la hoja de HUD.
        - Fallback elegante a ArcadeFont para textos personalizados.
        """
        w = screen.get_width()
        center_x = w // 2
        center_y = 330
        b_scale = 3.2

        clean_text = text.strip().upper() if text else ""

        # 1. Banner "ROUND X" (Usando sprites oficiales "ROUND" y números)
        if clean_text.startswith("ROUND") and self.sheet_loaded and self.round_word:
            parts = clean_text.split()
            r_num = 1
            if len(parts) >= 2 and parts[1].isdigit():
                r_num = int(parts[1])

            num_spr = self.round_nums.get(r_num, self.round_nums.get(1))
            rw = self.round_word.get_width()
            rh = self.round_word.get_height()
            nw = num_spr.get_width() if num_spr else 0

            spacing = 6
            tot_w = int((rw + spacing + nw) * b_scale)
            tot_h = int(rh * b_scale)
            start_x = center_x - tot_w // 2
            start_y = center_y - tot_h // 2

            screen.blit(pygame.transform.scale(self.round_word, (int(rw * b_scale), tot_h)), (start_x, start_y))
            if num_spr:
                screen.blit(
                    pygame.transform.scale(num_spr, (int(nw * b_scale), tot_h)),
                    (start_x + int((rw + spacing) * b_scale), start_y)
                )

            # Subtexto si aplica (ej. "START !")
            if subtext:
                if self.arcade_font and self.arcade_font.loaded:
                    self.arcade_font.render_to(screen, (center_x, start_y + tot_h + 16), subtext, scale=0.85, align="center")
                else:
                    sub_s = self.font_medium.render(subtext, True, COLOR_WHITE)
                    screen.blit(sub_s, (center_x - sub_s.get_width() // 2, start_y + tot_h + 10))
            return

        # 2. Banner "FIGHT!" (Usando sprite oficial "FIGHT!")
        if clean_text == "FIGHT!" and self.sheet_loaded and self.fight_word:
            fw = self.fight_word.get_width()
            fh = self.fight_word.get_height()
            sw = int(fw * b_scale)
            sh = int(fh * b_scale)
            screen.blit(pygame.transform.scale(self.fight_word, (sw, sh)), (center_x - sw // 2, center_y - sh // 2))
            return

        # 3. Banner "K.O."
        if clean_text in ("K.O.", "K. O.", "KO") and self.sheet_loaded and self.red_ko:
            kw = self.red_ko.get_width()
            kh = self.red_ko.get_height()
            sw = int(kw * 5.0)
            sh = int(kh * 5.0)
            screen.blit(pygame.transform.scale(self.red_ko, (sw, sh)), (center_x - sw // 2, center_y - sh // 2))
            if subtext:
                if self.arcade_font and self.arcade_font.loaded:
                    self.arcade_font.render_to(screen, (center_x, center_y + sh // 2 + 16), subtext, scale=0.85, align="center")
                else:
                    sub_s = self.font_medium.render(subtext, True, COLOR_WHITE)
                    screen.blit(sub_s, (center_x - sub_s.get_width() // 2, center_y + sh // 2 + 10))
            return

        # 4. Otros banners ("YOU WIN", "YOU LOSE", "TIME OVER", etc.) vía ArcadeFont
        overlay = pygame.Surface((w, 140), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 270))

        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (center_x, 315), clean_text, scale=1.4, align="center")
            if subtext:
                self.arcade_font.render_to(screen, (center_x, 375), subtext, scale=0.75, align="center")
        else:
            txt_surf = self.font_large.render(clean_text, True, color)
            screen.blit(txt_surf, (center_x - txt_surf.get_width() // 2, 290))
            if subtext:
                sub_surf = self.font_medium.render(subtext, True, COLOR_WHITE)
                screen.blit(sub_surf, (center_x - sub_surf.get_width() // 2, 365))

    def draw(self, screen, player1, player2, timer_seconds, p1_wins, p2_wins, match_banner=None):
        """Renderiza el HUD completo del combate adaptándose simétricamente a la resolución activa."""
        self.anim_tick += 1

        w = screen.get_width()
        center_x = w // 2

        # Dimensiones arcade SF2 calibradas
        ko_w = 46
        ko_h = 32
        bar_h = 24
        bar_w = int(w * 0.395)  # En 960px: 379px. En 1280px: 505px
        margin_x = center_x - (ko_w // 2) - bar_w
        p1_bar_x = margin_x
        p2_bar_x = center_x + (ko_w // 2)
        p2_right_x = p2_bar_x + bar_w
        bar_y = 36

        # 1. Puntuaciones superiores (1P, HI, 2P)
        self.draw_scores(screen, margin_x=margin_x, y=10)

        # 2. Barras de salud (P1 a la izquierda, P2 a la derecha)
        self.draw_health_bar(screen, player1, x=p1_bar_x, y=bar_y, width=bar_w, height=bar_h, is_p2=False)
        self.draw_health_bar(screen, player2, x=p2_bar_x, y=bar_y, width=bar_w, height=bar_h, is_p2=True)

        # 3. Logotipo central KO
        self.draw_ko_badge(screen, center_x=center_x, y=bar_y - 4, width=ko_w, height=ko_h)

        # 4. Temporizador centrado debajo del KO
        self.draw_timer(screen, timer_seconds, center_x=center_x, y=bar_y + bar_h + 6)

        # 5. Nombres de personajes alineados debajo de las barras
        self.draw_character_names(screen, player1, player2, p1_x=p1_bar_x, p2_right_x=p2_right_x, y=bar_y + bar_h + 6)

        # 6. Medallones de rounds ganados
        self.draw_round_wins(screen, p1_wins, p2_wins, p1_x=p1_bar_x, p2_right_x=p2_right_x, y=104)

        # 7. Barras de Special Meter (Ultimate)
        meter_w = int(bar_w * 0.72)
        self.draw_special_meter(screen, player1, x=p1_bar_x, y=124, width=meter_w, height=12, is_p2=False)
        self.draw_special_meter(screen, player2, x=p2_right_x - meter_w, y=124, width=meter_w, height=12, is_p2=True)

        # 8. Banners de combate ("ROUND 1", "FIGHT!", "K.O.", etc.)
        if match_banner:
            self.draw_banner(
                screen,
                match_banner[0],
                match_banner[1] if len(match_banner) > 1 else None,
                match_banner[2] if len(match_banner) > 2 else COLOR_YELLOW
            )
