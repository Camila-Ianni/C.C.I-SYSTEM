"""
states.py - Gestor de Estados y Clases de Estado para C.C.I. System.
Arquitectura de Máquina de Estados (State Machine) para la consola virtual.

Estados soportados:
- BootState: Reproducción fluida de CCI_INTRO.mp4 con OpenCV y Pygame.
- IntroAvatarState: Reproducción cinematográfica de intro_cami.mp4.
- MenuState: Pantalla interactiva estilo arcade retro para selección de juegos.
- PlayingState: Aislamiento, ejecución en la misma ventana y retorno seguro de los juegos.
"""

import os
import sys
import math
import time
import cv2
import pygame

# Dimensiones base del sistema virtual
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720


class BaseState:
    """Clase base abstracta para todos los estados de la máquina de estados."""
    def __init__(self, state_machine):
        self.state_machine = state_machine

    def enter(self):
        """Se ejecuta al ingresar al estado."""
        pass

    def exit(self):
        """Se ejecuta al salir del estado."""
        pass

    def handle_events(self, events):
        """Procesa la lista de eventos de Pygame en el frame actual."""
        pass

    def update(self, dt):
        """Actualiza la lógica interna del estado."""
        pass

    def draw(self, screen):
        """Dibuja en la superficie principal de Pygame."""
        pass


