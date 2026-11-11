"""retro_core_runner.py - Ejecutor universal en Python puro de núcleos Libretro para C.C.I. SYSTEM.
Permite ejecutar ROMs de SNES, MAME/Arcade, Neo-Geo, N64, PS1, NDS y Wii directamente en ventanas Pygame a 60 FPS,
con soporte completo para mandos, teclado, renderizado software/OpenGL, audio estéreo no bloqueante y ejecución aislada por subproceso.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import threading
from pathlib import Path
import numpy as np
import pygame

# Mapeo de botones Libretro (RETRO_DEVICE_ID_JOYPAD_*)
RETRO_DEVICE_JOYPAD = 1
RETRO_DEVICE_ANALOG = 5
RETRO_DEVICE_POINTER = 6

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

RETRO_HW_FRAME_BUFFER_VALID = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1


class RetroSystemInfo(ctypes.Structure):
    _fields_ = [
        ("library_name", ctypes.c_char_p),
        ("library_version", ctypes.c_char_p),
        ("valid_extensions", ctypes.c_char_p),
        ("need_fullpath", ctypes.c_bool),
        ("block_extract", ctypes.c_bool),
    ]


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


class RetroLogCallback(ctypes.Structure):
    _fields_ = [("log", ctypes.c_void_p)]


class RetroHWRenderCallback(ctypes.Structure):
    _fields_ = [
        ("context_type", ctypes.c_uint),
        ("context_reset", ctypes.c_void_p),
        ("get_current_framebuffer", ctypes.c_void_p),
        ("get_proc_address", ctypes.c_void_p),
        ("depth", ctypes.c_bool),
        ("stencil", ctypes.c_bool),
        ("bottom_left_origin", ctypes.c_bool),
        ("version_major", ctypes.c_uint),
        ("version_minor", ctypes.c_uint),
        ("cache_context", ctypes.c_bool),
        ("context_destroy", ctypes.c_void_p),
        ("debug_context", ctypes.c_bool),
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


class _AudioRingBuffer:
    """Buffer circular ligero no bloqueante para evitar stalls del núcleo por CoreAudio."""

    def __init__(self, max_bytes: int = 32768):
        self._buf = bytearray()
        self._max_bytes = max_bytes
        self._lock = threading.Lock()

    def push(self, data: bytes):
        with self._lock:
            self._buf.extend(data)
            if len(self._buf) > self._max_bytes:
                overflow = len(self._buf) - self._max_bytes
                del self._buf[:overflow]

    def pull(self, size: int) -> bytes:
        with self._lock:
            avail = len(self._buf)
            if avail == 0:
                return b"\x00" * size
            take = min(avail, size)
            chunk = bytes(self._buf[:take])
            del self._buf[:take]
        if take < size:
            return chunk + (b"\x00" * (size - take))
        return chunk


def _load_sdl2_lib():
    try:
        pg_dir = Path(pygame.__file__).parent
        for cand in pg_dir.rglob("*SDL2*.dylib"):
            if "SDL2-" in cand.name or cand.name == "libSDL2.dylib":
                lib = ctypes.CDLL(str(cand))
                lib.SDL_GL_GetProcAddress.argtypes = [ctypes.c_char_p]
                lib.SDL_GL_GetProcAddress.restype = ctypes.c_void_p
                return lib
    except Exception:
        pass
    return None


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

        self.pixel_format = RETRO_PIXEL_FORMAT_RGB565
        self.latest_surface: pygame.Surface | None = None
        self.current_width = 256
        self.current_height = 224
        self.aspect_ratio = 0.0
        self.rom_buffer = None
        self.fps = 60.0
        self.sample_rate = 32000.0
        self.audio_stream = None
        self._audio_ring = _AudioRingBuffer()
        self.running = False
        self.paused = False
        self.is_hw_render = False
        self._hw_cb: RetroHWRenderCallback | None = None
        self._sdl_lib = None

        # Estado de botones y stick analógico
        self.joypad_state = [0] * 16
        self.analog_left = [0, 0]
        self.pointer_pressed = False
        self.pointer_x = 0
        self.pointer_y = 0

        self._init_core(self.core_path)

    def _init_core(self, core_path: Path):
        self.core_path = core_path.resolve()
        self.lib = ctypes.CDLL(str(self.core_path))

        # Directorios persistentes para BIOS y partidas guardadas
        root_dir = self.core_path.parent.parent
        sys_dir = (root_dir / "system").resolve()
        save_dir = (root_dir / "saves").resolve()
        sys_dir.mkdir(parents=True, exist_ok=True)
        save_dir.mkdir(parents=True, exist_ok=True)

        self._sys_dir_buf = ctypes.create_string_buffer(str(sys_dir).encode("utf-8"))
        self._sys_dir_ptr = ctypes.c_char_p(ctypes.addressof(self._sys_dir_buf))
        self._save_dir_buf = ctypes.create_string_buffer(str(save_dir).encode("utf-8"))
        self._save_dir_ptr = ctypes.c_char_p(ctypes.addressof(self._save_dir_buf))

        # Opciones estables por núcleo (evita errores OpenGL en N64 / BIOS NeoGeo / boot DS)
        self._core_vars = {
            "melonds_boot_directly": ctypes.create_string_buffer(b"enabled"),
            "mupen64plus-rdp-plugin": ctypes.create_string_buffer(b"angrylion"),
            "mupen64plus-rsp-plugin": ctypes.create_string_buffer(b"hle"),
            "mupen64plus-cpucore": ctypes.create_string_buffer(b"cached_interpreter"),
            "mupen64plus-angrylion-vioverlay": ctypes.create_string_buffer(b"Filtered"),
            "fbneo-neogeo-mode": ctypes.create_string_buffer(b"MVS_EUR"),
        }
        self._core_var_ptrs = {
            k: ctypes.c_char_p(ctypes.addressof(buf)) for k, buf in self._core_vars.items()
        }

        self._setup_c_types()
        self._sys_info = RetroSystemInfo()
        try:
            self.lib.retro_get_system_info(ctypes.byref(self._sys_info))
        except Exception:
            pass

        self._setup_callbacks()
        self.lib.retro_init()

    def _setup_c_types(self):
        self.lib.retro_api_version.restype = ctypes.c_uint
        self.lib.retro_get_system_info.argtypes = [ctypes.POINTER(RetroSystemInfo)]
        self.lib.retro_get_system_info.restype = None
        self.lib.retro_init.restype = None
        self.lib.retro_deinit.restype = None
        self.lib.retro_load_game.argtypes = [ctypes.POINTER(RetroGameInfo)]
        self.lib.retro_load_game.restype = ctypes.c_bool
        self.lib.retro_get_system_av_info.argtypes = [ctypes.POINTER(RetroSystemAvInfo)]
        self.lib.retro_get_system_av_info.restype = None
        self.lib.retro_unload_game.restype = None
        self.lib.retro_run.restype = None
        try:
            self.lib.retro_serialize_size.argtypes = []
            self.lib.retro_serialize_size.restype = ctypes.c_size_t
            self.lib.retro_serialize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            self.lib.retro_serialize.restype = ctypes.c_bool
            self.lib.retro_unserialize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            self.lib.retro_unserialize.restype = ctypes.c_bool
        except Exception:
            pass

    def _setup_callbacks(self):
        self._ctx_reset_type = ctypes.CFUNCTYPE(None)
        self._ctx_destroy_type = ctypes.CFUNCTYPE(None)
        self._get_fb_type = ctypes.CFUNCTYPE(ctypes.c_size_t)
        self._get_proc_type = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)
        self._log_cb_type = ctypes.CFUNCTYPE(
            None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )

        def _get_current_fb():
            return 0

        def _get_proc_address(name):
            if self._sdl_lib is None:
                self._sdl_lib = _load_sdl2_lib()
            if self._sdl_lib is not None and name:
                return self._sdl_lib.SDL_GL_GetProcAddress(name)
            return None

        def _silent_log(level, fmt, a1, a2, a3):
            return

        self._c_get_fb = self._get_fb_type(_get_current_fb)
        self._c_get_proc = self._get_proc_type(_get_proc_address)
        self._c_log_cb = self._log_cb_type(_silent_log)

        # 1. Environment Callback
        self._env_cb_type = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)

        def _env_cb(cmd, data):
            c = cmd & 0xFFFF
            if c == 10 and data:
                # RETRO_ENVIRONMENT_SET_PIXEL_FORMAT
                fmt = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint)).contents.value
                self.pixel_format = fmt
                return True
            if c == 9 and data:
                # RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY
                ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))[0] = self._sys_dir_ptr
                return True
            if c == 31 and data:
                # RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY
                ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))[0] = self._save_dir_ptr
                return True
            if c == 3 and data:
                # RETRO_ENVIRONMENT_GET_CAN_DUPE
                ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))[0] = True
                return True
            if c == 27 and data:
                # RETRO_ENVIRONMENT_GET_LOG_INTERFACE
                ctypes.cast(data, ctypes.POINTER(RetroLogCallback)).contents.log = (
                    ctypes.cast(self._c_log_cb, ctypes.c_void_p).value
                )
                return True
            if c == 14 and data:
                # RETRO_ENVIRONMENT_SET_HW_RENDER (OpenGL / OpenGL Core para Dolphin, etc.)
                cb = ctypes.cast(data, ctypes.POINTER(RetroHWRenderCallback)).contents
                if cb.context_type in (1, 3):
                    if self._sdl_lib is None:
                        self._sdl_lib = _load_sdl2_lib()
                    if self._sdl_lib is None:
                        return False
                    cb.get_current_framebuffer = ctypes.cast(self._c_get_fb, ctypes.c_void_p).value
                    cb.get_proc_address = ctypes.cast(self._c_get_proc, ctypes.c_void_p).value
                    self._hw_cb = cb
                    self.is_hw_render = True
                    return True
                return False
            if c == 15 and data:
                # RETRO_ENVIRONMENT_GET_VARIABLE
                var = ctypes.cast(data, ctypes.POINTER(RetroVariable)).contents
                key = var.key.decode("utf-8", errors="ignore") if var.key else ""
                if key in self._core_var_ptrs:
                    var.value = self._core_var_ptrs[key]
                    return True
            return False

        self._c_env_cb = self._env_cb_type(_env_cb)
        self.lib.retro_set_environment(self._c_env_cb)

        # 2. Video Refresh Callback (0RGB1555, XRGB8888, RGB565 y HW pass-through)
        self._video_cb_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t)

        def _video_cb(data, width, height, pitch):
            if not data or width == 0 or height == 0:
                return
            if data == RETRO_HW_FRAME_BUFFER_VALID:
                self.current_width = width
                self.current_height = height
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
                elif self.pixel_format == RETRO_PIXEL_FORMAT_0RGB1555:
                    buf = (ctypes.c_char * (pitch * height)).from_address(data)
                    raw_15 = np.ndarray((height, width), dtype=np.uint16, buffer=buf, strides=(pitch, 2))
                    r = ((raw_15 >> 10) & 0x1F) << 3
                    g = ((raw_15 >> 5) & 0x1F) << 3
                    b = (raw_15 & 0x1F) << 3
                    rgb = np.dstack((r, g, b)).astype(np.uint8)
                    self.latest_surface = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
            except Exception:
                pass

        self._c_video_cb = self._video_cb_type(_video_cb)
        self.lib.retro_set_video_refresh(self._c_video_cb)

        # 3. Audio Callbacks (Ring buffer no bloqueante para CoreAudio)
        self._audio_sample_type = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)

        def _audio_sample_cb(left, right):
            pass

        self._c_audio_sample_cb = self._audio_sample_type(_audio_sample_cb)
        self.lib.retro_set_audio_sample(self._c_audio_sample_cb)

        self._audio_batch_type = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t)

        def _audio_batch_cb(data, frames):
            if self.audio_stream and not self.paused and frames > 0 and data:
                try:
                    raw_bytes = ctypes.string_at(data, frames * 4)
                    self._audio_ring.push(raw_bytes)
                except Exception:
                    pass
            return frames

        self._c_audio_batch_cb = self._audio_batch_type(_audio_batch_cb)
        self.lib.retro_set_audio_sample_batch(self._c_audio_batch_cb)

        # 4. Input Callbacks
        self._input_poll_type = ctypes.CFUNCTYPE(None)

        def _input_poll_cb():
            pass

        self._c_input_poll_cb = self._input_poll_type(_input_poll_cb)
        self.lib.retro_set_input_poll(self._c_input_poll_cb)

        self._input_state_type = ctypes.CFUNCTYPE(
            ctypes.c_int16, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint
        )

        def _input_state_cb(port, device, index, id_):
            if port == 0:
                if device == RETRO_DEVICE_JOYPAD and 0 <= id_ < len(self.joypad_state):
                    return self.joypad_state[id_]
                elif device == RETRO_DEVICE_ANALOG and index == 0 and id_ in (0, 1):
                    return self.analog_left[id_]
                elif device == RETRO_DEVICE_POINTER:
                    if id_ == 2:
                        return 1 if self.pointer_pressed else 0
                    elif id_ == 0:
                        return self.pointer_x
                    elif id_ == 1:
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

            ring = self._audio_ring

            def _sd_callback(outdata, frames, time_info, status):
                needed = frames * 4
                chunk = ring.pull(needed)
                outdata[:] = chunk

            self.audio_stream = sd.RawOutputStream(
                samplerate=int(self.sample_rate),
                channels=2,
                dtype="int16",
                blocksize=512,
                callback=_sd_callback,
            )
            self.audio_stream.start()
        except Exception:
            self.audio_stream = None

    def _try_load_with_current_core(self, rom_p: Path) -> bool:
        need_fullpath = bool(getattr(self._sys_info, "need_fullpath", False))
        path_bytes = str(rom_p).encode("utf-8")

        if need_fullpath:
            self.rom_buffer = None
            game_info = RetroGameInfo(
                path=path_bytes,
                data=None,
                size=0,
                meta=None,
            )
        else:
            rom_bytes = rom_p.read_bytes()
            self.rom_buffer = (ctypes.c_char * len(rom_bytes)).from_buffer_copy(rom_bytes)
            game_info = RetroGameInfo(
                path=path_bytes,
                data=ctypes.cast(self.rom_buffer, ctypes.c_void_p),
                size=len(rom_bytes),
                meta=None,
            )

        return bool(self.lib.retro_load_game(ctypes.byref(game_info)))

    def load_rom(self, rom_path: str | Path) -> bool:
        rom_p = Path(rom_path).resolve()
        if not rom_p.exists():
            return False

        success = self._try_load_with_current_core(rom_p)

        # Fallback automático: MAME 2003-Plus -> FinalBurn Neo para ROMs Neo-Geo / CPS1 en roms/mame/
        if not success and "mame2003" in self.core_path.name.lower() and rom_p.suffix.lower() == ".zip":
            fbneo_path = self.core_path.parent / "fbneo_libretro.dylib"
            if fbneo_path.exists():
                try:
                    self.lib.retro_deinit()
                except Exception:
                    pass
                self._hw_cb = None
                self.is_hw_render = False
                self._init_core(fbneo_path)
                success = self._try_load_with_current_core(rom_p)

        if success:
            self.running = True
            av_info = RetroSystemAvInfo()
            try:
                self.lib.retro_get_system_av_info(ctypes.byref(av_info))
                if av_info.timing.sample_rate > 8000:
                    self.sample_rate = av_info.timing.sample_rate
                if av_info.timing.fps > 20:
                    self.fps = av_info.timing.fps
                if av_info.geometry.aspect_ratio > 0.1:
                    self.aspect_ratio = float(av_info.geometry.aspect_ratio)
                if av_info.geometry.base_width > 0 and av_info.geometry.base_height > 0:
                    self.current_width = int(av_info.geometry.base_width)
                    self.current_height = int(av_info.geometry.base_height)
            except Exception:
                pass

            if self._hw_cb and self._hw_cb.context_reset:
                try:
                    self._ctx_reset_type(self._hw_cb.context_reset)()
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

        up = is_down(pygame.K_UP)
        down = is_down(pygame.K_DOWN)
        left = is_down(pygame.K_LEFT)
        right = is_down(pygame.K_RIGHT)

        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_UP] = 1 if up else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_DOWN] = 1 if down else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_LEFT] = 1 if left else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_RIGHT] = 1 if right else 0

        self.analog_left[0] = -32767 if left else (32767 if right else 0)
        self.analog_left[1] = -32767 if up else (32767 if down else 0)

        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_A] = (
            1 if (is_down(pygame.K_x) or is_down(pygame.K_SPACE) or is_down(pygame.K_k)) else 0
        )
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_B] = (
            1 if (is_down(pygame.K_z) or is_down(pygame.K_j) or is_down(pygame.K_BACKSPACE)) else 0
        )
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_X] = (
            1 if (is_down(pygame.K_s) or is_down(pygame.K_i) or is_down(pygame.K_c)) else 0
        )
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_Y] = (
            1 if (is_down(pygame.K_a) or is_down(pygame.K_u) or is_down(pygame.K_v)) else 0
        )
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_START] = (
            1 if (is_down(pygame.K_RETURN) or is_down(pygame.K_1)) else 0
        )
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_SELECT] = (
            1 if (is_down(pygame.K_RSHIFT) or is_down(pygame.K_LSHIFT) or is_down(pygame.K_5) or is_down(pygame.K_TAB)) else 0
        )
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_L] = 1 if is_down(pygame.K_q) else 0
        self.joypad_state[RETRO_DEVICE_ID_JOYPAD_R] = 1 if (is_down(pygame.K_w) or is_down(pygame.K_e)) else 0

        if joystick and joystick.get_init():
            try:
                ax_x = joystick.get_axis(0)
                ax_y = joystick.get_axis(1)
                if abs(ax_x) > 0.2:
                    self.analog_left[0] = int(max(-1.0, min(1.0, ax_x)) * 32767)
                if abs(ax_y) > 0.2:
                    self.analog_left[1] = int(max(-1.0, min(1.0, ax_y)) * 32767)

                if ax_x < -0.4:
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_LEFT] = 1
                if ax_x > 0.4:
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_RIGHT] = 1
                if ax_y < -0.4:
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_UP] = 1
                if ax_y > 0.4:
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_DOWN] = 1

                num_buttons = joystick.get_numbuttons()
                if num_buttons > 0 and joystick.get_button(0):
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_B] = 1
                if num_buttons > 1 and joystick.get_button(1):
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_A] = 1
                if num_buttons > 2 and joystick.get_button(2):
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_Y] = 1
                if num_buttons > 3 and joystick.get_button(3):
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_X] = 1
                if num_buttons > 6 and joystick.get_button(6):
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_SELECT] = 1
                if num_buttons > 7 and joystick.get_button(7):
                    self.joypad_state[RETRO_DEVICE_ID_JOYPAD_START] = 1
            except Exception:
                pass

    def update_pointer_from_mouse(self, mx: int, my: int, pressed: bool, view_rect: tuple[int, int, int, int]):
        dx, dy, dw, dh = view_rect
        if not pressed or dw <= 0 or dh <= 0:
            self.pointer_pressed = False
            self.pointer_x = 0
            self.pointer_y = 0
            return
        if dx <= mx <= dx + dw and dy <= my <= dy + dh:
            nx = (mx - dx) / float(dw)
            ny = (my - dy) / float(dh)
            self.pointer_x = int(max(-32767, min(32767, (nx * 2.0 - 1.0) * 32767)))
            self.pointer_y = int(max(-32767, min(32767, (ny * 2.0 - 1.0) * 32767)))
            self.pointer_pressed = True
        else:
            self.pointer_pressed = False

    def serialize_state(self) -> bytes | None:
        if not self.running:
            return None
        try:
            sz = int(self.lib.retro_serialize_size())
            if sz <= 0:
                return None
            buf = ctypes.create_string_buffer(sz)
            if self.lib.retro_serialize(ctypes.cast(buf, ctypes.c_void_p), sz):
                return bytes(buf.raw)
        except Exception:
            pass
        return None

    def unserialize_state(self, state_bytes: bytes) -> bool:
        if not self.running or not state_bytes:
            return False
        try:
            sz = len(state_bytes)
            buf = ctypes.create_string_buffer(state_bytes, sz)
            return bool(self.lib.retro_unserialize(ctypes.cast(buf, ctypes.c_void_p), sz))
        except Exception:
            return False

    def step_frame(self):
        if self.running and not self.paused:
            self.lib.retro_run()

    def render_to(
        self,
        target_surface: pygame.Surface,
        screen_w: int = 1280,
        screen_h: int = 720,
        top_offset: int = 0,
        bottom_margin: int = 0,
    ) -> tuple[int, int, int, int]:
        avail_h = max(1, screen_h - top_offset - bottom_margin)
        if self.latest_surface:
            sw, sh = self.latest_surface.get_size()
            if self.aspect_ratio > 0.1:
                eff_w = sh * self.aspect_ratio
                scale = min(screen_w / max(1.0, eff_w), avail_h / max(1.0, float(sh)))
                dw = max(1, int(eff_w * scale))
                dh = max(1, int(sh * scale))
            else:
                scale = min(screen_w / max(1, sw), avail_h / max(1, sh))
                dw = max(1, int(sw * scale))
                dh = max(1, int(sh * scale))

            scaled = pygame.transform.scale(self.latest_surface, (dw, dh))
            dx = (screen_w - dw) // 2
            dy = top_offset + (avail_h - dh) // 2

            target_surface.fill((0, 0, 0))
            target_surface.blit(scaled, (dx, dy))
            return (dx, dy, dw, dh)
        return (0, top_offset, screen_w, avail_h)

    def unload(self):
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None

        if self._hw_cb and self._hw_cb.context_destroy:
            try:
                self._ctx_destroy_type(self._hw_cb.context_destroy)()
            except Exception:
                pass
            self._hw_cb = None

        if self.running:
            try:
                self.lib.retro_unload_game()
            except Exception:
                pass
            self.running = False

        try:
            self.lib.retro_deinit()
        except Exception:
            pass

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

        needs_gl = "dolphin" in self.core_path.name.lower()
        screen = None
        if needs_gl:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
            pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
            screen = pygame.display.set_mode((sw, sh), pygame.OPENGL | pygame.DOUBLEBUF)
            pygame.display.set_caption(title)

        if not self.load_rom(rp):
            if needs_gl:
                try:
                    pygame.display.quit()
                except Exception:
                    pass
            raise RuntimeError(f"No se pudo cargar la ROM: {rp}")

        if not needs_gl:
            screen = pygame.display.set_mode((sw, sh))
            pygame.display.set_caption(title)

        clock = pygame.time.Clock()
        target_fps = max(30, min(60, int(round(self.fps)))) if self.fps else 60

        joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for j in joysticks:
            if not j.get_init():
                try:
                    j.init()
                except Exception:
                    pass

        running = True
        while running:
            clock.tick(target_fps)
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
            if not self.is_hw_render and screen is not None:
                self.render_to(screen, sw, sh)
            pygame.display.flip()

        self.unload()
        try:
            pygame.display.quit()
        except Exception:
            pass


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ejecutor Libretro aislado C.C.I. SYSTEM")
    parser.add_argument("--core", required=True, help="Ruta al núcleo .dylib/.so/.dll")
    parser.add_argument("--rom", required=True, help="Ruta al archivo ROM")
    parser.add_argument("--title", default="C.C.I. SYSTEM — Retro Core 60 FPS", help="Título de ventana")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv)

    try:
        runner = LibretroRunner(
            core_path=args.core,
            rom_path=args.rom,
            screen_w=args.width,
            screen_h=args.height,
        )
        runner.run_standalone(title=args.title)
        return 0
    except Exception as exc:
        print(f"[LibretroRunner] Error: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
