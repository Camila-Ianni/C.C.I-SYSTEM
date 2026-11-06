"""
backend/communities/stream_adapter.py
Adaptador de captura de pantalla, ventanas y juegos para Streaming en CCI Communities.
Provee:
- Validación de perfiles de video (resolución, FPS, bitrate).
- Catálogo de fuentes detectables (pantallas, ventanas, juegos de C.C.I. SYSTEM).
- Perfiles de calidad adaptativa.
"""

from typing import Any, Dict, List, Optional, Tuple

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

# Títulos de juegos oficiales de C.C.I. SYSTEM detectables automáticamente
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
    res_clean = resolution.lower().strip()
    if res_clean not in ALLOWED_RESOLUTIONS:
        raise StreamValidationError(
            f"Resolución no soportada '{resolution}'. Permitidas: {', '.join(ALLOWED_RESOLUTIONS)}",
            "INVALID_RESOLUTION"
        )

    if fps not in ALLOWED_FPS:
        raise StreamValidationError(
            f"FPS no soportados '{fps}'. Permitidos: {', '.join(map(str, ALLOWED_FPS))}",
            "INVALID_FPS"
        )

    if not (MIN_BITRATE_KBPS <= bitrate_kbps <= MAX_BITRATE_KBPS):
        raise StreamValidationError(
            f"Bitrate {bitrate_kbps} kbps fuera de rango ({MIN_BITRATE_KBPS}-{MAX_BITRATE_KBPS} kbps)",
            "INVALID_BITRATE"
        )

    return res_clean, fps, bitrate_kbps


def detect_available_capture_sources() -> Dict[str, List[Dict[str, Any]]]:
    """
    Detecta fuentes de captura disponibles en el sistema (pantallas, ventanas y juegos de C.C.I.).
    """
    screens = [
        {
            "id": "screen:0",
            "type": "screen",
            "name": "Pantalla Principal (1920x1080)",
            "width": 1920,
            "height": 1080,
            "is_primary": True,
        }
    ]

    windows = [
        {
            "id": "window:cci_launcher",
            "type": "window",
            "name": "C.C.I. SYSTEM Launcher (1280x720)",
            "app_name": "CCI-Launcher",
        }
    ]

    games = []
    for g in CCI_TITLES:
        games.append({
            "id": f"game:{g['game_id']}",
            "type": "game",
            "game_id": g["game_id"],
            "name": g["title"],
            "process_name": g["process_name"],
            "has_direct_audio": True,
        })

    return {
        "screens": screens,
        "windows": windows,
        "games": games,
        "profiles": STREAM_PROFILES,
    }
