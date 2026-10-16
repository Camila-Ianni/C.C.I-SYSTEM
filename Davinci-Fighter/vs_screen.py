"""
vs_screen.py - Pantalla oficial de VS y Secuencia de Vuelo de Avión de Street Fighter II.
Recrea con máxima fidelidad arcade la secuencia pre-combate de Street Fighters.mov:
- Mapa mundial con pines de origen (P1) y destino (P2).
- Retratos de combate y tarjetas de enfrentamiento de ambos profesores.
- Logotipo 'VS' gigante con destello dorado central.
- Animación fluida de vuelo de avión con rotación dinámica y trazado de ruta de puntos rojos.
- Sincronización de audio: drone continuo de avión en bucle y explosión de impacto 'VS' al aterrizar.
- Transición automática al escenario de combate.
"""

import os
import math
import pygame
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_WHITE,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BG,
    COLOR_GREEN,
    FPS,
    ARCADE_WIDTH,
    ARCADE_HEIGHT,
    PILLARBOX_OFFSET_X,
)
from character_data import get_character_data
from character_select import CHARACTER_LOCATIONS
from audio_manager import audio_manager
from arcade_font import get_arcade_font


class VSScreen:
    """
    Pantalla de enfrentamiento VS y cutscene animada de vuelo sobre el mapa mundial.
    """
    def __init__(self, screen, p1_char="carloni", p2_char="cavasso"):
        self.screen = screen
        self.p1_char = p1_char
        self.p2_char = p2_char
        self.p1_data = get_character_data(p1_char)
        self.p2_data = get_character_data(p2_char)

        self.p1_loc = CHARACTER_LOCATIONS.get(p1_char, {"country": "JAPÓN", "flag": "🇯🇵", "map_pos": (1040, 260)})
        self.p2_loc = CHARACTER_LOCATIONS.get(p2_char, {"country": "EE. UU.", "flag": "🇺🇸", "map_pos": (300, 250)})

        self.start_pos = self.p1_loc["map_pos"]
        self.end_pos = self.p2_loc["map_pos"]

        self.arcade_font = get_arcade_font()
        self.font_vs = pygame.font.Font(None, 120)
        self.font_title = pygame.font.Font(None, 44)
        self.font_name = pygame.font.Font(None, 34)
        self.font_info = pygame.font.Font(None, 24)
        self.font_tag = pygame.font.Font(None, 20)

        # Estados de la cutscene: "takeoff", "flying", "landed", "hold", "finished"
        self.state = "takeoff"
        self.state_time = 0.0
        self.flight_duration = 2.4  # Segundos de vuelo de avión
        self.flight_progress = 0.0
        self.plane_pos = self.start_pos
        self.plane_angle = 0.0
        self.trajectory_points = []
        self._generate_trajectory()

        # Efectos visuales de impacto
        self.impact_flash = 0.0
        self.shake_offset = (0, 0)
        self.landed_sound_played = False
        self.finished = False

        # Superficie de avión en sprite
        self.plane_surf = self._create_plane_surface()

        # Cargar fondo de mapa mundial centrado en formato arcade 4:3 con laterales negros
        self.bg_image = None
        bg_path = os.path.join("assets", "backgrounds", "MAP.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "backgrounds", "player select.png")
        if os.path.exists(bg_path):
            try:
                raw_bg = pygame.image.load(bg_path)
                scaled_43 = pygame.transform.scale(raw_bg, (ARCADE_WIDTH, ARCADE_HEIGHT))
                self.bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                self.bg_image.fill((0, 0, 0))
                self.bg_image.blit(scaled_43, (PILLARBOX_OFFSET_X, 0))
            except Exception as e:
                print(f"[VSScreen] Error cargando fondo: {e}")

        # Iniciar drone continuo de avión
        audio_manager.start_airplane_drone()

    def _create_plane_surface(self, size=44):
        """Genera el sprite procedural del avión estilo Street Fighter II."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # Fuselaje blanco
        pygame.draw.polygon(surf, (245, 245, 245), [(42, 22), (8, 15), (2, 22), (8, 29)])
        # Alas
        pygame.draw.polygon(surf, (220, 220, 220), [(24, 22), (16, 2), (22, 2), (30, 22)])
        pygame.draw.polygon(surf, (200, 200, 200), [(24, 22), (16, 42), (22, 42), (30, 22)])
        # Alerones rojos
        pygame.draw.polygon(surf, (235, 40, 40), [(6, 22), (0, 8), (4, 8), (10, 22)])
        pygame.draw.polygon(surf, (235, 40, 40), [(6, 22), (0, 36), (4, 36), (10, 22)])
        # Contorno oscuro
        pygame.draw.polygon(surf, (30, 30, 30), [(42, 22), (8, 15), (2, 22), (8, 29)], 2)
        return surf

    def _generate_trajectory(self):
        """Genera una parábola suave de waypoints entre origen y destino."""
        p1_x, p1_y = self.start_pos
        p2_x, p2_y = self.end_pos

        num_pts = 40
        self.trajectory_points = []
        for i in range(num_pts + 1):
            t = i / float(num_pts)
            # Interpolación lineal + elevación en arco
            cur_x = p1_x + (p2_x - p1_x) * t
            # Arco parábolico vertical (hasta 60px de elevación en el cenit)
            arch = -70.0 * 4.0 * t * (1.0 - t)
            cur_y = p1_y + (p2_y - p1_y) * t + arch
            self.trajectory_points.append((cur_x, cur_y))

    def handle_input(self, event):
        """Permite saltar la animación del VS presionando cualquier tecla."""
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.finish()
            return "fight"
        return None

    def update(self, dt=1.0 / FPS):
        """Actualiza la posición del avión, rotación y efectos de impacto."""
        if self.finished:
            return "fight"

        self.state_time += dt

        if self.state in ("takeoff", "flying"):
            self.flight_progress = min(1.0, self.flight_progress + dt / self.flight_duration)
            
            # Calcular posición en la trayectoria
            exact_idx = self.flight_progress * (len(self.trajectory_points) - 1)
            idx0 = int(exact_idx)
            idx1 = min(len(self.trajectory_points) - 1, idx0 + 1)
            frac = exact_idx - idx0

            x0, y0 = self.trajectory_points[idx0]
            x1, y1 = self.trajectory_points[idx1]
            cur_x = x0 + (x1 - x0) * frac
            cur_y = y0 + (y1 - y0) * frac
            self.plane_pos = (cur_x, cur_y)

            # Calcular ángulo de orientación del avión hacia el siguiente punto
            dx = x1 - x0
            dy = y1 - y0
            if math.hypot(dx, dy) > 0.001:
                # -math.degrees porque el eje Y en pantalla va hacia abajo
                self.plane_angle = -math.degrees(math.atan2(dy, dx))

            if self.flight_progress >= 1.0:
                self.state = "landed"
                self.state_time = 0.0
                if not self.landed_sound_played:
                    self.landed_sound_played = True
                    audio_manager.play_vs_impact()
                    self.impact_flash = 1.0

        elif self.state == "landed":
            # Efecto de flash blanco y temblor de pantalla durante 0.3s
            if self.impact_flash > 0:
                self.impact_flash = max(0.0, self.impact_flash - dt * 3.5)
                # Shake
                self.shake_offset = (
                    int(math.sin(self.state_time * 50) * 8 * self.impact_flash),
                    int(math.cos(self.state_time * 60) * 8 * self.impact_flash),
                )
            else:
                self.shake_offset = (0, 0)

            # Mantener la pantalla de enfrentamiento por 1.2s antes de iniciar el combate
            if self.state_time >= 1.2:
                self.state = "finished"
                self.finished = True
                return "fight"

        return None

    def finish(self):
        """Finaliza inmediatamente la cutscene y detiene el audio."""
        self.finished = True
        audio_manager.stop_airplane_drone()

    def draw(self, screen=None):
        """Renderiza la pantalla completa de VS con avión y trazado de ruta."""
        target = screen or self.screen
        if target is None:
            return

        render_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # 1. Fondo del mapa mundial
        if self.bg_image:
            render_surf.blit(self.bg_image, (0, 0))
        else:
            render_surf.fill(COLOR_BG)

        # Oscurecer ligeramente el mapa para destacar a los luchadores y la ruta
        dim_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 15, 110))
        render_surf.blit(dim_overlay, (0, 0))

        # 2. Marcadores de Origen y Destino en el Mapa
        p1_x, p1_y = self.start_pos
        p2_x, p2_y = self.end_pos

        # Pin Origen P1 (Rojo pulsante)
        pygame.draw.circle(render_surf, (255, 50, 50), (int(p1_x), int(p1_y)), 10)
        pygame.draw.circle(render_surf, COLOR_WHITE, (int(p1_x), int(p1_y)), 10, 2)
        tag_p1 = self.font_tag.render(self.p1_loc["country"], True, COLOR_WHITE)
        render_surf.blit(tag_p1, (int(p1_x) - tag_p1.get_width() // 2, int(p1_y) + 14))

        # Pin Destino P2 (Azul pulsante)
        pygame.draw.circle(render_surf, (50, 130, 255), (int(p2_x), int(p2_y)), 10)
        pygame.draw.circle(render_surf, COLOR_WHITE, (int(p2_x), int(p2_y)), 10, 2)
        tag_p2 = self.font_tag.render(self.p2_loc["country"], True, COLOR_WHITE)
        render_surf.blit(tag_p2, (int(p2_x) - tag_p2.get_width() // 2, int(p2_y) + 14))

        # 3. Trazado de la ruta de puntos (Dotted Flight Path)
        pts_drawn = int(self.flight_progress * len(self.trajectory_points))
        for i in range(pts_drawn):
            pt_x, pt_y = self.trajectory_points[i]
            # Puntos rojos brillantes con borde blanco
            pygame.draw.circle(render_surf, (255, 60, 60), (int(pt_x), int(pt_y)), 4)
            if i % 3 == 0:
                pygame.draw.circle(render_surf, COLOR_YELLOW, (int(pt_x), int(pt_y)), 2)

        # 4. Avión volando con rotación
        if self.plane_surf:
            rotated_plane = pygame.transform.rotate(self.plane_surf, self.plane_angle)
            p_rect = rotated_plane.get_rect(center=(int(self.plane_pos[0]), int(self.plane_pos[1])))
            render_surf.blit(rotated_plane, p_rect)

        # 5. Tarjetas laterales de los luchadores P1 y P2
        self._draw_fighter_vs_card(render_surf, self.p1_data, self.p1_loc, is_p1=True)
        self._draw_fighter_vs_card(render_surf, self.p2_data, self.p2_loc, is_p1=False)

        # 6. Emblema Central 'VS'
        self._draw_vs_emblem(render_surf)

        # 7. Flash blanco de impacto al llegar
        if self.impact_flash > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = int(255 * self.impact_flash)
            flash_surf.fill((255, 255, 255, alpha))
            render_surf.blit(flash_surf, (0, 0))

        # 8. Asegurar franjas negras laterales arcade 4:3 (Pillarbox)
        if PILLARBOX_OFFSET_X > 0:
            pygame.draw.rect(render_surf, (0, 0, 0), (0, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))
            pygame.draw.rect(render_surf, (0, 0, 0), (PILLARBOX_OFFSET_X + ARCADE_WIDTH, 0, PILLARBOX_OFFSET_X, SCREEN_HEIGHT))

        # Blit final a la pantalla con temblor si aplica
        target.blit(render_surf, self.shake_offset)

    def _draw_fighter_vs_card(self, screen, data, loc, is_p1=True):
        """Dibuja la tarjeta del profesor a la izquierda o derecha dentro del formato arcade 4:3."""
        card_w = 260
        card_h = 380
        x = PILLARBOX_OFFSET_X + 25 if is_p1 else (PILLARBOX_OFFSET_X + ARCADE_WIDTH - card_w - 25)
        y = 160

        card_rect = pygame.Rect(x, y, card_w, card_h)
        # Fondo
        bg_card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_card.fill((10, 15, 30, 235))
        screen.blit(bg_card, (x, y))

        color_border = (255, 60, 60) if is_p1 else (60, 130, 255)
        pygame.draw.rect(screen, color_border, card_rect, 4, border_radius=8)

        # Banner 1P / 2P
        header_text = "PLAYER 1" if is_p1 else "PLAYER 2"
        lbl_head = self.font_title.render(header_text, True, color_border)
        screen.blit(lbl_head, (x + card_w // 2 - lbl_head.get_width() // 2, y + 15))

        # Retrato
        portrait_rect = pygame.Rect(x + 20, y + 60, card_w - 40, 180)
        pygame.draw.rect(screen, data["color"], portrait_rect)
        pygame.draw.rect(screen, COLOR_WHITE, portrait_rect, 2)

        # Nombre del Profesor en fuente SF2 arcade
        first_name = data["name"].split()[0].upper()
        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (x + card_w // 2, y + 265), first_name, scale=0.8, align="center")
        else:
            name_surf = self.font_name.render(first_name, True, COLOR_YELLOW)
            screen.blit(name_surf, (x + card_w // 2 - name_surf.get_width() // 2, y + 255))

        # Bandera y País
        flag_str = f"{loc.get('country', '')} {loc.get('flag', '')}"
        flag_surf = self.font_info.render(flag_str, True, COLOR_WHITE)
        screen.blit(flag_surf, (x + card_w // 2 - flag_surf.get_width() // 2, y + 295))

        # Cita de combate en fuente arcade SF2
        quote_text = data.get("quote", "")[:28]
        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (x + card_w // 2, y + 338), f'"{quote_text}"', scale=0.55, align="center")
        else:
            quote_surf = self.font_tag.render(f'"{quote_text}"', True, (220, 220, 180))
            screen.blit(quote_surf, (x + card_w // 2 - quote_surf.get_width() // 2, y + 335))

    def _draw_vs_emblem(self, screen):
        """Renderiza el logotipo 'VS' arcade en el centro de la pantalla."""
        center_x = SCREEN_WIDTH // 2
        center_y = 350

        # Destello de rayos arcade en el fondo del VS
        for angle_deg in range(0, 360, 30):
            rad = math.radians(angle_deg + self.state_time * 40)
            x_end = center_x + math.cos(rad) * 90
            y_end = center_y + math.sin(rad) * 90
            pygame.draw.line(screen, (80, 50, 20), (center_x, center_y), (x_end, y_end), 2)

        # Círculo contenedor
        pygame.draw.circle(screen, (30, 20, 10), (center_x, center_y), 65)
        pygame.draw.circle(screen, COLOR_YELLOW, (center_x, center_y), 65, 4)

        # Texto 'VS' en tipografía arcade SF2
        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (center_x, center_y), "VS", scale=2.2, align="center")
        else:
            vs_shadow = self.font_vs.render("VS", True, (160, 20, 20))
            vs_surf = self.font_vs.render("VS", True, COLOR_YELLOW)
            screen.blit(vs_shadow, (center_x - vs_shadow.get_width() // 2 + 4, center_y - vs_shadow.get_height() // 2 + 4))
            screen.blit(vs_surf, (center_x - vs_surf.get_width() // 2, center_y - vs_surf.get_height() // 2))
