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
import importlib.util
import subprocess

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
from sidebar_ui import draw_sidebar, load_sidebar, make_sidebar_font, sidebar_destination

if _old_stderr_fd is not None:
    try:
        os.dup2(_old_stderr_fd, 2)
        os.close(_old_stderr_fd)
    except Exception:
        pass



# Dimensiones base del sistema virtual
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720


class JoystickManager:
    """
    Gestor universal de Mandos / Joysticks (pygame.joystick) para C.C.I. System.
    - Soporta DualShock, DualSense (PS4/PS5), Xbox 360/One/Series, Switch Pro y genéricos USB.
    - Maneja hotplugging (conexión / desconexión en caliente).
    - Traduce automáticamente analógicos, D-pad y botones a teclas virtuales de Pygame
      (KEYDOWN/KEYUP) y mantiene sincronizado pygame.key.get_pressed().
    - Inyecta soporte de joystick universal y transparente a los 6 juegos sin romper su lógica.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.joysticks = {}
        self.deadzone = 0.35
        self.active_simulated_keys = set()
        self._axis_states = {}  # {(joy_id, axis): val}
        self._button_map = {
            # Botones estándar estilo Xbox / PlayStation / Nintendo / Arcade
            0: pygame.K_SPACE,      # A / Cruz -> Confirmar / Salto / Disparo
            1: pygame.K_b,          # B / Círculo -> Cancelar / Secundario / Granada
            2: pygame.K_j,          # X / Cuadrado -> Golpe débil / Disparo primario
            3: pygame.K_k,          # Y / Triángulo -> Golpe fuerte / Especial
            4: pygame.K_u,          # LB / L1 -> Patada débil
            5: pygame.K_i,          # RB / R1 -> Patada fuerte / Turbo
            6: pygame.K_ESCAPE,     # Back / Share / Select -> Volver / Menú / Salir
            7: pygame.K_RETURN,     # Start / Options -> Pausa / Confirmar / Start
            8: pygame.K_p,          # Guía / Home / L3
            9: pygame.K_o,          # R3
        }
        self.init_subsystem()
        self._install_hooks()

    def init_subsystem(self):
        """Inicializa el subsistema de joystick de Pygame y abre dispositivos detectados."""
        if not pygame.joystick.get_init():
            try:
                pygame.joystick.init()
            except Exception as e:
                print(f"[JoystickManager] Error iniciando pygame.joystick: {e}")
                return

        self.refresh_devices()

    def refresh_devices(self):
        """Detecta y activa todos los mandos conectados."""
        if not pygame.joystick.get_init():
            return
        count = pygame.joystick.get_count()
        for i in range(count):
            if i not in self.joysticks:
                try:
                    joy = pygame.joystick.Joystick(i)
                    joy.init()
                    self.joysticks[i] = joy
                    print(f"[JoystickManager] Mando #{i} conectado: {joy.get_name()}")
                except Exception as e:
                    print(f"[JoystickManager] No se pudo inicializar mando #{i}: {e}")

    def _install_hooks(self):
        """Instala interceptores transparentes en pygame.key.get_pressed y pygame.event.get."""
        orig_get_pressed = pygame.key.get_pressed
        orig_event_get = pygame.event.get
        active_keys = self.active_simulated_keys
        process_event = self.process_event

        class ScancodeWrapper:
            def __init__(self, base_keys):
                self.base_keys = base_keys

            def __getitem__(self, key):
                if key in active_keys:
                    return 1
                try:
                    return 1 if self.base_keys[key] else 0
                except (IndexError, KeyError):
                    return 0

            def __len__(self):
                return len(self.base_keys)

        def hooked_get_pressed():
            base = orig_get_pressed()
            if not active_keys:
                return base
            return ScancodeWrapper(base)

        def hooked_event_get(*args, **kwargs):
            events = orig_event_get(*args, **kwargs)
            res = []
            for ev in events:
                synthesized = process_event(ev)
                res.append(ev)
                if synthesized:
                    res.extend(synthesized)
            return res

        pygame.key.get_pressed = hooked_get_pressed
        pygame.event.get = hooked_event_get


    def process_event(self, event):
        """
        Interpreta eventos de joystick y genera eventos de teclado equivalentes.
        Retorna una lista de eventos sintetizados (si los hay).
        """
        synthesized = []

        # 1. Hotplugging
        if event.type == pygame.JOYDEVICEADDED:
            self.refresh_devices()
        elif event.type == pygame.JOYDEVICEREMOVED:
            instance_id = getattr(event, "instance_id", None)
            if instance_id is not None and instance_id in self.joysticks:
                del self.joysticks[instance_id]
                print(f"[JoystickManager] Mando #{instance_id} desconectado")

        # 2. D-pad (Hat)
        elif event.type == pygame.JOYHATMOTION:
            hat_x, hat_y = event.value
            # Eje X D-pad
            if hat_x < 0:
                synthesized.extend(self._press_key(pygame.K_LEFT))
                synthesized.extend(self._press_key(pygame.K_a))
                synthesized.extend(self._release_key(pygame.K_RIGHT))
                synthesized.extend(self._release_key(pygame.K_d))
            elif hat_x > 0:
                synthesized.extend(self._press_key(pygame.K_RIGHT))
                synthesized.extend(self._press_key(pygame.K_d))
                synthesized.extend(self._release_key(pygame.K_LEFT))
                synthesized.extend(self._release_key(pygame.K_a))
            else:
                synthesized.extend(self._release_key(pygame.K_LEFT))
                synthesized.extend(self._release_key(pygame.K_a))
                synthesized.extend(self._release_key(pygame.K_RIGHT))
                synthesized.extend(self._release_key(pygame.K_d))

            # Eje Y D-pad
            if hat_y < 0:
                synthesized.extend(self._press_key(pygame.K_DOWN))
                synthesized.extend(self._press_key(pygame.K_s))
                synthesized.extend(self._release_key(pygame.K_UP))
                synthesized.extend(self._release_key(pygame.K_w))
            elif hat_y > 0:
                synthesized.extend(self._press_key(pygame.K_UP))
                synthesized.extend(self._press_key(pygame.K_w))
                synthesized.extend(self._release_key(pygame.K_DOWN))
                synthesized.extend(self._release_key(pygame.K_s))
            else:
                synthesized.extend(self._release_key(pygame.K_UP))
                synthesized.extend(self._release_key(pygame.K_w))
                synthesized.extend(self._release_key(pygame.K_DOWN))
                synthesized.extend(self._release_key(pygame.K_s))

        # 3. Stick Analógico (Axis 0: Horizontal, Axis 1: Vertical)
        elif event.type == pygame.JOYAXISMOTION:
            axis = event.axis
            val = event.value
            if axis == 0:  # Stick izquierdo horizontal
                if val < -self.deadzone:
                    synthesized.extend(self._press_key(pygame.K_LEFT))
                    synthesized.extend(self._press_key(pygame.K_a))
                    synthesized.extend(self._release_key(pygame.K_RIGHT))
                    synthesized.extend(self._release_key(pygame.K_d))
                elif val > self.deadzone:
                    synthesized.extend(self._press_key(pygame.K_RIGHT))
                    synthesized.extend(self._press_key(pygame.K_d))
                    synthesized.extend(self._release_key(pygame.K_LEFT))
                    synthesized.extend(self._release_key(pygame.K_a))
                else:
                    synthesized.extend(self._release_key(pygame.K_LEFT))
                    synthesized.extend(self._release_key(pygame.K_a))
                    synthesized.extend(self._release_key(pygame.K_RIGHT))
                    synthesized.extend(self._release_key(pygame.K_d))
            elif axis == 1:  # Stick izquierdo vertical
                if val < -self.deadzone:
                    synthesized.extend(self._press_key(pygame.K_UP))
                    synthesized.extend(self._press_key(pygame.K_w))
                    synthesized.extend(self._release_key(pygame.K_DOWN))
                    synthesized.extend(self._release_key(pygame.K_s))
                elif val > self.deadzone:
                    synthesized.extend(self._press_key(pygame.K_DOWN))
                    synthesized.extend(self._press_key(pygame.K_s))
                    synthesized.extend(self._release_key(pygame.K_UP))
                    synthesized.extend(self._release_key(pygame.K_w))
                else:
                    synthesized.extend(self._release_key(pygame.K_UP))
                    synthesized.extend(self._release_key(pygame.K_w))
                    synthesized.extend(self._release_key(pygame.K_DOWN))
                    synthesized.extend(self._release_key(pygame.K_s))

        # 4. Botones
        elif event.type == pygame.JOYBUTTONDOWN:
            mapped_key = self._button_map.get(event.button)
            if mapped_key:
                synthesized.extend(self._press_key(mapped_key))
        elif event.type == pygame.JOYBUTTONUP:
            mapped_key = self._button_map.get(event.button)
            if mapped_key:
                synthesized.extend(self._release_key(mapped_key))

        return synthesized

    def _press_key(self, key):
        if key not in self.active_simulated_keys:
            self.active_simulated_keys.add(key)
            e = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, scancode=0)
            return [e]
        return []

    def _release_key(self, key):
        if key in self.active_simulated_keys:
            self.active_simulated_keys.discard(key)
            e = pygame.event.Event(pygame.KEYUP, key=key, mod=0, scancode=0)
            return [e]
        return []

    def reset(self):
        """Limpia el estado de teclas simuladas."""
        self.active_simulated_keys.clear()

    def rumble(self, low=0.6, high=0.6, duration_ms=250):
        """Emite vibración háptica en los mandos conectados."""
        for joy in self.joysticks.values():
            if hasattr(joy, "rumble"):
                try:
                    joy.rumble(float(low), float(high), int(duration_ms))
                except Exception:
                    pass

    def hit_rumble(self):
        self.rumble(0.75, 0.9, 230)

    def damage_rumble(self):
        self.rumble(0.5, 0.65, 180)

    def explosion_rumble(self):
        self.rumble(1.0, 0.85, 420)



# Instancia global del JoystickManager
joystick_manager = JoystickManager()


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
                # debe saltarse (skip) y pasar directamente al siguiente estado.
                if self.allow_skip and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self.audio_player.stop()
                    self.state_machine.change_state(self.next_state_name)
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
    """ESTADO 'INTRO_AVATAR': Reproduce Pixel_girl_reading_dialogue_boxes_20261016123851.mp4 con audio y pasa a USER_SELECT al terminar."""
    def __init__(self, state_machine):
        super().__init__(
            state_machine,
            video_path="Pixel_girl_reading_dialogue_boxes_20261016123851.mp4",
            next_state_name="USER_SELECT",
            allow_skip=True
        )



class MenuState(BaseState):
    """
    ESTADO 'MENU': Carrusel interactivo estilo rueda cilíndrica 3D sobre 'select_game.jpeg'.
    - 14 Juegos integrados:
        1. Da Vinci Fighters
        2. Metal Slug
        3. Asteroids
        4. Super Mario Bros
        5. Pac-Man
        6. Space Invaders
        7. Tetris
        8. The Legend of Zelda
        9. DOOM
        10-14. Minecraft, Flappy Bird, Dino, GhostBusters, Cyberpunk Metroidvania
    - Carrusel vertical cilíndrico idéntico al diseño de referencia:
      * Tarjeta central destacada con marco blanco brillante sci-fi y flechas indicadoras (< >).
      * Tarjetas superiores e inferiores curvadas hacia la derecha con escala, opacidad y perspectiva.
      * Desplazamiento ultra suave con inercia e interpolación lerp.
      * Navegación con Arriba/Abajo (W/S o Flechas o D-pad / Stick del Gamepad).
      * Confirmación con ENTER o ESPACIO o Botón X / A del Gamepad.
    """
    def __init__(self, state_machine, on_game_launch=None):
        super().__init__(state_machine)
        self.on_game_launch = on_game_launch
        self.options = [
            {"key": "metalslug",      "title": "Metal Slug",         "dialog": "Metal Slug: Acción bélica y tanques arcade."},
            {"key": "asteroids",      "title": "Asteroids",          "dialog": "Asteroids: Clásico vector espacial de Atari."},
            {"key": "davinci",        "title": "Da Vinci Fighters",  "dialog": "Da Vinci Fighters: Combate arcade 1v1."},
            {"key": "mario",          "title": "Super Mario Bros",   "dialog": "Super Mario Bros: Aventura en el Reino Champiñón."},
            {"key": "pacman",         "title": "Pac-Man",            "dialog": "Pac-Man: Come puntos y esquiva fantasmas."},
            {"key": "space_invaders", "title": "Space Invaders",     "dialog": "Space Invaders: Defiende la Tierra de la invasión alienígena."},
            {"key": "tetris",         "title": "Tetris",             "dialog": "Tetris: Encaja los tetriminos y limpia líneas."},
            {"key": "zelda",          "title": "Zelda",              "dialog": "The Legend of Zelda: Explora y lucha en Hyrule."},
            {"key": "doom",           "title": "DOOM",               "dialog": "DOOM: Acción shooter en primera persona en Marte."},
            {"key": "flappy",         "title": "Flappy Bird",        "dialog": "Flappy Bird: Vuela entre las tuberías sin chocar."},
            {"key": "dino",           "title": "Dino",               "dialog": "Dino: Corre y salta obstáculos sin parar."},
            {"key": "ghostbusters",   "title": "GhostBusters",       "dialog": "GhostBusters: Plataformas de acción contra fantasmas."},
            {"key": "cyberpunk",      "title": "Cyberpunk Metroidvania", "dialog": "Cyberpunk Metroidvania: Plataformas de acción distópico."},
            {"key": "pokemon",        "title": "Pokémon",            "dialog": "Pokémon: Aventura RPG clásica por el mundo de Kanto."},
            {"key": "fighter",        "title": "Street Fighter II",  "dialog": "Street Fighter II: Combate arcade 1v1 con Ryu."},
            {"key": "sonic",          "title": "Sonic The Hedgehog", "dialog": "Sonic: Corre a toda velocidad por Green Hill Zone."},
            {"key": "megaman",        "title": "Mega Man",           "dialog": "Mega Man: Plataformas de acción robótica retro."},
            {"key": "mkultra",        "title": "Mortal Kombat",      "dialog": "Mortal Kombat: Combate visceral uno contra uno."},
            {"key": "castlevania",     "title": "Castlevania",        "dialog": "Castlevania: Aventura gótica y látigo contra Drácula."},
            {"key": "bubblebobble",    "title": "Bubble Bobble",      "dialog": "Bubble Bobble: Atrapa monstruos en burbujas mágicas."},
            {"key": "plantsvszombies", "title": "Plants vs. Zombies", "dialog": "Plants vs. Zombies: Defiende tu jardín de los no-muertos."},
            {"key": "donkeykong",      "title": "Donkey Kong",        "dialog": "Donkey Kong: Salta barriles y rescata a Pauline."},
            {"key": "qbert",           "title": "Q*bert",             "dialog": "Q*bert: Cambia el color de la pirámide esquivando enemigos."}
        ]
        self.selected_index = 2
        self.last_mouse_game = None
        self.last_mouse_time = 0.0
        self.scroll_pos = 0.0  # Posición suave interpolada
        self.anim_timer = 0.0

        # Cargar el lienzo original vacío del carrusel de selección.
        self.bg_image = None
        self.offset_x = 0
        bg_path = os.path.join("pantallas", "Menú futurista C.C.I System.png")

        if os.path.exists(bg_path):
            try:
                loaded = pygame.image.load(bg_path).convert()
                self.bg_image = pygame.transform.smoothscale(
                    loaded, (SCREEN_WIDTH, SCREEN_HEIGHT)
                )
            except Exception as e:
                print(f"[MenuState] Error cargando fondo {bg_path}: {e}")

        # Inicio usa la misma barra de la plantilla base de logros que las otras vistas.
        self.sidebar_surface = load_sidebar()
        self.sidebar_font = make_sidebar_font()
        self.sidebar_extensions = []
        if self.bg_image:
            for destination, source, solid_columns in (
                (pygame.Rect(260, 35, 90, 75), pygame.Rect(350, 35, 90, 75), 90),
                (pygame.Rect(260, 100, 150, 480), pygame.Rect(410, 100, 150, 480), 80),
            ):
                patch = self._feather_background_patch(destination, source, solid_columns)
                self.sidebar_extensions.append((destination.topleft, patch))

        # Cargar recursos del carrusel: tarjetas limpias y marco resaltado
        self.card_surfs = {}
        for opt in self.options:
            key = opt["key"]
            clean_path = f"assets_cards/{key}_clean.png"
            if not os.path.exists(clean_path):
                clean_path = f"assets_cards/{key}.png"
            if os.path.exists(clean_path):
                try:
                    self.card_surfs[key] = pygame.image.load(clean_path).convert_alpha()
                except Exception as e:
                    print(f"[MenuState] Error cargando tarjeta {clean_path}: {e}")

        # Marco de selección brillante
        self.selected_border = None
        if os.path.exists("assets_cards/selected_border_clean.png"):
            self.selected_border = pygame.image.load("assets_cards/selected_border_clean.png").convert_alpha()

        # Fuente retro para textos informativos
        self.font = None
        for font_candidate in [
            "./Zelda/extracted/15 - fixes audio/graphics/font/joystix.ttf",
            "./tetris/mario.ttf",
            "./Space-invaders/font/Pixeled.ttf",
            "./Mario/resources/fonts/Fixedsys500c.ttf"
        ]:
            if os.path.exists(font_candidate):
                try:
                    self.font = pygame.font.Font(font_candidate, 13)
                    self.font_large = pygame.font.Font(font_candidate, 15)
                    break
                except Exception:
                    pass
        if self.font is None:
            self.font = pygame.font.SysFont("Courier", 13, bold=True)
            self.font_large = pygame.font.SysFont("Courier", 15, bold=True)



    def enter(self):
        self.anim_timer = 0.0
        self.scroll_pos = float(self.selected_index)
        pygame.display.set_caption("C.C.I. SYSTEM - SELECT GAME (14 GAMES)")

    def handle_events(self, events):
        num_options = len(self.options)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                destination = self._sidebar_destination(event.pos)
                if destination:
                    if destination == "QUIT":
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    else:
                        self.state_machine.change_state(destination)
                    return
                if self._handle_background_arrow(event.pos):
                    return
                if self._handle_card_click(event.pos):
                    return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_F2, pygame.K_F3):
                    self.state_machine.change_state("USER_SELECT")
                    return
                if event.key == pygame.K_F4:
                    self.state_machine.change_state("LIBRARY")
                    return
                if event.key == pygame.K_F6:
                    self.state_machine.change_state("PROFILE")
                    return
                if event.key == pygame.K_F7:
                    self.state_machine.change_state("ACHIEVEMENTS")
                    return
                if event.key == pygame.K_F8:
                    self.state_machine.change_state("SETTINGS")
                    return
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % num_options
                    self._play_beep(pitch=650)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_index = (self.selected_index + 1) % num_options
                    self._play_beep(pitch=550)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_index = (self.selected_index - 1) % num_options
                    self._play_beep(pitch=650)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_index = (self.selected_index + 1) % num_options
                    self._play_beep(pitch=550)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    selected_game = self.options[self.selected_index]["key"]
                    self._play_beep(pitch=900)
                    self._launch_game(selected_game)
                elif event.key == pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _launch_game(self, game_key):
        started = time.monotonic()
        self.state_machine.change_state("PLAYING", game_key=game_key)
        if self.on_game_launch:
            try:
                self.on_game_launch(game_key, time.monotonic() - started)
            except Exception as exc:
                print(f"[MenuState] No se pudo registrar la partida: {exc}")

    def _handle_background_arrow(self, pos):
        """La flecha derecha visible del fondo cambia la selección del juego."""
        x, y = pos
        if not (245 <= y <= 400):
            return False
        if 1218 <= x <= 1265:
            self.selected_index = (self.selected_index + 1) % len(self.options)
            self._play_beep(pitch=550)
            return True
        return False

    def _handle_card_click(self, pos):
        """Permite elegir una tarjeta visible con mouse y doble clic para abrirla."""
        num_options = len(self.options)
        round_pos = round(self.scroll_pos)
        for offset in (-2, -1, 0, 1, 2):
            d = offset - (self.scroll_pos - round_pos)
            index = (round_pos + offset) % num_options
            scale = 1.0 - abs(d) * 0.08
            width, height = int(500 * scale), int(109 * scale)
            rect = pygame.Rect(0, 0, width, height)
            x = 960 + d * d * 14.5
            y = 327 + d * 115.0
            rect.center = (int(x), int(y))
            if rect.collidepoint(pos):
                now = time.monotonic()
                if self.last_mouse_game == index and now - self.last_mouse_time < 0.45:
                    self._play_beep(pitch=900)
                    self._launch_game(self.options[index]["key"])
                else:
                    self.selected_index = index
                    self._play_beep(pitch=650)
                self.last_mouse_game = index
                self.last_mouse_time = now
                return True
        return False

    @staticmethod
    def _sidebar_destination(pos):
        """Usa las mismas filas de navegación que las demás vistas."""
        return sidebar_destination(pos)

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
        
        # Interpolación suave (lerp) del carrusel con envoltura circular más corta
        num_options = len(self.options)
        target = self.selected_index
        diff = (target - self.scroll_pos)
        while diff > num_options / 2:
            diff -= num_options
        while diff < -num_options / 2:
            diff += num_options
            
        self.scroll_pos += diff * min(1.0, dt * 14.0)
        self.scroll_pos %= num_options

    def _feather_background_patch(self, destination, source, solid_columns=0):
        """Limpia los restos de la antigua navegación y suaviza su borde exterior."""
        patch = self.bg_image.subsurface(destination).copy()
        clean = self.bg_image.subsurface(source).copy()
        width, height = patch.get_size()
        fade_width = max(1, width - solid_columns)
        for column in range(width):
            alpha = 255 if column < solid_columns else round(
                255 * (1.0 - (column - solid_columns) / max(1, fade_width - 1))
            )
            strip = clean.subsurface(pygame.Rect(column, 0, 1, height)).copy()
            strip.set_alpha(alpha)
            patch.blit(strip, (column, 0))
        return patch

    def _draw_common_sidebar(self, screen):
        """Usa el mismo diseño y tipografía común que las otras vistas."""
        for position, patch in self.sidebar_extensions:
            screen.blit(patch, position)
        draw_sidebar(screen, self.sidebar_surface, "home", self.sidebar_font)

    def draw(self, screen):
        screen.fill((0, 0, 0))

        # Fondo intacto; se sustituye únicamente la franja lateral.
        if self.bg_image:
            screen.blit(self.bg_image, (self.offset_x, 0))
        self._draw_common_sidebar(screen)

        # 2. Renderizar el carrusel vertical original (5 tarjetas visibles).
        num_options = len(self.options)
        center_y = 327
        center_x = 960

        # Para cada distancia relativa de -2 a +2 alrededor de la posición de scroll
        # Renderizamos de afuera hacia adentro para un correcto z-index
        indices_to_draw = [-2, 2, -1, 1, 0]
        
        for offset in indices_to_draw:
            # Calcular índice continuo relativo a la posición interpolada
            rel_idx = offset - (self.scroll_pos - round(self.scroll_pos))
            actual_idx = (round(self.scroll_pos) + offset) % num_options
            game_opt = self.options[actual_idx]
            game_key = game_opt["key"]

            if game_key not in self.card_surfs:
                continue

            # Parámetros cilíndricos calibrados con la imagen de referencia:
            # d: distancia respecto al centro seleccionado (-2.0 .. +2.0)
            d = rel_idx
            
            # Altura en Y con espaciado cilíndrico (~115px por slot)
            slot_y = center_y + d * 115.0
            
            # Curvatura cilíndrica en X: se desplaza a la derecha cuanto más lejos del centro
            slot_x = center_x + (d * d) * 14.5
            
            # Escala de la tarjeta: 100% en el centro, disminuye en los extremos (~85%)
            scale_factor = 1.0 - abs(d) * 0.08
            card_w = max(10, int(500 * scale_factor))
            card_h = max(10, int(109 * scale_factor))

            # Alpha / brillo: tarjetas no seleccionadas son ligeramente más tenues
            alpha = max(100, int(255 - abs(d) * 45))

            card_base = self.card_surfs[game_key]
            scaled_card = pygame.transform.smoothscale(card_base, (card_w, card_h))

            if alpha < 255:
                scaled_card.set_alpha(alpha)

            card_rect = scaled_card.get_rect(center=(int(slot_x), int(slot_y)))
            screen.blit(scaled_card, card_rect)

            # Si es el elemento central (offset == 0) y el scroll está casi asentado:
            if offset == 0 and abs(self.scroll_pos - self.selected_index) < 0.25:
                # Dibujar marco blanco brillante con pulsación sutil
                if self.selected_border:
                    pulse = int(2 + math.sin(self.anim_timer * 6.0) * 1.5)
                    bw = card_w + pulse * 2
                    bh = card_h + pulse * 2
                    border_surf = pygame.transform.smoothscale(self.selected_border, (bw, bh))
                    b_rect = border_surf.get_rect(center=(int(slot_x), int(slot_y)))
                    screen.blit(border_surf, b_rect)


        # El mensaje y los controles inferiores pertenecen al fondo original; no se
        # dibuja texto encima para evitar duplicar las instrucciones de la plantilla.


class ScreenPreviewState(BaseState):
    """Displays one of the completed UI screens with the shared sidebar navigation."""

    def __init__(self, state_machine, image_path):
        super().__init__(state_machine)
        self.image_path = image_path
        self.image = None

    def enter(self):
        try:
            loaded = pygame.image.load(self.image_path).convert()
            self.image = pygame.transform.smoothscale(
                loaded, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
        except (pygame.error, OSError) as error:
            self.image = None
            print(f"[ScreenPreviewState] Error cargando {self.image_path}: {error}")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state_machine.change_state("MENU")
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                destination = MenuState._sidebar_destination(event.pos)
                if destination == "QUIT":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                elif destination == "MENU":
                    self.state_machine.change_state("MENU")
                elif destination:
                    self.state_machine.change_state(destination)
                return

    def draw(self, screen):
        screen.fill((0, 0, 0))
        if self.image:
            screen.blit(self.image, (0, 0))


# Juegos que corren en su propio proceso: clave -> (carpeta, script, módulo requerido o None)
EXTERNAL_GAMES = {
    "flappy":       ("Flappy-Bird", "main.py", None),
    "dino":         ("Dino", "main.py", None),
    "ghostbusters": ("GhostBusters", "main.py", None),
    "cyberpunk":    ("Cyberpunk-Metroidvania/Platformer 01-04-2022", "main.py", None),
    "pokemon":      ("pokemon", "main.py", None),
    "fighter":      ("fighter", "main.py", None),
    "streetfighter":("fighter", "main.py", None),
    "sonic":        ("sonic", "main.py", None),
    "megaman":      ("MegamanPygame", "Game.py", None),
    "mkultra":      ("MK-Ultra", "MKUltra.py", None),
    "castlevania":     ("castlevania", "Main.py", None),
    "bubblebobble":    ("bubble-bobble", "main.py", None),
    "plantsvszombies": ("PlantsVSZombies", "main.py", None),
    "donkeykong":      ("PythonDonkeyKong", "main.py", None),
    "qbert":           ("qbert", "Qbert.py", None),
}


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

    @staticmethod
    def _show_notice(screen, message, seconds=3.0):
        """Muestra un aviso centrado (p. ej. dependencia faltante) antes de volver al menú."""
        try:
            font = pygame.font.Font(None, 34)
            text = font.render(message, True, (255, 255, 255))
            box = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)).inflate(60, 40)
            screen.fill((0, 0, 0))
            pygame.draw.rect(screen, (20, 22, 30), box, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), box, 2, border_radius=8)
            screen.blit(text, text.get_rect(center=box.center))
            pygame.display.flip()
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                for ev in pygame.event.get():
                    if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                        return
                pygame.time.wait(30)
        except Exception:
            pass

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

        # Capturar instantánea de módulos base del launcher para purgar completamente
        # cualquier colisión (por ejemplo: weapon.py de Zelda vs weapon.py de DOOM)
        base_modules = set(sys.modules.keys())
        CONFLICTING_MODULES = [
            "settings", "audio_manager", "game", "menu", "input_manager",
            "character_select", "player", "intro_cutscene", "title_screen",
            "vs_screen", "pacman", "main", "constants", "config", "setup", "tools",
            "weapon", "level", "tile", "support", "entity", "enemy", "magic", "ui",
            "upgrade", "particles", "debug", "sound", "npc", "object_renderer",
            "raycasting", "object_handler", "map", "sprite_object", "pathfinding"
        ]
        for mod in CONFLICTING_MODULES:
            sys.modules.pop(mod, None)

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
                if davinci_dir in sys.path:
                    sys.path.remove(davinci_dir)
                sys.path.insert(0, davinci_dir)

                # Purgar específicamente cualquier módulo de settings o juego previo
                for mod in CONFLICTING_MODULES:
                    sys.modules.pop(mod, None)

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

                # Limpiar cualquier evento residual (como ENTER o SPACE) del menú principal
                pygame.event.clear()

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
                if davinci_dir in sys.path:
                    sys.path.remove(davinci_dir)
                for mod in CONFLICTING_MODULES:
                    sys.modules.pop(mod, None)
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
                if pacman_dir in sys.path:
                    sys.path.remove(pacman_dir)
                for mod in CONFLICTING_MODULES:
                    sys.modules.pop(mod, None)
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
                prev_ast_state = 'playing'
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
                        prev_ast_state = 'playing'
                    elif ast_instance.gameState == 'exploding':
                        if prev_ast_state != 'exploding':
                            joystick_manager.explosion_rumble()
                            prev_ast_state = 'exploding'
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

        elif self.game_key == "tetris":
            tetris_dir = os.path.join(root_dir, "tetris")
            print(f"[PlayingState] Cargando Tetris desde {tetris_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(tetris_dir)
                if tetris_dir not in sys.path:
                    sys.path.insert(0, tetris_dir)

                import Tetris as tetris_mod

                # Tetris está diseñado para 800x750 en superficie interna o screen
                # Creamos una superficie virtual de 800x750 y la escalamos a 1280x720 centrado
                t_surf = pygame.Surface((tetris_mod.s_width, tetris_mod.s_height))
                clock = pygame.time.Clock()
                locked_positions = {}
                grid = tetris_mod.create_grid(locked_positions)
                change_piece = False
                run_tetris = True
                current_piece = tetris_mod.get_shape()
                next_pieces_queue = [tetris_mod.get_shape() for _ in range(3)]
                fall_time = 0
                fall_speed = 0.35
                score = 0
                lines_cleared_total = 0
                level = 1
                last_score = tetris_mod.get_max_score()

                pygame.display.set_caption("TETRIS CLASSIC ARCADE")

                while run_tetris:
                    grid = tetris_mod.create_grid(locked_positions)
                    fall_time += clock.get_rawtime()
                    clock.tick(60)

                    if fall_time / 1000 > fall_speed:
                        fall_time = 0
                        current_piece.y += 1
                        if not tetris_mod.valid_space(current_piece, grid) and current_piece.y > 0:
                            current_piece.y -= 1
                            change_piece = True

                    events = pygame.event.get()
                    # Mapear eventos de Joystick
                    for ev in events:
                        synth = joystick_manager.process_event(ev)
                        events.extend(synth)

                    for event in events:
                        if event.type == pygame.QUIT:
                            run_tetris = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                run_tetris = False
                            elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                                current_piece.x -= 1
                                if not tetris_mod.valid_space(current_piece, grid):
                                    current_piece.x += 1
                            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                                current_piece.x += 1
                                if not tetris_mod.valid_space(current_piece, grid):
                                    current_piece.x -= 1
                            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                                current_piece.y += 1
                                if not tetris_mod.valid_space(current_piece, grid):
                                    current_piece.y -= 1
                            elif event.key == pygame.K_UP or event.key == pygame.K_w or event.key == pygame.K_j or event.key == pygame.K_SPACE:
                                current_piece.rotation = (current_piece.rotation + 1) % len(current_piece.shape)
                                if not tetris_mod.valid_space(current_piece, grid):
                                    current_piece.rotation = (current_piece.rotation - 1) % len(current_piece.shape)

                    piece_pos = tetris_mod.convert_shape_format(current_piece)

                    if change_piece:
                        for pos in piece_pos:
                            locked_positions[pos] = current_piece.color
                        current_piece = next_pieces_queue.pop(0)
                        next_pieces_queue.append(tetris_mod.get_shape())
                        change_piece = False
                        cleared = tetris_mod.clear_rows(tetris_mod.create_grid(locked_positions), locked_positions)
                        if cleared > 0:
                            lines_cleared_total += cleared
                            score += cleared * 10
                            level = 1 + (lines_cleared_total // 10)
                            fall_speed = max(0.08, 0.35 - (level - 1) * 0.03)
                            tetris_mod.update_score(score)
                            if last_score < score:
                                last_score = score
                            joystick_manager.rumble(0.65, 0.8, 220)
                        else:
                            joystick_manager.rumble(0.2, 0.3, 60)

                    # Reconstruir cuadrícula limpia con posiciones bloqueadas
                    grid = tetris_mod.create_grid(locked_positions)

                    # Colocar la pieza actual en movimiento sobre la cuadrícula
                    piece_pos = tetris_mod.convert_shape_format(current_piece)
                    for i in range(len(piece_pos)):
                        x, y = piece_pos[i]
                        if y >= 0:
                            grid[y][x] = current_piece.color

                    tetris_mod.draw_window(t_surf, grid, score, level, last_score)
                    tetris_mod.draw_next_shape_queue(next_pieces_queue, t_surf)

                    # Escalar y centrar t_surf (800x720) en screen (1280x720)
                    scaled_t = pygame.transform.smoothscale(t_surf, (800, 720))
                    screen.fill((8, 7, 12))
                    screen.blit(scaled_t, ((1280 - 800) // 2, 0))
                    pygame.display.flip()

                    if tetris_mod.check_lost(locked_positions):
                        tetris_mod.draw_text_middle('You Lost', 40, (255, 255, 255), t_surf)
                        scaled_t = pygame.transform.smoothscale(t_surf, (800, 720))
                        screen.blit(scaled_t, ((1280 - 800) // 2, 0))
                        pygame.display.flip()
                        pygame.time.delay(1500)
                        run_tetris = False

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Tetris: {e}")
                import traceback
                traceback.print_exc()
            finally:
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.stop()
                except Exception:
                    pass
                if tetris_dir in sys.path:
                    sys.path.remove(tetris_dir)
                for mod in CONFLICTING_MODULES:
                    sys.modules.pop(mod, None)
                os.chdir(original_cwd)

        elif self.game_key == "doom":
            doom_dir = os.path.join(root_dir, "DOOM")
            print(f"[PlayingState] Cargando DOOM desde {doom_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(doom_dir)
                if doom_dir not in sys.path:
                    sys.path.insert(0, doom_dir)

                orig_set_mode = pygame.display.set_mode
                # DOOM renderiza a RES = (1600, 900)
                doom_surf = pygame.Surface((1600, 900))
                pygame.display.set_mode = lambda *args, **kwargs: doom_surf

                from main import Game as DoomGame
                doom_game = DoomGame()
                doom_game.screen = doom_surf
                pygame.display.set_mode = orig_set_mode
                pygame.display.set_caption("DOOM 3D - C.C.I. SYSTEM")

                clock = pygame.time.Clock()
                running_doom = True

                while running_doom:
                    doom_game.global_trigger = False
                    events = pygame.event.get()
                    for ev in events:
                        synth = joystick_manager.process_event(ev)
                        events.extend(synth)

                    for event in events:
                        if event.type == pygame.QUIT:
                            running_doom = False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            running_doom = False
                        elif event.type == doom_game.global_event:
                            doom_game.global_trigger = True
                        doom_game.player.single_fire_event(event)

                    doom_game.player.update()
                    doom_game.raycasting.update()
                    doom_game.object_handler.update()
                    doom_game.weapon.update()
                    doom_game.delta_time = clock.tick(60)

                    doom_game.draw()

                    # Escalar de 1600x900 (16:9) directo a 1280x720 (16:9)
                    scaled_doom = pygame.transform.scale(doom_surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    screen.blit(scaled_doom, (0, 0))
                    pygame.display.flip()

            except Exception as e:
                print(f"[PlayingState] Error ejecutando DOOM: {e}")
                import traceback
                traceback.print_exc()
            finally:
                try:
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.stop()
                except Exception:
                    pass
                if doom_dir in sys.path:
                    sys.path.remove(doom_dir)
                for mod in CONFLICTING_MODULES:
                    sys.modules.pop(mod, None)
                os.chdir(original_cwd)

        elif self.game_key == "zelda":
            zelda_dir = os.path.join(root_dir, "Zelda", "extracted", "15 - fixes audio", "code")
            print(f"[PlayingState] Cargando Zelda desde {zelda_dir}...")
            original_cwd = os.getcwd()
            try:
                os.chdir(zelda_dir)
                if zelda_dir not in sys.path:
                    sys.path.insert(0, zelda_dir)

                orig_set_mode = pygame.display.set_mode
                pygame.display.set_mode = lambda *args, **kwargs: screen

                from main import Game as ZeldaGame
                zelda_game = ZeldaGame()
                zelda_game.screen = screen
                pygame.display.set_mode = orig_set_mode
                pygame.display.set_caption("THE LEGEND OF ZELDA")

                clock = pygame.time.Clock()
                running_zelda = True

                while running_zelda:
                    events = pygame.event.get()
                    for ev in events:
                        synth = joystick_manager.process_event(ev)
                        events.extend(synth)

                    for event in events:
                        if event.type == pygame.QUIT:
                            running_zelda = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                running_zelda = False
                            elif event.key == pygame.K_m:
                                zelda_game.level.toggle_menu()

                    screen.fill('#71ddee')
                    zelda_game.level.run()
                    pygame.display.update()
                    clock.tick(60)

            except Exception as e:
                print(f"[PlayingState] Error ejecutando Zelda: {e}")
                import traceback
                traceback.print_exc()
            finally:
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.stop()
                except Exception:
                    pass
                if zelda_dir in sys.path:
                    sys.path.remove(zelda_dir)
                for mod in CONFLICTING_MODULES:
                    sys.modules.pop(mod, None)
                os.chdir(original_cwd)

        elif self.game_key in EXTERNAL_GAMES:
            folder, entry, requires = EXTERNAL_GAMES[self.game_key]
            game_dir = os.path.join(root_dir, folder)
            entry_path = os.path.join(game_dir, entry)
            print(f"[PlayingState] Lanzando {self.game_key} desde {entry_path}...")
            problem = None
            if not os.path.isfile(entry_path):
                problem = f"No se encontró {folder}/{entry}"
            elif requires and importlib.util.find_spec(requires) is None:
                problem = f"Falta instalar '{requires}':  pip install {requires}"
            if problem:
                print(f"[PlayingState] {problem}")
                self._show_notice(screen, problem)
            else:
                try:
                    env = os.environ.copy()
                    env.setdefault("SDL_VIDEO_CENTERED", "1")
                    env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")
                    subprocess.run([sys.executable, entry_path], cwd=os.path.dirname(entry_path), env=env, check=False)
                except Exception as e:
                    print(f"[PlayingState] Error ejecutando {self.game_key}: {e}")
                    self._show_notice(screen, f"Error al iniciar {self.game_key}")
            pygame.display.set_caption("C.C.I. SYSTEM")

        # Limpiar exhaustivamente cualquier módulo importado por el juego ejecutado
        for mod in list(sys.modules.keys()):
            if mod not in base_modules:
                sys.modules.pop(mod, None)

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
