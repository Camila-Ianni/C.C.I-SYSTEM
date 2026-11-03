"""
cci_updater.py - Módulo de actualización automática y gestión de versiones para C.C.I. SYSTEM.
100% Python nativo sin dependencias externas.
Verifica actualizaciones en segundo plano (daemon thread) sin interferir en los 60 FPS de la consola.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("CCIUpdater")

ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "version.json"

DEFAULT_API_URL = "http://127.0.0.1:5050"


def load_local_version() -> Dict[str, Any]:
    if VERSION_FILE.exists():
        try:
            return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "name": "C.C.I. SYSTEM",
        "version": "2.1.0",
        "release_name": "Ecosistema Arcade & Cloud Sync",
        "author": "Camila Carolina Ianni",
        "release_date": "2026-11-03",
    }


CURRENT_VERSION_INFO = load_local_version()
CURRENT_VERSION = CURRENT_VERSION_INFO.get("version", "2.1.0")


def parse_semver(v_str: str) -> Tuple[int, int, int]:
    """Convierte cadenas como '2.1.0' o 'v2.0' en una tupla de enteros (major, minor, patch)."""
    clean = v_str.strip().lstrip("vV")
    parts = clean.split(".")
    nums = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def is_newer_version(latest_str: str, current_str: str = CURRENT_VERSION) -> bool:
    """Retorna True si latest_str es estrictamente mayor que current_str."""
    return parse_semver(latest_str) > parse_semver(current_str)


def check_for_updates_sync(api_url: str = DEFAULT_API_URL, timeout: float = 2.0) -> Dict[str, Any]:
    """
    Comprueba de forma síncrona si existe una nueva versión contra el endpoint /api/v1/version.
    """
    endpoint = f"{api_url.rstrip('/')}/api/v1/version"
    req = urllib.request.Request(
        endpoint,
        headers={"User-Agent": f"CCI-System-Updater/{CURRENT_VERSION}", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                remote_data = json.loads(resp.read().decode("utf-8"))
                remote_ver = remote_data.get("version", CURRENT_VERSION)
                has_update = is_newer_version(remote_ver, CURRENT_VERSION)
                return {
                    "status": "update_available" if has_update else "up_to_date",
                    "current_version": CURRENT_VERSION,
                    "latest_version": remote_ver,
                    "has_update": has_update,
                    "release_name": remote_data.get("release_name", ""),
                    "release_date": remote_data.get("release_date", ""),
                    "downloads": remote_data.get("downloads", {}),
                    "changelog": remote_data.get("changelog", []),
                }
    except Exception as exc:
        logger.debug("No se pudo comprobar actualizaciones: %s", exc)
        return {
            "status": "offline",
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "has_update": False,
            "error": str(exc),
        }


def check_for_updates_background(
    api_url: str = DEFAULT_API_URL,
    on_result: Optional[Callable[[Dict[str, Any]], None]] = None,
    timeout: float = 2.0
) -> threading.Thread:
    """
    Ejecuta la comprobación en un hilo daemon para no congelar el loop de renderizado a 60 FPS.
    """
    def _worker():
        result = check_for_updates_sync(api_url=api_url, timeout=timeout)
        if on_result:
            try:
                on_result(result)
            except Exception:
                pass

    t = threading.Thread(target=_worker, name="CCI-UpdaterWorker", daemon=True)
    t.start()
    return t


def get_system_badge() -> str:
    """Retorna el badge de versión para mostrar en el HUD o pantalla de Ajustes."""
    return f"C.C.I. SYSTEM v{CURRENT_VERSION} // REV 2026"
