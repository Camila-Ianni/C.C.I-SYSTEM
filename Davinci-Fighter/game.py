import sys
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, GROUND_Y, COLOR_GROUND_LINE,
    COLOR_RED, COLOR_YELLOW, COLOR_GREEN, MODE_PVP, MODE_PVAI, COLOR_WHITE,
    ARCADE_WIDTH, ARCADE_HEIGHT, PILLARBOX_OFFSET_X
)
from stage_manager import stage_manager, STAGE_WIDTH
from player import Player
from enemy_ai import EnemyAI
from collision import CollisionManager
from hud import HUD
from effects import effect_manager
from audio_manager import audio_manager

class GameState:
    START_ROUND = "start_round"
    FIGHTING = "fighting"
    ROUND_ENDED = "round_ended"
    MATCH_OVER = "match_over"


class Game:
    """
    Clase principal que administra el combate (PVP o PVAI) con scrolling horizontal de cámara (2200px)
    y animaciones de público de fondo.
    """
    def __init__(self, screen, p1_char="carloni", p2_char="cavasso", game_mode=MODE_PVAI, stage_id=None):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_paused = False

        # Configuración
        self.p1_char = p1_char
        self.p2_char = p2_char
        self.game_mode = MODE_PVAI if str(game_mode).lower() in (MODE_PVAI, "1p", "single", "cpu", "ai") else MODE_PVP
        self.stage_id = stage_id

        # Cargar el escenario: si se especificó stage_id, usarlo; de lo contrario por oponente P2
        if self.stage_id:
            self.stage = stage_manager.get_stage_for_country(self.stage_id) if self.stage_id in ("usa", "japan", "thailand", "brazil", "spain", "india", "dhalsim", "china", "chunli", "ussr", "urss", "russia", "zangief", "ken", "usa_ken", "harbor", "port", "honda", "japan_up", "romero", "bathhouse", "sento", "ehonda", "guile", "cavasso", "airbase", "hangar", "usa_guile", "usa_up", "balrog", "vegas", "las_vegas") else stage_manager.get_stage_for_character(self.stage_id)
        else:
            self.stage = stage_manager.get_stage_for_character(self.p2_char)

        # HUD y Cámara Arcade 4:3
        self.hud = HUD()
        self.camera_x = 0
        self.viewport_w = ARCADE_WIDTH
        self.viewport_h = ARCADE_HEIGHT
        self.offset_x = PILLARBOX_OFFSET_X

        # Inicialización de luchadores P1 (x=800) y P2 (x=1300) en el mundo de 2200px
        self.player1 = Player(x=800, y=GROUND_Y - 140, char_id=self.p1_char, player_id=1)
        self.player2 = Player(x=1300, y=GROUND_Y - 140, char_id=self.p2_char, player_id=2)

        # Controlador de IA si el modo es Player vs AI
        self.ai_controller = None
        if self.game_mode == MODE_PVAI:
            self.ai_controller = EnemyAI(self.player2, self.player1)

        # Sistema de Rounds y Temporizador
        self.p1_wins = 0
        self.p2_wins = 0
        self.current_round = 1
        self.timer = 99.0

        # Estado del combate
        self.game_state = GameState.START_ROUND
        self.state_timer = 0
        self.banner_info = None

        music_key = self.stage_id if self.stage_id else self.p2_char
        audio_manager.play_stage_music(music_key)

    def reset_round(self):
        """Restablece posiciones en el mapa expandido, vida y temporizador para el siguiente round."""
        self.player1.x = 800
        self.player1.y = GROUND_Y - 140
        self.player1.health = self.player1.max_health
        self.player1.set_state("idle")
        self.player1.facing_right = True

        self.player2.x = 1300
        self.player2.y = GROUND_Y - 140
        self.player2.health = self.player2.max_health
        self.player2.set_state("idle")
        self.player2.facing_right = False

        self.timer = 99.0
        self.game_state = GameState.START_ROUND
        self.state_timer = 0
        if hasattr(self.stage, "reset"):
            self.stage.reset()

    def update_camera_and_bounds(self):
        """
        Calcula el desplazamiento horizontal de la cámara (camera_x) siguiendo el punto medio entre los dos jugadores
        y restringe que no se alejen más del ancho de la pantalla arcade visible (viewport_w = 960).
        """
        # Restricción de distancia máxima entre luchadores
        max_dist = self.viewport_w - 140
        dist = self.player2.x - self.player1.x
        if dist > max_dist:
            mid = (self.player1.x + self.player2.x) / 2
            self.player1.x = mid - max_dist / 2
            self.player2.x = mid + max_dist / 2
        elif dist < -max_dist:
            mid = (self.player1.x + self.player2.x) / 2
            self.player2.x = mid - max_dist / 2
            self.player1.x = mid + max_dist / 2

        # Calcular posición objetivo de la cámara centrada entre ambos jugadores
        mid_x = (self.player1.rect.centerx + self.player2.rect.centerx) // 2
        target_camera_x = mid_x - (self.viewport_w // 2)

        # Clampear la cámara dentro del límite del escenario (0 a STAGE_WIDTH - viewport_w)
        max_camera_x = max(0, STAGE_WIDTH - self.viewport_w)
        self.camera_x = max(0, min(max_camera_x, target_camera_x))

        # Mantener a los luchadores dentro de los bordes visibles de la pantalla de combate
        min_p_x = self.camera_x + 10
        max_p_x = self.camera_x + self.viewport_w - 10
        if self.player1.x < min_p_x:
            self.player1.x = min_p_x
        elif self.player1.x + self.player1.width > max_p_x:
            self.player1.x = max_p_x - self.player1.width
        self.player1.rect.x = int(self.player1.x)

        if self.player2.x < min_p_x:
            self.player2.x = min_p_x
        elif self.player2.x + self.player2.width > max_p_x:
            self.player2.x = max_p_x - self.player2.width
        self.player2.rect.x = int(self.player2.x)

    def handle_events(self):
        """Procesa los eventos de entrada de Pygame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_paused = not self.is_paused

        if not self.is_paused and self.game_state == GameState.FIGHTING:
            self.player1.handle_input()
            if self.game_mode == MODE_PVP:
                self.player2.handle_input()

        return None

    def update(self):
        """Actualiza la lógica del juego, cámara, físicas y público animado."""
        if self.is_paused:
            return

        self.player1.face_target(self.player2)
        self.player2.face_target(self.player1)

        # Actualizar animaciones del público de fondo y efectos interactivos
        self.stage.update(players=[self.player1, self.player2])
        effect_manager.update()

        if self.game_state == GameState.START_ROUND:
            self.state_timer += 1
            if self.state_timer < 90:
                self.banner_info = (f"ROUND {self.current_round}", "START !", COLOR_YELLOW)
            elif self.state_timer < 140:
                self.banner_info = ("FIGHT!", None, COLOR_RED)
            else:
                self.banner_info = None
                self.game_state = GameState.FIGHTING
                self.state_timer = 0

            self.player1.update()
            self.player2.update()
            self.update_camera_and_bounds()

        elif self.game_state == GameState.FIGHTING:
            self.timer -= 1.0 / FPS
            if self.timer <= 0:
                self.timer = 0
                self.game_state = GameState.ROUND_ENDED
                self.state_timer = 0

            if self.ai_controller:
                self.ai_controller.update()

            self.player1.update()
            self.player2.update()
            self.update_camera_and_bounds()

            CollisionManager.check_attack_collision(self.player1, self.player2)
            CollisionManager.check_attack_collision(self.player2, self.player1)

            if self.player1.health <= 0 or self.player2.health <= 0:
                self.game_state = GameState.ROUND_ENDED
                self.state_timer = 0

        elif self.game_state == GameState.ROUND_ENDED:
            self.state_timer += 1
            self.player1.update()
            self.player2.update()
            self.update_camera_and_bounds()

            if self.state_timer == 1:
                if self.player1.health > self.player2.health:
                    self.p1_wins += 1
                    self.banner_info = ("K. O.", f"{self.player1.name.upper()} WINS ROUND", COLOR_YELLOW)
                elif self.player2.health > self.player1.health:
                    self.p2_wins += 1
                    self.banner_info = ("K. O.", f"{self.player2.name.upper()} WINS ROUND", COLOR_YELLOW)
                else:
                    self.banner_info = ("TIME OVER", "DRAW ROUND", COLOR_YELLOW)

            if self.state_timer >= 150:
                if self.p1_wins >= 2:
                    self.game_state = GameState.MATCH_OVER
                    self.banner_info = ("YOU WIN", f"{self.player1.name.upper()} WINS", COLOR_GREEN)
                    audio_manager.play_music("victory")
                elif self.p2_wins >= 2:
                    self.game_state = GameState.MATCH_OVER
                    win_label = "YOU LOSE" if self.game_mode == MODE_PVAI else "YOU WIN"
                    self.banner_info = (win_label, f"{self.player2.name.upper()} WINS", COLOR_RED)
                    audio_manager.play_music("victory")
                else:
                    self.current_round += 1
                    self.reset_round()

        elif self.game_state == GameState.MATCH_OVER:
            self.state_timer += 1
            self.player1.update()
            self.player2.update()
            self.update_camera_and_bounds()

    def draw_victory_screen(self, screen):
        """Dibuja la pantalla de victoria y burla final (After-fight taunt) con la fuente SF2."""
        vw = screen.get_width()
        vh = screen.get_height()
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 225))
        screen.blit(overlay, (0, 0))

        winner = self.player1 if self.p1_wins >= self.p2_wins else self.player2
        loser = self.player2 if winner == self.player1 else self.player1
        is_p1_winner = (winner == self.player1)

        from arcade_font import get_arcade_font
        af = get_arcade_font()

        # Marco central decorativo dorado
        box_rect = pygame.Rect(80, 80, vw - 160, vh - 160)
        pygame.draw.rect(screen, (30, 30, 45), box_rect)
        pygame.draw.rect(screen, COLOR_YELLOW, box_rect, 4, border_radius=6)

        # Título de Victoria
        title_text = "YOU WIN !" if (is_p1_winner or self.game_mode == MODE_PVP) else "YOU LOSE !"
        if af and af.loaded:
            af.render_to(screen, (vw // 2, 140), title_text, scale=1.6, align="center")
            # Nombre del Ganador
            af.render_to(screen, (vw // 2, 200), f"WINNER: {winner.name.upper()}", scale=0.9, align="center")
        else:
            font_t = pygame.font.Font(None, 64)
            t_s = font_t.render(title_text, True, COLOR_YELLOW)
            screen.blit(t_s, (vw // 2 - t_s.get_width() // 2, 120))

        # Cita de combate (After-Fight Taunt) en fuente arcade grande SF2
        quote_text = getattr(winner, "quote", "PERFECT VICTORY!")
        quote_box = pygame.Rect(120, 270, vw - 240, 150)
        pygame.draw.rect(screen, (20, 20, 30), quote_box)
        pygame.draw.rect(screen, (120, 120, 140), quote_box, 2, border_radius=4)

        if af and af.loaded:
            # Dividir cita si es larga
            words = quote_text.split()
            line1, line2 = "", ""
            for w in words:
                if len(line1 + " " + w) < 32 and not line2:
                    line1 = f"{line1} {w}".strip()
                else:
                    line2 = f"{line2} {w}".strip()

            af.render_to(screen, (vw // 2, 320), f'"{line1}"', scale=0.8, align="center")
            if line2:
                af.render_to(screen, (vw // 2, 365), f'"{line2}"', scale=0.8, align="center")
        else:
            font_q = pygame.font.Font(None, 32)
            q_s = font_q.render(f'"{quote_text}"', True, COLOR_WHITE)
            screen.blit(q_s, (vw // 2 - q_s.get_width() // 2, 330))

        # Indicador de continuar (parpadeo)
        if (self.state_timer // 20) % 2 == 0:
            prompt = "PRESS ANY KEY TO CONTINUE"
            if af and af.loaded:
                af.render_to(screen, (vw // 2, 470), prompt, scale=0.7, align="center")
            else:
                font_c = pygame.font.Font(None, 28)
                c_s = font_c.render(prompt, True, COLOR_YELLOW)
                screen.blit(c_s, (vw // 2 - c_s.get_width() // 2, 470))

    def draw(self):
        """Dibuja el combate dentro del formato arcade 4:3 (960x720) con franjas negras laterales (160px)."""
        shake_x, shake_y = effect_manager.get_shake_offset()

        render_surface = pygame.Surface((self.viewport_w, self.viewport_h))

        # Renderizar escenario expandido con desplazamiento de cámara
        self.stage.draw(render_surface, self.camera_x)
        pygame.draw.line(render_surface, COLOR_GROUND_LINE, (0, GROUND_Y), (self.viewport_w, GROUND_Y), 2)

        # Renderizar luchadores y efectos con desplazamiento de cámara
        self.player1.draw(render_surface, self.camera_x)
        self.player2.draw(render_surface, self.camera_x)

        effect_manager.draw(render_surface, self.camera_x)

        # Renderizar elementos de primer plano (cercas, etc.) frente a los luchadores
        if hasattr(self.stage, "draw_foreground"):
            self.stage.draw_foreground(render_surface, self.camera_x)

        # HUD (fijo en pantalla arcade de 960px)
        self.hud.draw(
            render_surface,
            self.player1,
            self.player2,
            timer_seconds=self.timer,
            p1_wins=self.p1_wins,
            p2_wins=self.p2_wins,
            match_banner=self.banner_info
        )

        # Si el combate finalizó y pasaron los primeros frames de banner, mostrar pantalla de victoria
        if self.game_state == GameState.MATCH_OVER and self.state_timer > 90:
            self.draw_victory_screen(render_surface)

        if self.is_paused:
            overlay = pygame.Surface((self.viewport_w, self.viewport_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            render_surface.blit(overlay, (0, 0))

            font_pause = pygame.font.Font(None, 72)
            font_sub = pygame.font.Font(None, 36)

            p_surf = font_pause.render("JUEGO EN PAUSA", True, COLOR_YELLOW)
            sub_surf = font_sub.render("Presiona ESC para continuar", True, COLOR_WHITE)

            render_surface.blit(p_surf, (self.viewport_w // 2 - p_surf.get_width() // 2, 280))
            render_surface.blit(sub_surf, (self.viewport_w // 2 - sub_surf.get_width() // 2, 370))

        # Blit a la pantalla centrada (1280x720) con efecto de screen shake
        self.screen.blit(render_surface, (self.offset_x + shake_x, shake_y))

        # Dibujar barras negras laterales opacas (Pillarbox arcade)
        if self.offset_x > 0:
            pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, self.offset_x, SCREEN_HEIGHT))
            pygame.draw.rect(self.screen, (0, 0, 0), (self.offset_x + self.viewport_w, 0, self.offset_x, SCREEN_HEIGHT))

        pygame.display.flip()

    def run(self):
        """Ejecuta el ciclo de combate y retorna la acción al finalizar."""
        while self.running:
            res = self.handle_events()
            if res == "exit":
                return "menu"
            
            # En pantalla de victoria, cualquier tecla vuelve al menú
            if self.game_state == GameState.MATCH_OVER and self.state_timer > 120:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                        return "menu"

            self.update()
            self.draw()
            self.clock.tick(FPS)
        return "menu"
