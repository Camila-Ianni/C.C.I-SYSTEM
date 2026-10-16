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


import subprocess
import shutil

class VideoAudioPlayer:
    """
    Controlador de audio complementario para VideoState.
    OpenCV sólo decodifica video; VideoAudioPlayer reproduce la pista de audio
    de forma nativa y sincronizada en segundo plano (usando afplay en macOS o pygame.mixer.music).
    """
    def __init__(self, video_path):
        self.video_path = video_path
        self.process = None

    def play(self):
        self.stop()
        if not os.path.exists(self.video_path):
            return

        # En macOS, afplay reproduce directamente el contenedor mp4 sin requerir herramientas externas
        if sys.platform == "darwin" and shutil.which("afplay"):
            try:
                self.process = subprocess.Popen(
                    ["afplay", self.video_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return
            except Exception as e:
                print(f"[VideoAudioPlayer] Error al invocar afplay: {e}")

        # Fallback usando pygame.mixer.music si el formato es soportado
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(self.video_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"[VideoAudioPlayer] pygame.mixer no pudo reproducir {self.video_path}: {e}")

    def stop(self):
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.kill()
            except Exception:
                pass
            self.process = None

        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass


class VideoState(BaseState):
    """
    Estado genérico de reproducción de video sincronizado usando OpenCV con Audio Activado.
    - Sincroniza FPS mediante cv2.CAP_PROP_FPS y cálculo de tiempo transcurrido (time.perf_counter).
    - Reproduce el audio integrado del video mediante VideoAudioPlayer.
    - Convierte fotogramas BGR de OpenCV a superficies RGB de Pygame.
    - Permite omitir (skip) con ENTER o ESPACIO hacia el estado deseado deteniendo el audio de inmediato.
    """
    def __init__(self, state_machine, video_path, next_state_name, allow_skip=True):
        super().__init__(state_machine)
        self.video_path = video_path
        self.next_state_name = next_state_name
        self.allow_skip = allow_skip
        
        self.cap = None
        self.audio_player = VideoAudioPlayer(video_path)
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

        # Iniciar reproducción de audio sincronizado
        self.audio_player.play()
        self.start_time = time.perf_counter()

    def exit(self):
        # Detener audio de inmediato al salir del estado
        self.audio_player.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.current_surface = None

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Si el usuario presiona Enter o Espacio durante cualquier video,
                # debe saltarse (skip) y pasar directamente al Menú.
                if self.allow_skip and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self.audio_player.stop()
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
                self.audio_player.stop()
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
                self.current_surface = pygame.image.frombuffer(
                    frame_rgb.tobytes(), (target_w, target_h), "RGB"
                )

    def draw(self, screen):
        if self.current_surface:
            screen.blit(self.current_surface, (0, 0))
        else:
            screen.fill((0, 0, 0))


class BootState(VideoState):
    """ESTADO 'BOOT': Reproduce CCI_INTRO.mp4 con audio y pasa a INTRO_AVATAR al terminar."""
    def __init__(self, state_machine):
        super().__init__(state_machine, video_path="CCI_INTRO.mp4", next_state_name="INTRO_AVATAR", allow_skip=True)


class IntroAvatarState(VideoState):
    """ESTADO 'INTRO_AVATAR': Reproduce intro_cami.mp4 con audio y pasa al MENU al terminar."""
    def __init__(self, state_machine):
        super().__init__(state_machine, video_path="intro_cami.mp4", next_state_name="MENU", allow_skip=True)


class MenuState(BaseState):
    """
    ESTADO 'MENU': Pantalla de selección interactiva basada en 'select_game.jpg'.
    - Renderiza la imagen oficial de selección de juegos a 1280x720.
    - Soporta navegación horizontal (Izquierda / Derecha) y vertical (A / D / W / S / Flechas).
    - Resalta dinámicamente con marco brillante la opción seleccionada:
      0 -> DA VINCI FIGHTERS (Panel izquierdo)
      1 -> METAL SLUG (Panel derecho)
    - Selección con Enter o Espacio.
    """
    def __init__(self, state_machine):
        super().__init__(state_machine)
        self.options = [
            {"key": "davinci", "title": "Da Vinci Fighters"},
            {"key": "metalslug", "title": "Metal Slug"}
        ]
        self.selected_index = 0
        self.anim_timer = 0.0

        # Cargar y escalar select_game.jpg al tamaño de la pantalla
        self.bg_image = None
        img_candidates = ["select_game.jpg", "select_game.png", "select_game.jpeg"]
        for cand in img_candidates:
            if os.path.exists(cand):
                try:
                    loaded = pygame.image.load(cand)
                    self.bg_image = pygame.transform.smoothscale(loaded, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    break
                except Exception as e:
                    print(f"[MenuState] Error al cargar {cand}: {e}")

        # Coordenadas exactas de los dos paneles en la resolución de 1280x720
        # (Medidas calibradas en base a la relación de aspecto de select_game.jpg)
        self.card_rects = [
            pygame.Rect(48, 182, 574, 452),   # Panel Da Vinci Fighters
            pygame.Rect(658, 182, 574, 452)   # Panel Metal Slug
        ]

    def enter(self):
        self.anim_timer = 0.0
        pygame.display.set_caption("C.C.I. SYSTEM - SELECT GAME")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % len(self.options)
                    self._play_beep(pitch=600)
                elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
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
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((15, 18, 25))

        # Efecto de iluminación/resaltado sobre la tarjeta seleccionada
        selected_rect = self.card_rects[self.selected_index]
        pulse = (math.sin(self.anim_timer * 5.0) + 1.0) / 2.0  # Rango 0.0 a 1.0

        # Resplandor cian/blanco arcade semitransparente
        glow_alpha = int(35 + pulse * 45)
        glow_surf = pygame.Surface((selected_rect.width + 16, selected_rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(
            glow_surf,
            (0, 220, 255, glow_alpha),
            glow_surf.get_rect(),
            border_radius=18
        )
        screen.blit(glow_surf, (selected_rect.x - 8, selected_rect.y - 8))

        # Borde brillante animado sobre el marco de la tarjeta metálica
        border_color = (
            int(180 + pulse * 75),
            int(220 + pulse * 35),
            255
        )
        pygame.draw.rect(screen, border_color, selected_rect, width=3, border_radius=14)

        # Indicador 'P1' / Flecha de selección arcade sobre la tarjeta
        font_p1 = pygame.font.Font(None, 28)
        tag_text = font_p1.render("◄ SELECT ►", True, border_color)
        tag_x = selected_rect.centerx - (tag_text.get_width() // 2)
        tag_y = selected_rect.top - 24 + int(pulse * 3)
        screen.blit(tag_text, (tag_x, tag_y))


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
