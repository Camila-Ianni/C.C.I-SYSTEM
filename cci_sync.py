"""
cci_sync.py - Cliente de sincronización en segundo plano (Daemon Thread) para C.C.I. System.
Garantiza que el bucle de juego a 60 FPS en Pygame nunca sufra bloqueos de red ni esperas I/O.
Soporta sincronización HTTP contra la API REST o persistencia directa en SQLite local si está offline.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

import cci_database

logger = logging.getLogger("CCISync")

DEFAULT_API_URL = "http://127.0.0.1:5050"


def _http_post_json(url: str, payload: dict, timeout: float = 2.0) -> Optional[dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "CCI-System-Desktop/2.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
    except Exception as exc:
        logger.debug("Fallo en petición HTTP hacia %s: %s", url, exc)
    return None


def sync_profile_background(
    profile_data: Dict[str, Any],
    api_url: str = DEFAULT_API_URL,
    on_success: Optional[Callable[[dict], None]] = None
) -> threading.Thread:
    """
    Sincroniza un perfil en un hilo daemon desacoplado.
    Primero intenta HTTP; si no responde o está offline, persiste directamente en SQLite.
    """
    def _worker():
        endpoint = f"{api_url.rstrip('/')}/api/v1/profiles/sync"
        result = _http_post_json(endpoint, profile_data, timeout=1.5)

        if not result or result.get("status") != "success":
            # Persistencia directa en base de datos local SQLite
            try:
                cci_database.init_db()
                db_result = cci_database.sync_profile_data(profile_data)
                result = {"status": "success", "mode": "direct_sqlite", "profile": db_result}
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}

        if on_success and result.get("status") == "success":
            try:
                on_success(result)
            except Exception:
                pass

    t = threading.Thread(target=_worker, name="CCI-ProfileSyncWorker", daemon=True)
    t.start()
    return t


def submit_score_background(
    game_id: str,
    player_name: str,
    score: int,
    level: int = 1,
    profile_id: Optional[str] = None,
    api_url: str = DEFAULT_API_URL,
    on_success: Optional[Callable[[dict], None]] = None
) -> threading.Thread:
    """
    Registra un récord arcade en un hilo daemon.
    Intenta HTTP REST API y luego fallback a SQLite directo.
    """
    def _worker():
        payload = {
            "game_id": game_id,
            "player_name": player_name,
            "score": int(score),
            "level": int(level),
            "profile_id": profile_id,
        }
        endpoint = f"{api_url.rstrip('/')}/api/v1/leaderboards"
        result = _http_post_json(endpoint, payload, timeout=1.5)

        if not result or result.get("status") != "success":
            try:
                cci_database.init_db()
                rec_id = cci_database.record_highscore(
                    game_id=game_id,
                    player_name=player_name,
                    score=score,
                    level=level,
                    profile_id=profile_id
                )
                result = {"status": "success", "mode": "direct_sqlite", "id": rec_id}
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}

        if on_success and result.get("status") == "success":
            try:
                on_success(result)
            except Exception:
                pass

    t = threading.Thread(target=_worker, name="CCI-ScoreSyncWorker", daemon=True)
    t.start()
    return t
