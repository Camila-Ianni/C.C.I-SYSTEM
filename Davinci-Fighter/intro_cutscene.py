"""
intro_cutscene.py - Secuencia oficial completa de introducción arcade de Street Fighter II.

Fases continuas (100% fiel al arranque arcade original y Street Fighters.mov):
1. FASE 1 - RAM Diagnostic / Boot Test (0.0s .. 1.8s): Aparecen secuencialmente las comprobaciones:
   SCR 1   RAM OK
   SCR 2   RAM OK
   SCR 3   RAM OK
   OBJECT  RAM OK
   WORK    RAM OK
2. FASE 2 - Title Code & Revision (1.8s .. 3.8s): Fade in suave de opaco a nítido:
   S T R E E T   F I G H T E R   2 '
             9 2 0 5 1 3
               E T C
3. FASE 3 - Warning / Legal Screen (3.8s .. 8.5s):
   Efecto de máquina de escribir de izquierda a derecha (typewriter effect) con el texto legal de advertencia.
4. FASE 4 - Street Brawl Punch Cutscene & Skyscraper Pan a 60 FPS (8.5s .. fin):
   Animación de los luchadores en la calle, golpe certero, paneo por el rascacielos y caída del logotipo.

Soporta salto inmediato (skip) en cualquier momento con ESPACIO, ENTER, ESCAPE o clic de ratón.
"""

import os
import json
import re
import time
import threading
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_YELLOW, COLOR_RED, FPS
from sprite_font import get_boot_font, get_warning_font

DEFAULT_FIGHT_FRAME_CANDIDATES = [
    "30 fotogramas",
    "30 Fotogramas",
    os.path.join("assets", "30 fotogramas"),
    os.path.join("assets", "30 Fotogramas"),
    os.path.join("assets", "pelea_frames"),
]

def _resolve_default_fight_dir():
    for path in DEFAULT_FIGHT_FRAME_CANDIDATES:
        if os.path.isdir(path):
            return path
    return "30 fotogramas"

DEFAULT_FIGHT_FRAME_DIR = _resolve_default_fight_dir()
DEFAULT_FIGHT_VIDEO = os.path.join("assets", "Pelea.mov")
FRAME_FILE_RE = re.compile(r"^frame_\d+\.(?:jpg|jpeg|png)$", re.IGNORECASE)


