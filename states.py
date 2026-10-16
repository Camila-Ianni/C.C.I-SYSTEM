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

# En macOS, opencv-python y pygame-ce contienen bibliotecas SDL2 duplicadas en sus .dylibs.
# Redirigir stderr a nivel de descriptor de archivo de bajo nivel durante la importación
# silencia limpiamente los warnings de duplicación de Objective-C sin alterar la funcionalidad.
_old_stderr_fd = None
try:
    sys.stderr.flush()
    _old_stderr_fd = os.dup(2)
    _devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(_devnull_fd, 2)
    os.close(_devnull_fd)
except Exception:
    _old_stderr_fd = None

import pygame
import cv2

if _old_stderr_fd is not None:
    try:
        os.dup2(_old_stderr_fd, 2)
        os.close(_old_stderr_fd)
    except Exception:
        pass



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
    """ESTADO 'INTRO_AVATAR': Reproduce Pixel_girl_reading_dialogue_boxes_20261016123851.mp4 con audio y pasa al MENU al terminar."""
    def __init__(self, state_machine):
        super().__init__(
            state_machine,
            video_path="Pixel_girl_reading_dialogue_boxes_20261016123851.mp4",
            next_state_name="MENU",
            allow_skip=True
        )



class MenuState(BaseState):
    """
    ESTADO 'MENU': Pantalla de selección interactiva basada en 'games.png' (6 juegos).
    - Renderiza 'games.png' (1452x1083) escalado de forma proporcional y centrado en 1280x720.
    - Soporta rejilla 2x3 con navegación completa (Izquierda/Derecha/Arriba/Abajo / WASD):
      Fila 0:
        (0,0) Da Vinci Fighters
        (0,1) Metal Slug
        (0,2) Asteroids
      Fila 1:
        (1,0) Super Mario Bros
        (1,1) Pac-Man
        (1,2) Space Invaders
    - Efecto Hover dinámico: Al posicionarse sobre cualquier juego con el teclado,
      la tarjeta cambia instantáneamente a su versión a todo color extraída de 'cards-color.jpeg'
      y se ilumina con el halo arcade cibernético.
    - Selección con ENTER o ESPACIO.
    """
    def __init__(self, state_machine):
        super().__init__(state_machine)
        # Disposición real de los 6 cartuchos en la interfaz gráfica
        self.options = [
            {"key": "davinci", "title": "Da Vinci Fighters", "row": 0, "col": 0},
            {"key": "metalslug", "title": "Metal Slug", "row": 0, "col": 1},
            {"key": "asteroids", "title": "Asteroids", "row": 0, "col": 2},
            {"key": "mario", "title": "Super Mario Bros", "row": 1, "col": 0},
            {"key": "pacman", "title": "Pac-Man", "row": 1, "col": 1},
            {"key": "space_invaders", "title": "Space Invaders", "row": 1, "col": 2},
        ]
        self.selected_index = 0
        self.anim_timer = 0.0

        # Cargar games.png preservando su relación de aspecto (1452x1083)
        self.bg_image = None
        self.img_rect = None
        self.card_rects = []
        self.color_cards = []

        orig_w, orig_h = 1452, 1083
        scale = SCREEN_HEIGHT / orig_h  # 720 / 1083 ≈ 0.66482
        scaled_w = int(orig_w * scale)   # ~965 px
        scaled_h = SCREEN_HEIGHT         # 720 px
        self.offset_x = (SCREEN_WIDTH - scaled_w) // 2  # Centrado horizontal (~157 px)

        img_path = "games.png"
        if not os.path.exists(img_path):
            img_path = "select_game.jpg"

        if os.path.exists(img_path):
            try:
                loaded = pygame.image.load(img_path).convert()
                self.bg_image = pygame.transform.smoothscale(loaded, (scaled_w, scaled_h))
                self.img_rect = pygame.Rect(self.offset_x, 0, scaled_w, scaled_h)
            except Exception as e:
                print(f"[MenuState] Error cargando imagen de menú {img_path}: {e}")

        # Coordenadas exactas y calibradas de los 6 cards en games.png (1452x1083):
        # Fila 0:
        #   (0,0) Da Vinci Fighters: [381, 262, 330, 243]
        #   (0,1) Metal Slug:        [740, 262, 325, 243]
        #   (0,2) Asteroids:         [1086, 262, 321, 243]
        # Fila 1:
        #   (1,0) Super Mario Bros:  [381, 530, 330, 253]
        #   (1,1) Pac-Man:           [740, 530, 325, 253]
        #   (1,2) Space Invaders:    [1086, 530, 321, 253]
        games_boxes = [
            (381, 262, 330, 243),  # Da Vinci
            (740, 262, 325, 243),  # Metal Slug
            (1086, 262, 321, 243), # Asteroids
            (381, 530, 330, 253),  # Super Mario
            (740, 530, 325, 253),  # Pac-Man
            (1086, 530, 321, 253), # Space Invaders
        ]

        for gx, gy, gw, gh in games_boxes:
            sx = int(round(self.offset_x + gx * scale))
            sy = int(round(gy * scale))
            sw = int(round(gw * scale))
            sh = int(round(gh * scale))
            self.card_rects.append(pygame.Rect(sx, sy, sw, sh))

        # Cargar y recortar las tarjetas en B&N y Color desde 'cards-bn.jpeg' y 'cards-color.jpeg'
        self.bn_cards = []
        self.color_cards = []
        self._load_cards(scale, games_boxes)

    def _load_cards(self, scale, games_boxes):
        """
        Corta y prepara los sprites de cada tarjeta:
        - Versión en Blanco y Negro (cards-bn.jpeg) para el estado inactivo.
        - Versión a todo Color (cards-color.jpeg) para el efecto Hover al seleccionarla.
        """
        bn_path = "cards-bn.jpeg"
        color_path = "cards-color.jpeg"

        # Bounding boxes de las cards en la imagen fuente de alta resolución (2400x1792)
        src_boxes = [
            (628, 433, 548, 403),  # Da Vinci Fighters
            (1223, 433, 538, 404), # Metal Slug
            (1795, 433, 533, 405), # Asteroids
            (628, 876, 548, 420),  # Super Mario Bros
            (1223, 876, 538, 421), # Pac-Man
            (1796, 876, 532, 421), # Space Invaders
        ]

        # 1. Cargar cards en B&N
        if os.path.exists(bn_path):
            try:
                bn_img = pygame.image.load(bn_path)
                for i, (bx, by, bw, bh) in enumerate(src_boxes):
                    sub = bn_img.subsurface(pygame.Rect(bx, by, bw, bh)).copy().convert_alpha()
                    try:
                        arr = pygame.surfarray.pixels3d(sub)
                        alpha_arr = pygame.surfarray.pixels_alpha(sub)
                        is_bg = (arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)
                        alpha_arr[is_bg] = 0
                        del arr
                        del alpha_arr
                    except Exception:
                        pass
                    target_rect = self.card_rects[i]
                    scaled_card = pygame.transform.smoothscale(sub, (target_rect.width, target_rect.height))
                    self.bn_cards.append(scaled_card)
            except Exception as e:
                print(f"[MenuState] Aviso cargando cards B&N: {e}")

        # 2. Cargar cards a Color
        if os.path.exists(color_path):
            try:
                col_img = pygame.image.load(color_path)
                for i, (bx, by, bw, bh) in enumerate(src_boxes):
                    sub = col_img.subsurface(pygame.Rect(bx, by, bw, bh)).copy().convert_alpha()
                    try:
                        arr = pygame.surfarray.pixels3d(sub)
                        alpha_arr = pygame.surfarray.pixels_alpha(sub)
                        is_bg = (arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)
                        alpha_arr[is_bg] = 0
                        del arr
                        del alpha_arr
                    except Exception:
                        pass
                    target_rect = self.card_rects[i]
                    scaled_card = pygame.transform.smoothscale(sub, (target_rect.width, target_rect.height))
                    self.color_cards.append(scaled_card)
            except Exception as e:
                print(f"[MenuState] Aviso cargando cards en color: {e}")

    def enter(self):
        self.anim_timer = 0.0
        pygame.display.set_caption("C.C.I. SYSTEM - SELECT GAME (6 CARTRIDGES)")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                cur_row = self.selected_index // 3
                cur_col = self.selected_index % 3

                if event.key in (pygame.K_LEFT, pygame.K_a):
                    cur_col = (cur_col - 1) % 3
                    self.selected_index = cur_row * 3 + cur_col
                    self._play_beep(pitch=600)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    cur_col = (cur_col + 1) % 3
                    self.selected_index = cur_row * 3 + cur_col
                    self._play_beep(pitch=600)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    cur_row = (cur_row - 1) % 2
                    self.selected_index = cur_row * 3 + cur_col
                    self._play_beep(pitch=500)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    cur_row = (cur_row + 1) % 2
                    self.selected_index = cur_row * 3 + cur_col
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
        screen.fill((0, 0, 0))

        # 1. Dibujar el marco y fondo base del arcade (games.png)
        if self.bg_image and self.img_rect:
            screen.blit(self.bg_image, self.img_rect)

        # 2. Dibujar todas las tarjetas:
        # Si no está seleccionada -> versión Blanco y Negro (cards-bn)
        # Si está seleccionada (HOVER) -> versión a todo Color (cards-color)
        for i, card_rect in enumerate(self.card_rects):
            if i == self.selected_index and i < len(self.color_cards):
                screen.blit(self.color_cards[i], (card_rect.x, card_rect.y))
            elif i < len(self.bn_cards):
                screen.blit(self.bn_cards[i], (card_rect.x, card_rect.y))

        # Solo las imágenes: las inactivas en B&N y la seleccionada a Color (Hover)




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

                # Asegurar que el subsistema de audio esté 100% activo
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                    except Exception:
                        pass

                from src.game import Game as MetalSlugGame
                from src.config import FPS as MS_FPS, TITLE as MS_TITLE, VIRTUAL_WIDTH, VIRTUAL_HEIGHT
                from src.core.sound_manager import SoundManager

                # Reiniciar el singleton SoundManager para garantizar carga de rutas desde el nuevo cwd
                SoundManager._instance = None
                sound_mgr = SoundManager()

                # Instanciar Metal Slug reutilizando la superficie screen sin abrir ventanas nuevas
                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                try:
                    ms_instance = MetalSlugGame()
                    ms_instance.screen = screen
                finally:
                    pygame.display.set_mode = orig_set_mode

                pygame.display.set_caption(MS_TITLE)

                # Escalar la pantalla virtual nativa Neo-Geo (320x224) a la resolución completa de la ventana (1280x720)
                # Manteniendo relación de aspecto 4:3 arcade con márgenes limpios centrados
                scale_y = SCREEN_HEIGHT / VIRTUAL_HEIGHT          # 720 / 224 ≈ 3.214
                scaled_w = int(VIRTUAL_WIDTH * scale_y)           # ~1028 px
                scaled_h = SCREEN_HEIGHT                          # 720 px
                offset_x = (SCREEN_WIDTH - scaled_w) // 2         # Centrado horizontal (~126 px)

                # Sobrescribimos el método original de draw para que no haga blit desalineado
                # ni haga un doble flip que cause parpadeo (flickering/tearing)
                orig_draw = ms_instance.draw
                def single_draw():
                    # Ejecutar el renderizado interno de entidades a virtual_screen
                    # sin ejecutar el bloque final de scale a 960x672 ni el flip original
                    # Usamos una superficie auxiliar temporal o interceptamos el blit final
                    pass

                # Reemplazamos la función de presentación final de ms_instance:
                # El ciclo original de Metal Slug en ms_instance.draw() hace:
                # scaled = pygame.transform.scale(self.virtual_screen, (WINDOW_WIDTH, WINDOW_HEIGHT))
                # self.screen.blit(scaled, (0, 0))
                # pygame.display.flip()
                # Para evitar el parpadeo de dos flips por frame, delegamos el renderizado
                # asignando una función adaptada a 1280x720:
                def presentation_draw():
                    # 1. Ejecutar el pipeline de renderizado original hasta el virtual_screen
                    # Guardamos la pantalla real y ponemos una superficie dummy temporal
                    real_screen = ms_instance.screen
                    dummy_surf = pygame.Surface((1, 1))
                    ms_instance.screen = dummy_surf
                    
                    # Evitamos que pygame.display.flip() sea llamado dentro de draw()
                    real_flip = pygame.display.flip
                    pygame.display.flip = lambda: None
                    try:
                        orig_draw()
                    finally:
                        ms_instance.screen = real_screen
                        pygame.display.flip = real_flip

                    # 2. Dibujar a la ventana real (1280x720) centrado con pillarbox y UN SOLO flip
                    screen.fill((0, 0, 0))
                    scaled_frame = pygame.transform.scale(ms_instance.virtual_screen, (scaled_w, scaled_h))
                    screen.blit(scaled_frame, (offset_x, 0))

                    if offset_x > 0:
                        pygame.draw.rect(screen, (0, 0, 0), (0, 0, offset_x, SCREEN_HEIGHT))
                        pygame.draw.rect(screen, (0, 0, 0), (offset_x + scaled_w, 0, offset_x + 10, SCREEN_HEIGHT))

                    pygame.display.flip()

                ms_instance.draw = presentation_draw

                # Loop fluido de Metal Slug (1 actualización y 1 solo renderizado por tick)
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

        elif self.game_key == "mario":
            mario_dir = os.path.join(root_dir, "Mario")
            print(f"[PlayingState] Cargando Super Mario Bros desde {mario_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(mario_dir)
                if mario_dir not in sys.path:
                    sys.path.insert(0, mario_dir)

                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                from data import setup, tools
                from data.states import main_menu, load_screen, level1
                from data import constants as c

                pygame.display.set_mode = orig_set_mode
                pygame.display.set_caption(setup.ORIGINAL_CAPTION)

                run_it = tools.Control(setup.ORIGINAL_CAPTION)
                run_it.screen = screen
                state_dict = {
                    c.MAIN_MENU: main_menu.Menu(),
                    c.LOAD_SCREEN: load_screen.LoadScreen(),
                    c.TIME_OUT: load_screen.TimeOut(),
                    c.GAME_OVER: load_screen.GameOver(),
                    c.LEVEL1: level1.Level1()
                }
                run_it.setup_states(state_dict, c.MAIN_MENU)

                # Ejecutar loop de Mario interceptando escape para volver
                while not run_it.done:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            run_it.done = True
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            run_it.done = True
                        elif event.type == pygame.KEYDOWN:
                            run_it.keys = pygame.key.get_pressed()
                        elif event.type == pygame.KEYUP:
                            run_it.keys = pygame.key.get_pressed()
                        run_it.state.get_event(event)

                    run_it.update()
                    pygame.display.flip()
                    run_it.clock.tick(run_it.fps)

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Super Mario Bros: {e}")
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

        elif self.game_key == "pacman":
            pacman_dir = os.path.join(root_dir, "PacMan")
            print(f"[PlayingState] Cargando Pac-Man desde {pacman_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(pacman_dir)
                if pacman_dir not in sys.path:
                    sys.path.insert(0, pacman_dir)

                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                from pacman import Game as PacmanGame
                from settings import FPS as PAC_FPS

                try:
                    pac_instance = PacmanGame()
                    pac_instance.screen = screen
                finally:
                    pygame.display.set_mode = orig_set_mode

                pygame.display.set_caption("PAC-MAN")

                running_pacman = True
                pac_instance.game_start_sfx.play()

                while running_pacman:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running_pacman = False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            running_pacman = False
                        else:
                            if event.type == pygame.KEYDOWN:
                                from model.direction import Direction
                                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                                    pac_instance.game_engine.direction_command = Direction.LEFT
                                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                                    pac_instance.game_engine.direction_command = Direction.RIGHT
                                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                                    pac_instance.game_engine.direction_command = Direction.DOWN
                                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                                    pac_instance.game_engine.direction_command = Direction.UP
                                elif event.key == pygame.K_SPACE and pac_instance.game_engine.game_over:
                                    pac_instance.game_start_sfx.play()
                                    pac_instance.game_engine = pac_instance.init()

                    pac_instance.update()
                    pac_instance.draw()

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Pac-Man: {e}")
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

        elif self.game_key == "space_invaders":
            si_dir = os.path.join(root_dir, "Space-invaders", "code")
            print(f"[PlayingState] Cargando Space Invaders desde {si_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(si_dir)
                if si_dir not in sys.path:
                    sys.path.insert(0, si_dir)

                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                from main import Game as SpaceInvadersGame
                import main as si_main

                si_main.screen = screen
                si_main.screen_width = SCREEN_WIDTH
                si_main.screen_height = SCREEN_HEIGHT

                si_instance = SpaceInvadersGame()
                pygame.display.set_mode = orig_set_mode
                pygame.display.set_caption("SPACE INVADERS")

                ALIENLASER = pygame.USEREVENT + 1
                pygame.time.set_timer(ALIENLASER, 800)
                clock = pygame.time.Clock()

                running_si = True
                while running_si:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running_si = False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            running_si = False
                        elif event.type == ALIENLASER:
                            si_instance.alien_shoot()

                    screen.fill((30, 30, 30))
                    si_instance.run()
                    pygame.display.flip()
                    clock.tick(60)

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Space Invaders: {e}")
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

        elif self.game_key == "asteroids":
            ast_dir = os.path.join(root_dir, "asteroids", "src")
            print(f"[PlayingState] Cargando Asteroids desde {ast_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(ast_dir)
                if ast_dir not in sys.path:
                    sys.path.insert(0, ast_dir)

                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                from asteroids import Asteroids as AsteroidsGame
                ast_instance = AsteroidsGame()
                ast_instance.stage.screen = screen
                pygame.display.set_mode = orig_set_mode
                pygame.display.set_caption("ATARI ASTEROIDS")

                clock = pygame.time.Clock()
                running_ast = True
                while running_ast:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running_ast = False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            running_ast = False
                        else:
                            ast_instance.input([event])

                    if ast_instance.paused and not ast_instance.frameAdvance:
                        ast_instance.displayPaused()
                        continue

                    screen.fill((10, 10, 10))
                    ast_instance.stage.moveSprites()
                    ast_instance.stage.drawSprites()
                    ast_instance.doSaucerLogic()
                    ast_instance.displayScore()
                    ast_instance.checkScore()

                    if ast_instance.gameState == 'playing':
                        ast_instance.playing()
                    elif ast_instance.gameState == 'exploding':
                        ast_instance.exploding()
                    else:
                        ast_instance.displayText()

                    pygame.display.flip()
                    clock.tick(60)

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Asteroids: {e}")
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

        # Limpiar eventos residuales y pantalla antes de regresar al Menú C.C.I.
        pygame.event.clear()
        screen.fill((0, 0, 0))
        pygame.display.flip()
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
