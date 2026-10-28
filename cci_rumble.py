"""
Módulo universal de Vibración / Háptica para C.C.I. SYSTEM
Soporta mandos DualShock 4, DualSense (PS5), Xbox 360/One/Series, Nintendo Switch Pro
y cualquier gamepad compatible con el protocolo rumble de SDL2 / pygame-ce.
"""

import json
import os
from pathlib import Path
import pygame

_joysticks = []
_initialized = False

DATA_DIR = Path.home() / ".cci-user-data"
DATA_FILE = DATA_DIR / "system.json"


def _is_vibration_enabled() -> bool:
    """Verifica si la vibración está activada en la configuración global de la consola."""
    env_val = os.environ.get("CCI_VIBRATION")
    if env_val is not None:
        return env_val.lower() not in ("0", "false", "no", "off")
    try:
        if DATA_FILE.is_file():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            settings = data.get("settings", {})
            return bool(settings.get("vibration", True))
    except Exception:
        pass
    return True


def init_rumble():
    """Inicializa el subsistema de joystick y busca mandos con capacidad de vibración."""
    global _initialized, _joysticks
    try:
        if not pygame.get_init():
            pygame.init()
    except Exception:
        pass

    try:
        if not pygame.joystick.get_init():
            pygame.joystick.init()
    except Exception:
        pass

    _joysticks = []
    try:
        count = pygame.joystick.get_count()
        for i in range(count):
            try:
                j = pygame.joystick.Joystick(i)
                if not j.get_init():
                    j.init()
                _joysticks.append(j)
            except Exception:
                pass
    except Exception:
        pass
    _initialized = True


def rumble(low: float = 0.6, high: float = 0.6, duration_ms: int = 250):
    """
    Emite una vibración en todos los mandos conectados.
    :param low: Intensidad del motor de baja frecuencia / peso (0.0 a 1.0)
    :param high: Intensidad del motor de alta frecuencia / zumbido (0.0 a 1.0)
    :param duration_ms: Duración en milisegundos
    """
    global _initialized, _joysticks
    if not _is_vibration_enabled():
        return

    if not _initialized or not _joysticks:
        init_rumble()

    for joy in list(_joysticks):
        if hasattr(joy, "rumble"):
            try:
                joy.rumble(float(low), float(high), int(duration_ms))
            except Exception:
                pass


def stop_rumble():
    """Detiene la vibración activa en todos los mandos."""
    global _joysticks
    for joy in _joysticks:
        if hasattr(joy, "stop_rumble"):
            try:
                joy.stop_rumble()
            except Exception:
                pass


def hit_rumble():
    """Vibración contundente: el personaje recibe un golpe de un enemigo."""
    rumble(low=0.75, high=0.9, duration_ms=230)


def damage_rumble():
    """Vibración moderada: pérdida de salud o daño continuo."""
    rumble(low=0.5, high=0.65, duration_ms=180)


def explosion_rumble():
    """Vibración potente: explosión, muerte o KO."""
    rumble(low=1.0, high=0.85, duration_ms=420)


def light_rumble():
    """Vibración sutil: impacto leve, salto sobre bloque o caída."""
    rumble(low=0.25, high=0.35, duration_ms=90)
