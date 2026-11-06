"""
backend/communities/stream_adapter.py
Adaptador de detección de fuentes, captura local de previsualización y validación de perfiles
de Streaming en CCI Communities.

DELIMITACIÓN EXPLÍCITA DE ALCANCE (Fase 0.2):
1. Detección de fuentes (`detect_available_capture_sources`): Inspecciona pantallas reales reportadas
   por el subsistema gráfico activo y procesos reales del sistema operativo (`ps`). Si no hay pantallas
   físicas disponibles (ej. entorno headless o driver `dummy`), devuelve `screens: []` y
   `screen_capture_status: "unavailable"` sin inventar pantallas ficticias.
2. Captura local (`capture_stream_frame`): Obtiene el framebuffer RGB real únicamente cuando existe
   una superficie gráfica activa en Pygame. Si no existe superficie, reporta `status: "unavailable"`.
3. Publicación WebRTC en red (`webrtc_media_publishing`): El backend emite y autoriza sesiones y
   tokens JWT para LiveKit SFU (`start_stream`, `pause_stream`, `stop_stream`), pero la codificación
   y transporte continuo de video/audio en red requiere el cliente WebRTC/LiveKit SFU externo
   (alcance parcial en el backend Python: señalización, control de sesión y captura local).
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Tuple

ALLOWED_RESOLUTIONS = ["720p", "1080p", "1440p", "4k"]
ALLOWED_FPS = [15, 30, 45, 60]
MIN_BITRATE_KBPS = 500
MAX_BITRATE_KBPS = 20000

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
            "scope": "partial_local_detection_and_signaling",
            "display_driver": driver_name,
            "screen_capture_status": "available" if screens else "unavailable",
            "local_preview_capture": "available" if has_real_surface else "unavailable",
            "webrtc_media_publishing": "external_livekit_sfu_client_required",
        },
    }


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