class VideoState(BaseState):
    """
    Estado genérico de reproducción de video sincronizado usando OpenCV.
    - Sincroniza FPS mediante cv2.CAP_PROP_FPS y cálculo de tiempo transcurrido (clock / time.perf_counter).
    - Convierte fotogramas BGR de OpenCV a superficies RGB de Pygame.
    - Soporta escalado fluido manteniendo el aspecto y centrado en pantalla.
    - Permite omitir (skip) con ENTER o ESPACIO hacia el estado deseado.
    """
    def __init__(self, state_machine, video_path, next_state_name, allow_skip=True):
        super().__init__(state_machine)
        self.video_path = video_path
        self.next_state_name = next_state_name
        self.allow_skip = allow_skip
        
        self.cap = None
        self.fps = 30.0
        self.frame_delay = 1.0 / 30.0
        self.current_surface = None
        self.is_finished = False
        self.start_time = 0.0
        self.frame_count = 0

    def enter(self):
        self.is_finished = False
        self.current_surface = None
        self.frame_count = 0

        if not os.path.exists(self.video_path):
            print(f"[VideoState] ADVERTENCIA: Video '{self.video_path}' no encontrado. Saltando estado.")
            self.state_machine.change_state(self.next_state_name)
            return

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"[VideoState] ERROR: No se pudo abrir '{self.video_path}'. Saltando estado.")
            self.state_machine.change_state(self.next_state_name)
            return

        # Obtener FPS nativos del video para que no se reproduzca acelerado ni desfasado
        video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if video_fps and not math.isnan(video_fps) and video_fps > 0:
            self.fps = video_fps
        else:
            self.fps = 30.0
        self.frame_delay = 1.0 / self.fps

        self.start_time = time.perf_counter()

    def exit(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.current_surface = None

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Requerimiento: Si el usuario presiona Enter o Espacio durante cualquier video,
                # debe saltarse (skip) y pasar directamente al Menú.
                if self.allow_skip and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self.state_machine.change_state("MENU")
                    return

    def update(self, dt):
        if self.is_finished or self.cap is None or not self.cap.isOpened():
            return

        # Sincronización precisa con el reloj real
        elapsed = time.perf_counter() - self.start_time
        target_frame = int(elapsed * self.fps)

        # Leer fotogramas para mantener sincronía sin acumular lag
        while self.frame_count <= target_frame and not self.is_finished:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.is_finished = True
                self.state_machine.change_state(self.next_state_name)
                return

            self.frame_count += 1
            # Solo convertimos a superficie de Pygame el fotograma más reciente
            if self.frame_count >= target_frame:
                frame_h, frame_w = frame.shape[:2]
                
                # Conversión BGR (OpenCV) a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Escalado eficiente si difiere de la resolución nativa
                target_w, target_h = SCREEN_WIDTH, SCREEN_HEIGHT
                if (frame_w, frame_h) != (target_w, target_h):
                    frame_rgb = cv2.resize(frame_rgb, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                
                # Creación de superficie Pygame mediante pygame.image.frombuffer
                # (Transposición de dimensiones para formato HxWxC a Pygame WxH)
                self.current_surface = pygame.image.frombuffer(
                    frame_rgb.tobytes(), (target_w, target_h), "RGB"
                )

    def draw(self, screen):
        if self.current_surface:
            screen.blit(self.current_surface, (0, 0))
        else:
            screen.fill((0, 0, 0))


class BootState(VideoState):
    """ESTADO 'BOOT': Reproduce CCI_INTRO.mp4 y pasa a INTRO_AVATAR al terminar."""
    def __init__(self, state_machine):
        super().__init__(state_machine, video_path="CCI_INTRO.mp4", next_state_name="INTRO_AVATAR", allow_skip=True)


class IntroAvatarState(VideoState):
    """ESTADO 'INTRO_AVATAR': Reproduce intro_cami.mp4 y pasa al MENU al terminar."""
    def __init__(self, state_machine):
        super().__init__(state_machine, video_path="intro_cami.mp4", next_state_name="MENU", allow_skip=True)


class MenuState(BaseState):
    """
    ESTADO 'MENU': Pantalla de selección interactiva estilo arcade retro.
    - Soporte visual cyberpunk/arcade con gradientes, líneas scanline y efectos glow.
    - Opciones seleccionables: 'Da Vinci Fighters' y 'Metal Slug'.
    - Navegación con flechas (Arriba/Abajo) y selección con Enter.
    """
    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.options = [
            {
                "title": "DA VINCI FIGHTERS",
                "subtitle": "Capcom CPS-1 / Street Fighter II Tribute",
                "key": "davinci",
                "color": (255, 60, 60),
                "badge": "FIGHTING 1P/2P"
            },
            {
                "title": "METAL SLUG",
                "subtitle": "SNK Neo-Geo Arcade Replica: Super Vehicle-001",
                "key": "metalslug",
                "color": (255, 200, 20),
                "badge": "ACTION RUN & GUN"
            }
        ]
        self.selected_index = 0
        self.anim_timer = 0.0

        # Cargar avatar si existe en el directorio raíz
        self.avatar_img = None
        avatar_path = "cami_player.png"
        if os.path.exists(avatar_path):
            try:
                loaded = pygame.image.load(avatar_path).convert_alpha()
                # Escalar proporcionalmente para encajar en el lateral del menú
                w, h = loaded.get_size()
                target_h = 360
                target_w = int(w * (target_h / h))
                self.avatar_img = pygame.transform.smoothscale(loaded, (target_w, target_h))
            except Exception as e:
                print(f"[MenuState] No se pudo cargar {avatar_path}: {e}")

    def enter(self):
        self.anim_timer = 0.0
        pygame.display.set_caption("C.C.I. SYSTEM - VIRTUAL ARCADE CONSOLE")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                    self._play_beep(pitch=600)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_index = (self.selected_index + 1) % len(self.options)
                    self._play_beep(pitch=500)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    selected_game = self.options[self.selected_index]["key"]
                    self._play_beep(pitch=900)
                    self.state_machine.change_state("PLAYING", game_key=selected_game)

    def _play_beep(self, pitch=500):
        """Genera un tono sintético ligero si el mixer está disponible."""
        try:
            if not pygame.mixer.get_init():
                return
            sample_rate = 22050
            duration = 0.05
            n_samples = int(sample_rate * duration)
            buf = bytearray()
            for i in range(n_samples):
                t = float(i) / sample_rate
                # Onda cuadrada arcade
                val = 127 if math.sin(2.0 * math.pi * pitch * t) > 0 else -128
                buf.append(val & 0xFF)
            sound = pygame.mixer.Sound(buffer=bytes(buf))
            sound.set_volume(0.25)
            sound.play()
        except Exception:
            pass

    def update(self, dt):
        self.anim_timer += dt

    def draw(self, screen):
        # Fondo oscuro retro con gradiente
        screen.fill((12, 14, 24))

        # Cuadrícula retro en el fondo
        grid_color = (25, 30, 50)
        grid_size = 40
        offset_y = int((self.anim_timer * 20) % grid_size)
        for y in range(-grid_size, SCREEN_HEIGHT + grid_size, grid_size):
            pygame.draw.line(screen, grid_color, (0, y + offset_y), (SCREEN_WIDTH, y + offset_y), 1)
        for x in range(0, SCREEN_WIDTH, grid_size):
            pygame.draw.line(screen, grid_color, (x, 0), (x, SCREEN_HEIGHT), 1)

        # Encabezado C.C.I. System
        font_header_big = pygame.font.Font(None, 64)
        font_header_sub = pygame.font.Font(None, 24)
        font_option = pygame.font.Font(None, 44)
        font_sub = pygame.font.Font(None, 24)
        font_badge = pygame.font.Font(None, 20)

        # Barra superior metálica/arcade
        pygame.draw.rect(screen, (20, 24, 42), (0, 0, SCREEN_WIDTH, 90))
        pygame.draw.line(screen, (0, 220, 255), (0, 90), (SCREEN_WIDTH, 90), 2)

        title_surf = font_header_big.render("C.C.I. SYSTEM", True, (0, 240, 255))
        screen.blit(title_surf, (50, 16))

        sub_surf = font_header_sub.render("VIRTUAL ARCADE MULTI-GAME PLATFORM // SELECT CARTRIDGE", True, (180, 200, 220))
        screen.blit(sub_surf, (52, 64))

        # Avatar en la esquina derecha si está disponible
        if self.avatar_img:
            # Sombra y marco para el avatar
            av_x = SCREEN_WIDTH - self.avatar_img.get_width() - 50
            av_y = 120 + int(math.sin(self.anim_timer * 2.5) * 6)  # Levitación suave
            
            # Resplandor detrás del avatar
            glow_surf = pygame.Surface((self.avatar_img.get_width() + 40, self.avatar_img.get_height() + 40), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (0, 200, 255, 35), glow_surf.get_rect())
            screen.blit(glow_surf, (av_x - 20, av_y - 20))
            screen.blit(self.avatar_img, (av_x, av_y))

        # Contenedor de opciones (lado izquierdo / central)
        menu_x = 70
        start_y = 170
        card_w = 640
        card_h = 130
        spacing = 40

        pulse = (math.sin(self.anim_timer * 6.0) + 1.0) / 2.0  # 0.0 a 1.0

        for i, opt in enumerate(self.options):
            cy = start_y + i * (card_h + spacing)
            is_selected = (i == self.selected_index)

            # Fondo de la tarjeta
            card_rect = pygame.Rect(menu_x, cy, card_w, card_h)
            if is_selected:
                # Color de tarjeta iluminada
                base_color = (32, 40, 68)
                border_color = (
                    int(opt["color"][0] * 0.7 + 255 * 0.3 * pulse),
                    int(opt["color"][1] * 0.7 + 255 * 0.3 * pulse),
                    int(opt["color"][2] * 0.7 + 255 * 0.3 * pulse)
                )
                border_w = 3
                # Flecha indicadora animada
                arrow_offset = int(pulse * 8)
                arrow_surf = font_option.render("►", True, border_color)
                screen.blit(arrow_surf, (menu_x - 42 + arrow_offset, cy + 30))
            else:
                base_color = (20, 24, 38)
                border_color = (60, 70, 95)
                border_w = 1

            pygame.draw.rect(screen, base_color, card_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, card_rect, width=border_w, border_radius=8)

            # Badge de categoría
            badge_surf = font_badge.render(f"[{opt['badge']}]", True, border_color if is_selected else (130, 140, 160))
            screen.blit(badge_surf, (menu_x + 20, cy + 18))

            # Título principal del juego
            text_color = (255, 255, 255) if is_selected else (170, 180, 200)
            txt_title = font_option.render(opt["title"], True, text_color)
            screen.blit(txt_title, (menu_x + 20, cy + 42))

            # Subtítulo descriptivo
            txt_sub = font_sub.render(opt["subtitle"], True, (130, 150, 180) if is_selected else (100, 110, 130))
            screen.blit(txt_sub, (menu_x + 20, cy + 88))

        # Barra inferior de controles
        footer_y = SCREEN_HEIGHT - 60
        pygame.draw.rect(screen, (15, 18, 30), (0, footer_y, SCREEN_WIDTH, 60))
        pygame.draw.line(screen, (40, 50, 80), (0, footer_y), (SCREEN_WIDTH, footer_y), 1)

        help_txt = font_header_sub.render("▲/▼ / W/S: NAVEGAR   |   ENTER / ESPACIO: INICIAR JUEGO   |   ESC: SALIR", True, (160, 180, 210))
        screen.blit(help_txt, ((SCREEN_WIDTH - help_txt.get_width()) // 2, footer_y + 20))


class PlayingState(BaseState):
    """
    ESTADO 'PLAYING':
    - Importa e invoca el juego seleccionado pasándole la superficie de la ventana principal (`screen`).
    - Alimenta el contexto de la ventana única (1280x720) sin crear ventanas nuevas.
    - Captura la salida y re-establece el estado del entorno de Pygame para retornar fluidamente al 'MENU'.
    """
    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.game_key = None

    def enter(self, game_key="davinci"):
        self.game_key = game_key
        self._run_game()

    def _run_game(self):
        screen = self.state_machine.screen
        root_dir = os.path.abspath(os.path.dirname(__file__))

        # Detener cualquier audio previo
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.stop()
        except Exception:
            pass

        if self.game_key == "davinci":
            davinci_dir = os.path.join(root_dir, "Davinci-Fighter")
            if not os.path.exists(davinci_dir):
                # Fallback por si la carpeta se llama davinci_fighters
                alt_dir = os.path.join(root_dir, "davinci_fighters")
                if os.path.exists(alt_dir):
                    davinci_dir = alt_dir

            print(f"[PlayingState] Cargando Da Vinci Fighters desde {davinci_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(davinci_dir)
                if davinci_dir not in sys.path:
                    sys.path.insert(0, davinci_dir)

                # Importar módulos de Da Vinci Fighters
                import settings
                import audio_manager as df_audio
                from intro_cutscene import IntroCutscene
                from title_screen import TitleScreen
                from menu import MainMenu
                from character_select import CharacterSelect
                from vs_screen import VSScreen
                from game import Game

                # Configurar ventana y reloj
                pygame.display.set_caption(settings.TITLE)
                clock = pygame.time.Clock()
                fps = settings.FPS

                # Secuencia pre-combate
                app_state = "intro_cutscene"
                intro_cutscene = IntroCutscene(screen)
                title_screen = None
                char_select = None
                vs_screen = None
                game_instance = None
                selected_mode = "1p"
                p1_char = "carloni"
                p2_char = "cavasso"
                selected_stage_id = None

                running_game = True
                while running_game:
                    dt = 1.0 / fps
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running_game = False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and app_state != "game":
                            # Tecla de escape en los menús de Da Vinci retorna al HUB de C.C.I.
                            running_game = False

                        if app_state == "intro_cutscene":
                            res = intro_cutscene.handle_input(event)
                            if res == "finish":
                                app_state = "title_screen"
                                title_screen = TitleScreen(screen)

                        elif app_state == "title_screen":
                            res = title_screen.handle_input(event)
                            if res in ("continue", "start"):
                                selected_mode = getattr(title_screen, "selected_mode", "1p")
                                credits_p1 = getattr(title_screen, "credits_p1", 1)
                                credits_p2 = getattr(title_screen, "credits_p2", 0)
                                char_select = CharacterSelect(screen, selected_mode, credits_p1=credits_p1, credits_p2=credits_p2)
                                app_state = "character_select"

                        elif app_state == "character_select":
                            res = char_select.handle_input(event)
                            if res and res.get("action") in ("vs", "fight"):
                                p1_char = res.get("p1_char", "carloni")
                                p2_char = res.get("p2_char", "cavasso")
                                selected_stage_id = res.get("stage_id", None)
                                selected_mode = char_select.game_mode
                                game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                                app_state = "game"

                        elif app_state == "vs_screen":
                            res = vs_screen.handle_input(event)
                            if res == "fight":
                                game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                                app_state = "game"

                    # Updates y Dibujado
                    if app_state == "intro_cutscene":
                        res = intro_cutscene.update(dt)
                        if res == "finish":
                            app_state = "title_screen"
                            title_screen = TitleScreen(screen)
                        intro_cutscene.draw(screen)

                    elif app_state == "title_screen":
                        title_screen.update(dt)
                        title_screen.draw(screen)

                    elif app_state == "character_select":
                        res = char_select.update(dt)
                        if res and res.get("action") in ("vs", "fight"):
                            p1_char = res.get("p1_char", "carloni")
                            p2_char = res.get("p2_char", "cavasso")
                            selected_stage_id = res.get("stage_id", None)
                            selected_mode = char_select.game_mode
                            game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                            app_state = "game"
                        char_select.draw(screen)

                    elif app_state == "vs_screen":
                        res = vs_screen.update(dt)
                        if res == "fight":
                            game_instance = Game(screen, p1_char, p2_char, selected_mode, stage_id=selected_stage_id)
                            app_state = "game"
                        vs_screen.draw(screen)

                    elif app_state == "game":
                        result = game_instance.run()
                        if result in ("menu", "exit"):
                            # Si sale del combate, volvemos a selección o al menú C.C.I.
                            running_game = False

                    pygame.display.flip()
                    clock.tick(fps)

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Da Vinci Fighters: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Limpiar canales de audio de Da Vinci
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.stop()
                except Exception:
                    pass
                os.chdir(original_cwd)

        elif self.game_key == "metalslug":
            ms_dir = os.path.join(root_dir, "METAL SLUG")
            if not os.path.exists(ms_dir):
                alt_dir = os.path.join(root_dir, "metal_slug")
                if os.path.exists(alt_dir):
                    ms_dir = alt_dir

            print(f"[PlayingState] Cargando Metal Slug desde {ms_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(ms_dir)
                if ms_dir not in sys.path:
                    sys.path.insert(0, ms_dir)

                from src.game import Game as MetalSlugGame
                from src.config import FPS as MS_FPS, TITLE as MS_TITLE

                # Instanciar el juego reutilizando la pantalla existente
                # Sobrescribimos el set_mode interno para que no cree otra ventana
                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                try:
                    ms_instance = MetalSlugGame()
                    # Asegurar referencia de screen
                    ms_instance.screen = screen
                finally:
                    pygame.display.set_mode = orig_set_mode

                pygame.display.set_caption(MS_TITLE)

                # Ejecutar ciclo de Metal Slug sin llamar a pygame.quit() al terminar
                while ms_instance.is_running:
                    ms_instance.handle_events()
                    ms_instance.update()
                    ms_instance.draw()
                    ms_instance.clock.tick(MS_FPS)

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Metal Slug: {e}")
                import traceback
                traceback.print_exc()
            finally:
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.stop()
                except Exception:
                    pass
                os.chdir(original_cwd)

        # Re-establecer pantalla y regresar al Menú C.C.I.
        self.state_machine.change_state("MENU")


class StateMachine:
    """
    Gestor central de la Máquina de Estados (State Machine Pattern).
    Controla el ciclo de vida, transiciones y delegación de eventos/renders.
    """
    def __init__(self, screen):
        self.screen = screen
        self.states = {}
        self.current_state = None
        self.current_state_name = None

    def register_state(self, name, state_instance):
        """Registra un estado en la máquina con su identificador."""
        self.states[name] = state_instance

    def change_state(self, state_name, **kwargs):
        """Transición segura hacia un nuevo estado."""
        if state_name not in self.states:
            raise ValueError(f"Estado '{state_name}' no registrado en StateMachine.")

        if self.current_state is not None:
            self.current_state.exit()

        print(f"[StateMachine] Transición: {self.current_state_name} -> {state_name}")
        self.current_state_name = state_name
        self.current_state = self.states[state_name]
        self.current_state.enter(**kwargs)

    def handle_events(self, events):
        if self.current_state:
            self.current_state.handle_events(events)

    def update(self, dt):
        if self.current_state:
            self.current_state.update(dt)

    def draw(self, screen):
        if self.current_state:
            self.current_state.draw(screen)