class IntroCutscene:
    """
    Motor de reproducción de la secuencia completa de apertura pre-título.
    """
    CANVAS_WIDTH = 1280
    CANVAS_HEIGHT = 720
    TARGET_WIDTH = 960
    TARGET_HEIGHT = 720
    PILLARBOX_WIDTH = 160

    # Fases de la introducción
    PHASE_RAM_CHECK = "ram_check"
    PHASE_TITLE_CODE = "title_code"
    PHASE_WARNING = "warning"
    PHASE_BRAWL = "brawl"
    PHASE_FINISHED = "finished"

    def __init__(
        self,
        screen,
        on_finish=None,
        on_finish_callback=None,
        cache_dir=None,
        video_path=None,
        audio_path=None,
    ):
        self.screen = screen
        self.on_finish = on_finish or on_finish_callback
        self.explicit_cache_dir = cache_dir is not None
        self.explicit_video_path = video_path is not None
        self.explicit_audio_path = audio_path is not None

        # La pelea tiene una única fuente autorizada: los frames extraídos de
        # Pelea.mov. No se reutiliza intro_frames ni ningún spritesheet como
        # sustituto visual de esta fase.
        self.cache_dir = cache_dir or DEFAULT_FIGHT_FRAME_DIR
        self.video_path = video_path or DEFAULT_FIGHT_VIDEO
        self.audio_path = audio_path or os.path.join("assets", "audio", "intro_cutscene.wav")

        self.screen_width = screen.get_width() if screen else self.CANVAS_WIDTH
        self.screen_height = screen.get_height() if screen else self.CANVAS_HEIGHT
        self.dest_x = (self.screen_width - self.TARGET_WIDTH) // 2
        self.dest_y = (self.screen_height - self.TARGET_HEIGHT) // 2

        # Fuentes Sprite exclusivas para las pantallas iniciales
        self.boot_font = get_boot_font()
        self.warning_font = get_warning_font()

        # Imagen oficial de Title Code & Revision (DAVINCI FIGHTERS 920513 ETC)
        self.title_code_img = None
        davinci_candidates = [
            os.path.join("assets", "fonts", "streetfighter davinci.PNG"),
            os.path.join("assets", "fonts", "streetfighter davinci.png"),
        ]
        for p in davinci_candidates:
            if os.path.exists(p):
                try:
                    raw_img = pygame.image.load(p).convert()
                    self.title_code_img = pygame.transform.smoothscale(raw_img, (self.screen_width, self.screen_height))
                    break
                except Exception as e:
                    print(f"[IntroCutscene] Error cargando title code image: {e}")

        # Fuentes oficiales arcade
        self.arcade_color_font = None
        self.arcade_color_font_small = None
        font_colr_path = os.path.join("assets", "fonts", "super-street-fighter-ii-large-colour", "super-street-fighter-ii-large-colour.colr.ttf")
        if os.path.exists(font_colr_path):
            try:
                self.arcade_color_font = pygame.font.Font(font_colr_path, 34)
                self.arcade_color_font_small = pygame.font.Font(font_colr_path, 22)
            except Exception as e:
                print(f"[IntroCutscene] Error cargando arcade colr font: {e}")

        # Fuentes seguras de Pygame para fallback
        self.font_ram = pygame.font.Font(None, 44)
        self.font_code = pygame.font.Font(None, 48)
        self.font_warn_hdr = pygame.font.Font(None, 46)
        self.font_warn_body = pygame.font.Font(None, 34)

        # Temporizadores y estados
        self.fps = 60.0
        self.dt_accumulator = 0.0
        self.elapsed_time = 0.0
        self.current_frame_idx = 0
        self.total_frames = 0
        self.finished = False
        self.skipped = False

        # Datos de FASE 1: RAM Check (0.0s .. 3.5s)
        self.ram_lines = [
            "SCR 1       RAM OK",
            "SCR 2       RAM OK",
            "SCR 3       RAM OK",
            "OBJECT      RAM OK",
            "WORK        RAM OK",
        ]
        self.ram_line_delay = 0.45

        # Datos de FASE 2: Title Code (3.5s .. 7.5s)
        self.code_lines = [
            "S T R E E T   F I G H T E R   2 '",
            "9 2 0 5 1 3",
            "E T C",
        ]

        # Datos de FASE 3: Warning Screen (7.5s .. 17.5s)
        self.warn_lines = [
            "This game is for use in all countries",
            "excluding the United States of America,",
            "Canada, Mexico and Japan.",
            "Sales, export or operation inside these",
            "countries may be construed as copyright",
            "and trademark infringement and is strictly",
            "prohibited.",
            "Violators are subject to severe penalties",
            "and will be prosecuted to the full extent",
            "of the law.",
        ]

        # Datos de FASE 4: Brawl Cutscene (60 FPS frames) (17.5s .. fin)
        self.frame_files = []
        self.current_surface = None
        self.audio_sound = None
        self._cv2_cap = None
        self._cv2_start_frame = 892

        self.fight_fps = 30.0
        self.title_fps = 30.0
        self.FIGHT_END_IDX = 246

        self.mode = "mock"
        self._init_frame_provider()
        self._init_audio()

    @property
    def is_finished(self):
        return self.finished

    @is_finished.setter
    def is_finished(self, val):
        self.finished = bool(val)

    @property
    def phase(self):
        if self.finished:
            return self.PHASE_FINISHED
        if self.elapsed_time < 3.5:
            return self.PHASE_RAM_CHECK
        elif self.elapsed_time < 7.5:
            return self.PHASE_TITLE_CODE
        elif self.elapsed_time < 14.5:
            return self.PHASE_WARNING
        else:
            return self.PHASE_BRAWL

    def _init_frame_provider(self):
        """Inicializa la fuente visual autorizada: los frames de la pelea en frente al edificio (carpeta 30 fotogramas)."""
        self.frame_files = []
        self.brawl_fps = 30.0
        self._frame_load_failed = False
        self._frame_cache = {}

        if os.path.isdir(self.cache_dir):
            manifest = {}
            manifest_path = os.path.join(self.cache_dir, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                except (OSError, ValueError, TypeError):
                    manifest = {}

            fps_m = float(
                manifest.get("frame_fps", manifest.get("native_video_fps", manifest.get("fps", 30.0)))
                or 30.0
            )
            total_m = int(manifest.get("total_frames", 0) or manifest.get("count", 0) or 0)

            if self.explicit_cache_dir and total_m > 0:
                self.frame_files = [
                    os.path.join(self.cache_dir, f"frame_{i:04d}.jpg")
                    for i in range(total_m)
                ]
            else:
                candidates = [f for f in os.listdir(self.cache_dir) if FRAME_FILE_RE.fullmatch(f)]
                if candidates:
                    candidates.sort(key=lambda x: int(re.search(r'\d+', x).group()))
                    self.frame_files = [os.path.join(self.cache_dir, f) for f in candidates]

            if self.frame_files:
                self.brawl_fps = max(1.0, fps_m)
                fight_count = min(self.FIGHT_END_IDX, len(self.frame_files))
                post_count = max(0, len(self.frame_files) - fight_count)
                fight_duration = fight_count / self.fight_fps
                post_duration = post_count / self.title_fps
                frames_duration = fight_duration + post_duration

                # Duración total de al menos 20.4 segundos (con hold en el title screen final para no cortar la canción)
                total_brawl_duration = max(20.4, frames_duration) if len(self.frame_files) >= 400 else frames_duration

                self.total_frames = (
                    len(self.frame_files)
                    if self.explicit_cache_dir
                    else max(1, int((14.5 + total_brawl_duration) * self.fps))
                )
                self.mode = "cache"
                self._load_current_brawl_frame()
                self._start_preload()
                return

        # Fallback cv2 si existe video
        if self.video_path and os.path.exists(self.video_path):
            try:
                import cv2
                self._cv2_cap = cv2.VideoCapture(self.video_path)
                if self._cv2_cap.isOpened():
                    native_fps = self._cv2_cap.get(cv2.CAP_PROP_FPS) or self.brawl_fps
                    native_count = int(self._cv2_cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                    self.brawl_fps = max(1.0, float(native_fps))
                    self.total_frames = (
                        865
                        if (self.explicit_cache_dir or self.explicit_video_path)
                        else max(1, int((14.5 + native_count / self.brawl_fps) * self.fps))
                    )
                    self.mode = "cv2"
                    self._load_current_brawl_frame()
                    return
            except Exception:
                self._cv2_cap = None

        self.mode = "mock"
        self.total_frames = 180
        self._load_current_brawl_frame()

    def _start_preload(self):
        """Inicia un hilo en segundo plano para precargar los frames en RAM a 960x720 sin bloquear la ejecución."""
        if not self.frame_files or getattr(self, "_preload_started", False):
            return
        self._preload_started = True

        def _worker():
            for i, frame_path in enumerate(self.frame_files):
                if self.finished or not hasattr(self, "_frame_cache"):
                    break
                if i not in self._frame_cache and os.path.exists(frame_path):
                    try:
                        surf = pygame.image.load(frame_path)
                        if pygame.display.get_surface():
                            surf = surf.convert()
                        w, h = surf.get_size()
                        if w > h * 1.4:
                            rect = pygame.Rect(int(w * 0.125), int(h * 0.052), int(w * 0.75), int(h * 0.896))
                            surf = surf.subsurface(rect)
                        if surf.get_size() != (self.TARGET_WIDTH, self.TARGET_HEIGHT):
                            surf = pygame.transform.scale(surf, (self.TARGET_WIDTH, self.TARGET_HEIGHT))
                        self._frame_cache[i] = surf
                    except Exception:
                        pass
                time.sleep(0.002)

        t = threading.Thread(target=_worker, daemon=True, name="IntroFramePreloader")
        t.start()

    def _init_audio(self):
        """Inicializa la pista de audio del opening."""
        self._brawl_audio_played = False
        self.audio_sound = None
        if self.explicit_audio_path:
            if self.audio_path and os.path.exists(self.audio_path) and pygame.mixer.get_init():
                try:
                    self.audio_sound = pygame.mixer.Sound(self.audio_path)
                except Exception:
                    self.audio_sound = None
            return

        audio_candidates = [
            os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3"),
            os.path.join("assets", "audio", "Opening Theme.mp3"),
            self.audio_path,
        ]
        for ap in audio_candidates:
            if ap and os.path.exists(ap) and pygame.mixer.get_init():
                try:
                    self.audio_sound = pygame.mixer.Sound(ap)
                    break
                except Exception:
                    self.audio_sound = None

    def _load_current_brawl_frame(self):
        """Carga exclusivamente el frame seleccionado de la animación de la pelea."""
        if self.mode == "cache" and self.frame_files:
            if self.explicit_cache_dir:
                idx = min(len(self.frame_files) - 1, max(0, self.current_frame_idx))
            else:
                brawl_t = max(0.0, self.elapsed_time - 14.5)
                fight_count = min(getattr(self, "FIGHT_END_IDX", 246), len(self.frame_files))
                fight_fps = getattr(self, "fight_fps", 30.0)
                title_fps = getattr(self, "title_fps", 30.0)
                fight_duration = fight_count / fight_fps

                if brawl_t < fight_duration:
                    idx = int(brawl_t * fight_fps)
                else:
                    post_t = brawl_t - fight_duration
                    idx = fight_count + int(post_t * title_fps)

                idx = min(len(self.frame_files) - 1, max(0, idx))

            if not hasattr(self, "_frame_cache"):
                self._frame_cache = {}

            if idx in self._frame_cache:
                self.current_surface = self._frame_cache[idx]
                self._frame_load_failed = False
                return

            frame_path = self.frame_files[idx]
            if os.path.exists(frame_path):
                try:
                    surf = pygame.image.load(frame_path)
                    if pygame.display.get_surface():
                        surf = surf.convert()
                    w, h = surf.get_size()
                    if w > h * 1.4:
                        # Zoom al área activa 4:3 eliminando bordes marrones superior/inferior y barras negras laterales
                        rect = pygame.Rect(int(w * 0.125), int(h * 0.052), int(w * 0.75), int(h * 0.896))
                        surf = surf.subsurface(rect)
                    if surf.get_size() != (self.TARGET_WIDTH, self.TARGET_HEIGHT):
                        surf = pygame.transform.scale(surf, (self.TARGET_WIDTH, self.TARGET_HEIGHT))

                    self._frame_cache[idx] = surf
                    self.current_surface = surf
                    self._frame_load_failed = False
                    return
                except Exception:
                    self._frame_load_failed = True
            else:
                self._frame_load_failed = True

        if self.mode == "cv2" and self._cv2_cap is not None and self._cv2_cap.isOpened():
            try:
                import cv2
                ret, frame = self._cv2_cap.read()
                if ret:
                    h, w = frame.shape[:2]
                    if w > h * 1.4:
                        crop = frame[int(h * 0.052):int(h * (0.052 + 0.896)), int(w * 0.125):int(w * (0.125 + 0.75))]
                    else:
                        crop = frame[100:2060, 400:3050] if frame.shape[0] > 1000 else frame
                    resized = cv2.resize(
                        crop, (self.TARGET_WIDTH, self.TARGET_HEIGHT), interpolation=cv2.INTER_LINEAR
                    )
                    self.current_surface = pygame.image.frombuffer(
                        resized.tobytes(), (self.TARGET_WIDTH, self.TARGET_HEIGHT), "BGR"
                    )
                    self._frame_load_failed = False
                    return
                else:
                    self._trigger_finish(skipped=False)
                    return
            except Exception:
                self._frame_load_failed = True

        surf = pygame.Surface((self.TARGET_WIDTH, self.TARGET_HEIGHT))
        surf.fill((0, 0, 0))
        self.current_surface = surf

    def _get_pelea_frame(self, idx):
        """Retorna un frame del único cache autorizado, sin buscar alternativas."""
        if not hasattr(self, "_pelea_cache"):
            self._pelea_cache = {}
        if idx in self._pelea_cache:
            return self._pelea_cache[idx]
        if not self.frame_files:
            return None
        safe_idx = min(len(self.frame_files) - 1, max(0, int(idx)))
        target_path = self.frame_files[safe_idx]
        if os.path.exists(target_path):
            try:
                surf = pygame.image.load(target_path)
                if pygame.display.get_surface():
                    surf = surf.convert()
                w, h = surf.get_size()
                if w > h * 1.4:
                    rect = pygame.Rect(int(w * 0.125), int(h * 0.052), int(w * 0.75), int(h * 0.896))
                    surf = surf.subsurface(rect)
                if surf.get_size() != (self.TARGET_WIDTH, self.TARGET_HEIGHT):
                    surf = pygame.transform.scale(surf, (self.TARGET_WIDTH, self.TARGET_HEIGHT))
                self._pelea_cache[idx] = surf
                return surf
            except Exception:
                pass
        return None

    def handle_input(self, event) -> str | None:
        """Salto inmediato al presionar cualquier tecla o clic."""
        if self.finished:
            return "finish"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                return self._trigger_finish(skipped=True)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._trigger_finish(skipped=True)

        return None

    def update(self, dt: float = 1.0 / FPS) -> str | None:
        """Actualiza la progresión temporal y avance de frames a 60 FPS."""
        if self.finished:
            return "finish"

        self.elapsed_time += dt
        self.dt_accumulator += dt
        frame_duration = 1.0 / self.fps

        # Iniciar audio del opening en la fase de brawl
        if self.elapsed_time >= 14.5 and not getattr(self, "_brawl_audio_played", False):
            self._brawl_audio_played = True
            audio_paths = [
                os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3"),
                os.path.join("assets", "audio", "Opening Theme.mp3"),
            ]
            played = False
            for ap in audio_paths:
                if os.path.exists(ap) and pygame.mixer.get_init():
                    try:
                        pygame.mixer.music.load(ap)
                        pygame.mixer.music.play()
                        played = True
                        break
                    except Exception:
                        pass
            if not played and self.audio_sound is not None:
                try:
                    self.audio_sound.play()
                except Exception:
                    pass

        advanced = False
        while self.dt_accumulator >= frame_duration:
            self.dt_accumulator -= frame_duration
            self.current_frame_idx += 1
            advanced = True

        if advanced:
            if self.current_frame_idx >= self.total_frames:
                self.current_frame_idx = max(0, self.total_frames - 1)
                return self._trigger_finish(skipped=False)
            elif self.mode != "assets" and hasattr(self, "frame_files") and self.frame_files:
                self._load_current_brawl_frame()

        return None

    def _draw_arcade_text(self, surf, text, center_x, center_y, small=False):
        """Renderiza texto usando la fuente oficial arcade Super Street Fighter II Large Colour."""
        f = self.arcade_color_font_small if small else self.arcade_color_font
        if f is not None:
            txt_surf = f.render(text, True, (255, 255, 255))
            surf.blit(txt_surf, (center_x - txt_surf.get_width() // 2, center_y - txt_surf.get_height() // 2))
        else:
            fb = self.font_warn_body if small else self.font_warn_hdr
            txt_surf = fb.render(text, True, (240, 70, 20))
            surf.blit(txt_surf, (center_x - txt_surf.get_width() // 2, center_y - txt_surf.get_height() // 2))

    def draw(self, screen=None) -> None:
        """Renderiza la pantalla correspondiente a la fase activa según elapsed_time."""
        target = screen if screen is not None else self.screen
        if target is None:
            return

        target.fill((0, 0, 0))
        current_phase = self.phase

        # 1. FASE 1: RAM Check Diagnostic (0.0s .. 3.5s)
        if current_phase == self.PHASE_RAM_CHECK:
            t = self.elapsed_time
            num_lines_visible = min(len(self.ram_lines), int(t / self.ram_line_delay) + 1)
            y_start = 220
            scale = 0.65
            line_height = int(66 * scale) + 10
            
            ref_line = "OBJECT      RAM OK"
            if self.boot_font and self.boot_font.sheet is not None:
                block_w, _ = self.boot_font.get_text_size(ref_line, scale=scale)
            else:
                block_w = 480
            start_x = (self.screen_width - block_w) // 2

            for i in range(num_lines_visible):
                line_str = self.ram_lines[i]
                if self.boot_font and self.boot_font.sheet is not None:
                    self.boot_font.draw_text(target, line_str, start_x, y_start + i * line_height, scale=scale)
                else:
                    parts = line_str.split("RAM OK")
                    left_part = parts[0]
                    surf_left = self.font_ram.render(left_part, True, (230, 190, 50))
                    surf_ok = self.font_ram.render("RAM OK", True, (240, 210, 60))
                    target.blit(surf_left, (start_x, y_start + i * line_height))
                    target.blit(surf_ok, (start_x + int(block_w * 0.65), y_start + i * line_height))

        # 2. FASE 2: Title Code (3.5s .. 7.5s) Fade in de opaco a nítido
        elif current_phase == self.PHASE_TITLE_CODE:
            t = self.elapsed_time - 3.5
            if t < 1.0:
                alpha = int(255 * (t / 1.0))
            elif t < 3.2:
                alpha = 255
            else:
                alpha = max(0, int(255 * (1.0 - (t - 3.2) / 0.8)))

            if self.title_code_img is not None:
                temp_surf = self.title_code_img.copy()
                temp_surf.set_alpha(alpha)
                target.blit(temp_surf, (0, 0))
            else:
                temp_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                y_start = 270
                for i, line_str in enumerate(self.code_lines):
                    txt_surf = self.font_code.render(line_str, True, (65, 115, 240))
                    txt_surf.set_alpha(alpha)
                    temp_surf.blit(txt_surf, (self.screen_width // 2 - txt_surf.get_width() // 2, y_start + i * 52))
                target.blit(temp_surf, (0, 0))

        # 3. FASE 3: Warning Screen (7.5s .. 14.5s) con efecto de máquina de escribir de izq a derecha
        elif current_phase == self.PHASE_WARNING:
            t = self.elapsed_time - 7.5
            chars_typed = int(t * 55.0)
            scale = 0.32
            letter_spacing = 2
            line_height = 38

            if self.warning_font and self.warning_font.sheet is not None:
                max_w = 0
                for line_str in self.warn_lines:
                    lw, _ = self.warning_font.get_text_size(line_str, scale=scale, letter_spacing=letter_spacing)
                    if lw > max_w:
                        max_w = lw
                start_x = self.PILLARBOX_WIDTH + (self.TARGET_WIDTH - max_w) // 2
                hdr_w, _ = self.warning_font.get_text_size("WARNING", scale=scale * 1.2, letter_spacing=letter_spacing)
                self.warning_font.draw_text(target, "WARNING", self.screen_width // 2 - hdr_w // 2, 70, scale=scale * 1.2, letter_spacing=letter_spacing)
            else:
                start_x = self.PILLARBOX_WIDTH + 80
                hdr_surf = self.font_warn_hdr.render("WARNING", True, (245, 170, 40))
                target.blit(hdr_surf, (self.screen_width // 2 - hdr_surf.get_width() // 2, 70))

            remaining_chars = chars_typed
            y_start = 145

            for line_str in self.warn_lines:
                if remaining_chars <= 0:
                    break
                chars_for_this_line = min(len(line_str), remaining_chars)
                visible_text = line_str[:chars_for_this_line]
                remaining_chars -= len(line_str)

                if self.warning_font and self.warning_font.sheet is not None:
                    self.warning_font.draw_text(target, visible_text, start_x, y_start, scale=scale, letter_spacing=letter_spacing)
                else:
                    line_surf = self.font_warn_body.render(visible_text, True, (235, 175, 75))
                    target.blit(line_surf, (start_x, y_start))
                y_start += line_height

        # 4. FASE 4: Brawl, Pan, and Title Cutscene (14.5s .. fin)
        elif current_phase == self.PHASE_BRAWL:
            if self.current_surface is not None:
                target.blit(self.current_surface, (self.dest_x, self.dest_y))
            else:
                # No se permite inventar una escena con sprites o fondos si un
                # frame del video no está disponible.
                rect = pygame.Rect(self.dest_x, self.dest_y, self.TARGET_WIDTH, self.TARGET_HEIGHT)
                pygame.draw.rect(target, (0, 0, 0), rect)

        # Pillarboxes arcade de 160px a los lados (formato 4:3 en canvas 1280x720)
        pygame.draw.rect(target, (0, 0, 0), (0, 0, self.PILLARBOX_WIDTH, self.CANVAS_HEIGHT))
        pygame.draw.rect(
            target,
            (0, 0, 0),
            (self.screen_width - self.PILLARBOX_WIDTH, 0, self.PILLARBOX_WIDTH, self.CANVAS_HEIGHT),
        )

    def finish(self) -> str:
        """Finaliza inmediatamente toda la secuencia."""
        return self._trigger_finish(skipped=True)

    def _trigger_finish(self, skipped: bool = False) -> str:
        """Detiene recursos y emite la señal de finalización."""
        if not self.finished:
            self.finished = True
            self.skipped = skipped
            if pygame.mixer.get_init():
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
            if self.audio_sound is not None:
                try:
                    self.audio_sound.stop()
                except Exception:
                    pass
                self.audio_sound = None
            if self._cv2_cap is not None:
                try:
                    self._cv2_cap.release()
                except Exception:
                    pass
                self._cv2_cap = None
            if hasattr(self, "_frame_cache"):
                self._frame_cache.clear()
            if self.on_finish is not None and callable(self.on_finish):
                self.on_finish()
        return "finish"
