"""retro_core_runner.py - Ejecutor universal en Python puro de núcleos Libretro para C.C.I. SYSTEM.
Permite ejecutar ROMs de SNES, MAME/Arcade y otras consolas directamente en ventanas Pygame a 60 FPS,
con soporte completo para mandos, teclado, audio estéreo en tiempo real y controles de estado (Pause, Volver).
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path
import numpy as np
import pygame

# Mapeo de botones Libretro (RETRO_DEVICE_ID_JOYPAD_*)
RETRO_DEVICE_JOYPAD = 1
RETRO_DEVICE_ID_JOYPAD_B = 0
RETRO_DEVICE_ID_JOYPAD_Y = 1
RETRO_DEVICE_ID_JOYPAD_SELECT = 2
RETRO_DEVICE_ID_JOYPAD_START = 3
RETRO_DEVICE_ID_JOYPAD_UP = 4
RETRO_DEVICE_ID_JOYPAD_DOWN = 5
RETRO_DEVICE_ID_JOYPAD_LEFT = 6
RETRO_DEVICE_ID_JOYPAD_RIGHT = 7
RETRO_DEVICE_ID_JOYPAD_A = 8
RETRO_DEVICE_ID_JOYPAD_X = 9
RETRO_DEVICE_ID_JOYPAD_L = 10
RETRO_DEVICE_ID_JOYPAD_R = 11

RETRO_PIXEL_FORMAT_0RGB1555 = 0
RETRO_PIXEL_FORMAT_XRGB8888 = 1
RETRO_PIXEL_FORMAT_RGB565 = 2


class RetroGameInfo(ctypes.Structure):
    _fields_ = [
        ("path", ctypes.c_char_p),
        ("data", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
        ("meta", ctypes.c_char_p),
    ]


class RetroVariable(ctypes.Structure):
    _fields_ = [
        ("key", ctypes.c_char_p),
        ("value", ctypes.c_char_p),
    ]


class RetroSystemAvInfo(ctypes.Structure):
    class Geometry(ctypes.Structure):
        _fields_ = [
            ("base_width", ctypes.c_uint),
            ("base_height", ctypes.c_uint),
            ("max_width", ctypes.c_uint),
            ("max_height", ctypes.c_uint),
            ("aspect_ratio", ctypes.c_float),
        ]

    class Timing(ctypes.Structure):
        _fields_ = [
            ("fps", ctypes.c_double),
            ("sample_rate", ctypes.c_double),
        ]

    _fields_ = [
        ("geometry", Geometry),
        ("timing", Timing),
    ]


class LibretroRunner:
    def __init__(
        self,
        core_path: str | Path,
        rom_path: str | Path | None = None,
        screen_w: int = 1280,
        screen_h: int = 720,
    ):
        self.core_path = Path(core_path).resolve()
        if not self.core_path.exists():
            raise FileNotFoundError(f"Núcleo no encontrado: {self.core_path}")

        self.rom_path = Path(rom_path).resolve() if rom_path else None
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.lib = ctypes.CDLL(str(self.core_path))
        self.pixel_format = RETRO_PIXEL_FORMAT_RGB565
        self.latest_surface: pygame.Surface | None = None
        self.current_width = 256
        self.current_height = 224
        self.rom_buffer = None
        self.fps = 60.0
        self.sample_rate = 32000.0
        self.audio_stream = None
        self.running = False
        self.paused = False

        # Estado de botones
        self.joypad_state = [0] * 16
        self.pointer_pressed = False
        self.pointer_x = 0
        self.pointer_y = 0

        # Directorio persistente para BIOS oficiales (system/bios7.bin, bios9.bin, etc.)
        self._sys_dir_path = str((self.core_path.parent.parent / "system").resolve()).encode("utf-8")
        self._sys_dir_buf = ctypes.create_string_buffer(self._sys_dir_path)
        self._sys_dir_ptr = ctypes.c_char_p(ctypes.addressof(self._sys_dir_buf))

        self._setup_c_types()
        self._setup_callbacks()
        self.lib.retro_init()

    def _setup_c_types(self):
        self.lib.retro_api_version.restype = ctypes.c_uint
        self.lib.retro_init.restype = None
        self.lib.retro_deinit.restype = None
        self.lib.retro_load_game.argtypes = [ctypes.POINTER(RetroGameInfo)]
        self.lib.retro_load_game.restype = ctypes.c_bool
        self.lib.retro_get_system_av_info.argtypes = [ctypes.POINTER(RetroSystemAvInfo)]
        self.lib.retro_get_system_av_info.restype = None
        self.lib.retro_unload_game.restype = None
        self.lib.retro_run.restype = None

    def _setup_callbacks(self):
        # 1. Environment Callback
        self._env_cb_type = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)

        def _env_cb(cmd, data):
            if cmd == 10 and data:
                fmt = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint)).contents.value
                self.pixel_format = fmt
                return True
            if cmd == 9 and data:
                ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
                ptr[0] = self._sys_dir_ptr
                return True
            if cmd == 3 and data:
                ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))
                ptr.contents = ctypes.c_bool(True)
                return True
            if cmd == 15 and data:
                # RETRO_ENVIRONMENT_GET_VARIABLE
                var = ctypes.cast(data, ctypes.POINTER(RetroVariable)).contents
                key = var.key.decode("utf-8", errors="ignore") if var.key else ""
                if key == "melonds_boot_directly":
                    var.value = b"enabled"
                    return True
            return False

        self._c_env_cb = self._env_cb_type(_env_cb)
        self.lib.retro_set_environment(self._c_env_cb)

        # 2. Video Refresh Callback con soporte de Stride/Pitch
        self._video_cb_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t)

        def _video_cb(data, width, height, pitch):
            if not data or width == 0 or height == 0:
                return

            self.current_width = width
            self.current_height = height

            try:
                if self.pixel_format == RETRO_PIXEL_FORMAT_RGB565:
                    buf = (ctypes.c_char * (pitch * height)).from_address(data)
                    raw_16 = np.ndarray((height, width), dtype=np.uint16, buffer=buf, strides=(pitch, 2))
                    r = ((raw_16 >> 11) & 0x1F) << 3
                    g = ((raw_16 >> 5) & 0x3F) << 2
                    b = (raw_16 & 0x1F) << 3
                    rgb = np.dstack((r, g, b)).astype(np.uint8)
                    self.latest_surface = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
                elif self.pixel_format == RETRO_PIXEL_FORMAT_XRGB8888:
                    buf = (ctypes.c_char * (pitch * height)).from_address(data)
                    raw_32 = np.ndarray((height, width), dtype=np.uint32, buffer=buf, strides=(pitch, 4))
                    r = (raw_32 >> 16) & 0xFF
                    g = (raw_32 >> 8) & 0xFF
                    b = raw_32 & 0xFF
                    rgb = np.dstack((r, g, b)).astype(np.uint8)
                    self.latest_surface = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
            except Exception:
                pass

        self._c_video_cb = self._video_cb_type(_video_cb)
        self.lib.retro_set_video_refresh(self._c_video_cb)

        # 3. Audio Callbacks (Transmisión Estéreo en Tiempo Real a Apple Core Audio)
        self._audio_sample_type = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)
        def _audio_sample_cb(left, right): pass
        self._c_audio_sample_cb = self._audio_sample_type(_audio_sample_cb)
        self.lib.retro_set_audio_sample(self._c_audio_sample_cb)

        self._audio_batch_type = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t)

        def _audio_batch_cb(data, frames):
            if self.audio_stream and not self.paused and frames > 0:
                try:
                    num_bytes = frames * 4
                    raw_bytes = ctypes.string_at(data, num_bytes)
                    self.audio_stream.write(raw_bytes)
                except Exception:
                    pass
            return frames

        self._c_audio_batch_cb = self._audio_batch_type(_audio_batch_cb)
        self.lib.retro_set_audio_sample_batch(self._c_audio_batch_cb)

        # 4. Input Callbacks
        self._input_poll_type = ctypes.CFUNCTYPE(None)
        def _input_poll_cb(): pass
        self._c_input_poll_cb = self._input_poll_type(_input_poll_cb)
        self.lib.retro_set_input_poll(self._c_input_poll_cb)

        self._input_state_type = ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
        def _input_state_cb(port, device, index, id_):
            if port == 0:
                if device == RETRO_DEVICE_JOYPAD and 0 <= id_ < len(self.joypad_state):
                    return self.joypad_state[id_]
                elif device == 6:  # RETRO_DEVICE_POINTER (touchscreen)
                    if id_ == 2:  # PRESSED
                        return 1 if self.pointer_pressed else 0
                    elif id_ == 0:  # X
                        return self.pointer_x
                    elif id_ == 1:  # Y
                        return self.pointer_y
            return 0
        self._c_input_state_cb = self._input_state_type(_input_state_cb)
        self.lib.retro_set_input_state(self._c_input_state_cb)

    def _init_audio(self):
        try:
            import sounddevice as sd
            if self.audio_stream:
                try:
                    self.audio_stream.stop()
                    self.audio_stream.close()
                except Exception:
                    pass
            self.audio_stream = sd.RawOutputStream(
                samplerate=int(self.sample_rate),
                channels=2,
                dtype="int16",
                blocksize=512,
            )
            self.audio_stream.start()
        except Exception as e:
            self.audio_stream = None

    def load_rom(self, rom_path: str | Path) -> bool:
        rom_p = Path(rom_path).resolve()
        if not rom_p.exists():
            return False

        rom_bytes = rom_p.read_bytes()
        self.rom_buffer = (ctypes.c_char * len(rom_bytes)).from_buffer_copy(rom_bytes)

        game_info = RetroGameInfo(
            path=str(rom_p).encode("utf-8"),
            data=ctypes.cast(self.rom_buffer, ctypes.c_void_p),
            size=len(rom_bytes),
            meta=None,
        )

        success = self.lib.retro_load_game(ctypes.byref(game_info))
        if success:
            self.running = True
            # Extraer timing y audio rate exactos
            av_info = RetroSystemAvInfo()
            try:
                self.lib.retro_get_system_av_info(ctypes.byref(av_info))
                if av_info.timing.sample_rate > 8000:
                    self.sample_rate = av_info.timing.sample_rate
                if av_info.timing.fps > 20:
                    self.fps = av_info.timing.fps
            except Exception:
                pass
            self._init_audio()
        return success

    def update_input(self, keys, joystick=None):
        def is_down(k):
            try:
                return bool(keys[k])
            except Exception:
                return False

        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_UP] = 1 if is_down(pygame.K_UP) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_DOWN] = 1 if is_down(pygame.K_DOWN) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_LEFT] = 1 if is_down(pygame.K_LEFT) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_RIGHT] = 1 if is_down(pygame.K_RIGHT) else 0

        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_A] = 1 if is_down(pygame.K_x) or is_down(pygame.K_RETURN) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_B] = 1 if is_down(pygame.K_z) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_X] = 1 if is_down(pygame.K_s) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_Y] = 1 if is_down(pygame.K_a) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_START] = 1 if is_down(pygame.K_RETURN) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_SELECT] = 1 if is_down(pygame.K_RSHIFT) or is_down(pygame.K_LSHIFT) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_L] = 1 if is_down(pygame.K_q) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_R] = 1 if is_down(pygame.K_w) else 0

        if joystick and joystick.get_init():
            try:
                ax_x = joystick.get_axis(0)
                ax_y = joystick.get_axis(1)
                if ax_x < -0.4: self.joypad_state[RETRO_DEVICE_ID_JOYPAD_LEFT] = 1
                if ax_x > 0.4:  self.joypad_state[RETRO_DEVICE_ID_JOYPAD_RIGHT] = 1
                if ax_y < -0.4: self.joypad_state[RETRO_DEVICE_ID_JOYPAD_UP] = 1
                if ax_y > 0.4:  self.joypad_state[RETRO_DEVICE_ID_JOYPAD_DOWN] = 1

                num_buttons = joystick.get_numbuttons()
                if num_buttons > 0 and joystick.get_button(0): self.joypad_state[RETRO_DEVICE_ID_JOYPAD_B] = 1
                if num_buttons > 1 and joystick.get_button(1): self.joypad_state[RETRO_DEVICE_ID_JOYPAD_A] = 1
                if num_buttons > 2 and joystick.get_button(2): self.joypad_state[RETRO_DEVICE_ID_JOYPAD_Y] = 1
                if num_buttons > 3 and joystick.get_button(3): self.joypad_state[RETRO_DEVICE_ID_JOYPAD_X] = 1
            except Exception:
                pass

    def step_frame(self):
        if self.running and not self.paused:
            self.lib.retro_run()

    def render_to(self, target_surface: pygame.Surface, screen_w: int = 1280, screen_h: int = 720):
        if self.latest_surface:
            sw, sh = self.latest_surface.get_size()
            scale = min(screen_w / sw, screen_h / sh)
            dw = int(sw * scale)
            dh = int(sh * scale)
            scaled = pygame.transform.scale(self.latest_surface, (dw, dh))
            dx = (screen_w - dw) // 2
            dy = (screen_h - dh) // 2

            target_surface.fill((0, 0, 0))
            target_surface.blit(scaled, (dx, dy))

    def unload(self):
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None

        if self.running:
            try:
                self.lib.retro_unload_game()
                self.lib.retro_deinit()
            except Exception:
                pass
            self.running = False

    def run_standalone(
        self,
        rom_path: str | Path | None = None,
        screen_w: int | None = None,
        screen_h: int | None = None,
        title: str = "C.C.I. SYSTEM — Retro Core 60 FPS",
    ):
        """Bucle de ejecución interactivo completo a 60 FPS con teclado, gamepad y audio."""
        rp = rom_path or self.rom_path
        if not rp:
            raise ValueError("No se especificó rom_path para ejecutar.")

        sw = screen_w or self.screen_w
        sh = screen_h or self.screen_h

        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()
        if not pygame.joystick.get_init():
            try:
                pygame.joystick.init()
            except Exception:
                pass

        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.pause()
        except Exception:
            pass

        if not self.load_rom(rp):
            raise RuntimeError(f"No se pudo cargar la ROM: {rp}")

        screen = pygame.display.set_mode((sw, sh))
        pygame.display.set_caption(title)
        clock = pygame.time.Clock()

        joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for j in joysticks:
            if not j.get_init():
                try:
                    j.init()
                except Exception:
                    pass

        running = True
        while running:
            clock.tick(60)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.JOYBUTTONDOWN and event.button in (6, 8):
                    running = False

            keys = pygame.key.get_pressed()
            joy = joysticks[0] if joysticks else None
            self.update_input(keys, joy)
            self.step_frame()
            self.render_to(screen, sw, sh)
            pygame.display.flip()

        self.unload()
        try:
            pygame.display.quit()
        except Exception:
            pass
