"""
backend/communities/stream_adapter.py
Adaptador de detección de fuentes, captura real de pantalla/ventana/juego y validación de perfiles
de Streaming WebRTC en CCI Communities (P1-B).
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import threading
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_RESOLUTIONS = ["720p", "1080p", "1440p", "4k"]
ALLOWED_FPS = [15, 30, 45, 60]
MIN_BITRATE_KBPS = 500
MAX_BITRATE_KBPS = 20000

RESOLUTION_DIMENSIONS: Dict[str, Tuple[int, int]] = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}

STREAM_PROFILES = {
    "720p_30fps": {"resolution": "720p", "fps": 30, "bitrate_kbps": 1500},
    "720p_60fps": {"resolution": "720p", "fps": 60, "bitrate_kbps": 2500},
    "1080p_30fps": {"resolution": "1080p", "fps": 30, "bitrate_kbps": 3000},
    "1080p_60fps": {"resolution": "1080p", "fps": 60, "bitrate_kbps": 4500},
    "1440p_60fps": {"resolution": "1440p", "fps": 60, "bitrate_kbps": 8000},
}

# Catálogo de títulos de C.C.I. SYSTEM cuyos procesos se verifican contra el SO
CCI_TITLES = [
    {"game_id": "davinci-fighter", "title": "Davinci-Fighter", "process_name": "Davinci-Fighter"},
    {"game_id": "metal-slug", "title": "METAL SLUG", "process_name": "metal_slug"},
    {"game_id": "metal-slug-x", "title": "METAL SLUG X", "process_name": "mslugx"},
    {"game_id": "mortal-kombat-2", "title": "Mortal Kombat II", "process_name": "mk2"},
    {"game_id": "street-fighter-2", "title": "Street Fighter II", "process_name": "sf2"},
    {"game_id": "doom", "title": "DOOM (1993)", "process_name": "doom"},
    {"game_id": "cuphead", "title": "Cuphead", "process_name": "cuphead"},
    {"game_id": "super-mario-world", "title": "Super Mario World", "process_name": "smw"},
    {"game_id": "sonic-the-hedgehog-2", "title": "Sonic the Hedgehog 2", "process_name": "sonic2"},
    {"game_id": "chrono-trigger", "title": "Chrono Trigger", "process_name": "chrono"},
]


class StreamValidationError(Exception):
    def __init__(self, message: str, code: str = "INVALID_STREAM_PROFILE"):
        super().__init__(message)
        self.message = message
        self.code = code


def validate_stream_profile(resolution: str, fps: int, bitrate_kbps: int) -> Tuple[str, int, int]:
    """
    Valida los parámetros técnicos de transmisión de video y audio.
    Lanza StreamValidationError si no cumplen los límites técnicos.
    """
    res_clean = str(resolution).lower().strip()
    if res_clean not in ALLOWED_RESOLUTIONS:
        raise StreamValidationError(
            f"Resolución no soportada '{resolution}'. Permitidas: {', '.join(ALLOWED_RESOLUTIONS)}",
            "INVALID_RESOLUTION",
        )

    if int(fps) not in ALLOWED_FPS:
        raise StreamValidationError(
            f"FPS no soportados '{fps}'. Permitidos: {', '.join(map(str, ALLOWED_FPS))}",
            "INVALID_FPS",
        )

    if not (MIN_BITRATE_KBPS <= int(bitrate_kbps) <= MAX_BITRATE_KBPS):
        raise StreamValidationError(
            f"Bitrate {bitrate_kbps} kbps fuera de rango ({MIN_BITRATE_KBPS}-{MAX_BITRATE_KBPS} kbps)",
            "INVALID_BITRATE",
        )

    return res_clean, int(fps), int(bitrate_kbps)


def _list_running_process_names() -> List[str]:
    """Inspecciona procesos activos del sistema operativo de forma segura (sin bloquear)."""
    try:
        if os.name == "posix":
            proc = subprocess.run(
                ["ps", "-eo", "comm="],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
            if proc.returncode == 0:
                return [line.strip().lower() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def detect_available_capture_sources(force_headless: bool = False) -> Dict[str, Any]:
    """
    Detecta fuentes de captura reales disponibles en el sistema operativo.
    No inventa pantallas ficticias si no hay un display físico activo.
    Separa explícitamente los estados de detección, captura local y publicación WebRTC.
    """
    screens: List[Dict[str, Any]] = []
    has_real_surface = False
    driver_name = "uninitialized"

    if not force_headless:
        try:
            import pygame
            if pygame.display.get_init():
                driver_name = pygame.display.get_driver() or "unknown"
                surf = pygame.display.get_surface()
                has_real_surface = surf is not None
                if driver_name != "dummy":
                    sizes = pygame.display.get_desktop_sizes()
                    for idx, (w, h) in enumerate(sizes):
                        if w > 0 and h > 0:
                            screens.append({
                                "id": f"screen:{idx}",
                                "type": "screen",
                                "name": f"Pantalla {'Principal' if idx == 0 else idx + 1} ({w}x{h})",
                                "width": int(w),
                                "height": int(h),
                                "is_primary": idx == 0,
                                "driver": driver_name,
                            })
        except Exception:
            pass

    running_procs = _list_running_process_names() if not force_headless else []
    python_active = any("python" in p for p in running_procs)

    # Detección adicional de pantallas físicas vía Qt cuando no estamos en offscreen/headless
    if not force_headless and not screens:
        try:
            from PySide6.QtGui import QGuiApplication

            qapp = QGuiApplication.instance()
            if qapp is not None and (QGuiApplication.platformName() or "").strip().lower() != "offscreen":
                driver_name = f"qt:{QGuiApplication.platformName()}"
                for idx, scr in enumerate(QGuiApplication.screens()):
                    geom = scr.geometry()
                    w, h = int(geom.width()), int(geom.height())
                    if w > 0 and h > 0:
                        screens.append({
                            "id": f"screen:{idx}",
                            "type": "screen",
                            "name": f"Pantalla {'Principal' if idx == 0 else idx + 1} ({w}x{h})",
                            "width": w,
                            "height": h,
                            "is_primary": idx == 0,
                            "driver": driver_name,
                        })
        except Exception:
            pass

    has_livekit_video = False
    if not force_headless:
        try:
            has_livekit_video = importlib.util.find_spec("livekit.rtc") is not None
        except Exception:
            has_livekit_video = False

    windows: List[Dict[str, Any]] = []
    if python_active or has_real_surface:
        windows.append({
            "id": "window:cci_launcher",
            "type": "window",
            "name": "C.C.I. SYSTEM Launcher (1280x720)",
            "app_name": "CCI-Launcher",
            "is_active": bool(python_active),
        })

    games: List[Dict[str, Any]] = []
    for g in CCI_TITLES:
        pname = g["process_name"].lower()
        is_running = any(pname in proc for proc in running_procs)
        games.append({
            "id": f"game:{g['game_id']}",
            "type": "game",
            "game_id": g["game_id"],
            "name": g["title"],
            "process_name": g["process_name"],
            "has_direct_audio": True,
            "is_running": bool(is_running),
        })

    return {
        "screens": screens,
        "windows": windows,
        "games": games,
        "profiles": STREAM_PROFILES,
        "subsystem_status": {
            "scope": "livekit_webrtc_desktop_capture" if (has_livekit_video and not force_headless) else "partial_local_detection_and_signaling",
            "display_driver": driver_name,
            "screen_capture_status": "available" if screens else "unavailable",
            "local_preview_capture": "available" if (has_real_surface or screens or windows) else "unavailable",
            "webrtc_media_publishing": "livekit_video_ready" if (has_livekit_video and not force_headless) else "external_livekit_sfu_client_required",
        },
    }


def parse_resolution_dimensions(
    resolution: str = "720p",
    max_width: int = 1920,
    max_height: int = 1080,
) -> Tuple[int, int]:
    """Convierte una resolución nominal ('720p', '1080p', etc.) en dimensiones pares para WebRTC."""
    res_clean = str(resolution or "720p").lower().strip()
    w, h = RESOLUTION_DIMENSIONS.get(res_clean, (1280, 720))
    w = min(int(w), max(2, int(max_width)))
    h = min(int(h), max(2, int(max_height)))
    # Asegurar múltiplos de 2 requeridos por codificadores VP8/H264
    return max(2, w - (w % 2)), max(2, h - (h % 2))


def resize_rgba_frame(
    width: int,
    height: int,
    rgba_bytes: bytes,
    target_width: int,
    target_height: int,
) -> Tuple[int, int, bytes]:
    """Redimensiona un buffer RGBA manteniendo proporciones pares cuando difiere del objetivo."""
    tw = max(2, int(target_width) - (int(target_width) % 2))
    th = max(2, int(target_height) - (int(target_height) % 2))
    if width == tw and height == th and len(rgba_bytes) == tw * th * 4:
        return tw, th, rgba_bytes

    try:
        from PIL import Image

        img = Image.frombytes("RGBA", (int(width), int(height)), rgba_bytes)
        if img.size != (tw, th):
            img = img.resize((tw, th), Image.Resampling.BILINEAR)
        return tw, th, img.tobytes()
    except Exception:
        pass

    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(rgba_bytes, dtype=np.uint8).reshape((int(height), int(width), 4))
        resized = cv2.resize(arr, (tw, th), interpolation=cv2.INTER_LINEAR)
        return tw, th, np.ascontiguousarray(resized).tobytes()
    except Exception:
        return int(width), int(height), rgba_bytes


def _qpixmap_to_rgba_frame(
    pix: Any,
    target_width: int,
    target_height: int,
) -> Optional[Tuple[int, int, bytes]]:
    """Convierte un QPixmap a bytes RGBA8888 compactos y redimensionados."""
    if pix is None or pix.isNull() or pix.width() <= 0 or pix.height() <= 0:
        return None
    from PySide6.QtGui import QImage

    img = pix.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = int(img.width()), int(img.height())
    bpl = int(img.bytesPerLine())
    raw = bytes(img.constBits())
    rgba = raw[: w * h * 4] if bpl == w * 4 else b"".join(
        raw[r * bpl : r * bpl + w * 4] for r in range(h)
    )
    return resize_rgba_frame(w, h, rgba, target_width, target_height)


def capture_qwidget_rgba(
    widget: Any,
    target_width: int = 1280,
    target_height: int = 720,
) -> Optional[Tuple[int, int, bytes]]:
    """Captura los píxeles renderizados reales de un QWidget en formato RGBA8888."""
    if widget is None or threading.current_thread() is not threading.main_thread():
        return None
    try:
        return _qpixmap_to_rgba_frame(widget.grab(), target_width, target_height)
    except Exception:
        return None


def capture_source_rgba(
    source_id: str = "screen:0",
    target_width: int = 1280,
    target_height: int = 720,
    window_widget: Any = None,
) -> Optional[Tuple[int, int, bytes]]:
    """Captura un frame RGBA real de pantalla, ventana Qt o superficie Pygame.

    Devuelve `(width, height, rgba_bytes)` o `None` si la fuente no está disponible.
    """
    src = str(source_id or "screen:0").strip()
    tw = max(2, int(target_width) - (int(target_width) % 2))
    th = max(2, int(target_height) - (int(target_height) % 2))

    # 1. Ventana de la aplicación Qt (funciona tanto en pantalla física como en offscreen)
    if src.startswith("window:") and window_widget is not None:
        grabbed = capture_qwidget_rgba(window_widget, tw, th)
        if grabbed is not None:
            return grabbed

    # 2. Superficie activa de Pygame (juegos integrados o ventana principal SDL)
    if src.startswith("game:") or src.startswith("window:") or src == "pygame":
        try:
            import pygame

            if pygame.display.get_init():
                surf = pygame.display.get_surface()
                if surf is not None:
                    w, h = surf.get_size()
                    if w > 0 and h > 0:
                        raw_rgba = pygame.image.tobytes(surf, "RGBA")
                        return resize_rgba_frame(w, h, raw_rgba, tw, th)
        except Exception:
            pass
        if src.startswith("game:") and window_widget is not None:
            grabbed = capture_qwidget_rgba(window_widget, tw, th)
            if grabbed is not None:
                return grabbed

    # 3. Captura de monitor físico vía Qt Screen o Pillow ImageGrab
    if src.startswith("screen:"):
        try:
            idx = int(src.split(":", 1)[1])
        except Exception:
            idx = 0

        if threading.current_thread() is threading.main_thread():
            try:
                from PySide6.QtGui import QGuiApplication

                qapp = QGuiApplication.instance()
                if qapp is not None and (QGuiApplication.platformName() or "").strip().lower() != "offscreen":
                    screens = QGuiApplication.screens()
                    if 0 <= idx < len(screens):
                        grabbed = _qpixmap_to_rgba_frame(screens[idx].grabWindow(0), tw, th)
                        if grabbed is not None:
                            return grabbed
            except Exception:
                pass

        # Fallback fuera del hilo Qt (no disponible en entornos headless sin compositor)
        if os.getenv("QT_QPA_PLATFORM", "").strip().lower() != "offscreen":
            try:
                from PIL import ImageGrab

                snap = ImageGrab.grab()
                if snap is not None and snap.width > 0 and snap.height > 0:
                    rgba_img = snap.convert("RGBA")
                    return resize_rgba_frame(rgba_img.width, rgba_img.height, rgba_img.tobytes(), tw, th)
            except Exception:
                pass

    return None


def capture_stream_frame() -> Dict[str, Any]:
    """
    Captura un frame instantáneo de la superficie activa de Pygame para previsualización local.
    Si no existe superficie gráfica activa, devuelve `captured: False` y `status: 'unavailable'`
    sin generar buffers ficticios.
    """
    try:
        import pygame
        if pygame.display.get_init():
            surf = pygame.display.get_surface()
            if surf is not None:
                w, h = surf.get_size()
                raw_rgb = pygame.image.tobytes(surf, "RGB")
                return {
                    "captured": True,
                    "status": "available",
                    "source": "pygame_display_surface",
                    "width": w,
                    "height": h,
                    "pixel_format": "RGB24",
                    "byte_length": len(raw_rgb),
                }
    except Exception:
        pass
    return {
        "captured": False,
        "status": "unavailable",
        "source": "none",
        "width": 0,
        "height": 0,
        "pixel_format": "none",
        "byte_length": 0,
    }
