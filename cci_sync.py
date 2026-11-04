"""
cci_sync.py - Cliente de sincronización en segundo plano (Daemon Thread) para C.C.I. System.
Garantiza que el bucle de juego a 60 FPS en Pygame nunca sufra bloqueos de red ni esperas I/O.
Soporta sincronización remota contra la API REST (Render) con token de autenticación
o persistencia directa en SQLite local si está offline.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import cci_database

logger = logging.getLogger("CCISync")

DEFAULT_API_URL = os.environ.get("CCI_API_URL", "https://c-c-i-system.onrender.com")


def get_stored_auth_token() -> Optional[str]:
    """Recupera el token de autenticación guardado en la consola si el usuario inició sesión."""
    token_file = cci_database.DATA_DIR / "auth_token.json"
    if token_file.exists():
        try:
            data = json.loads(token_file.read_text(encoding="utf-8"))
            return data.get("token")
        except Exception:
            pass
    return os.environ.get("CCI_AUTH_TOKEN")


def save_auth_token(token: str, username: str = "", email: str = "") -> None:
    """Almacena localmente las credenciales del usuario autenticado en la consola."""
    token_file = cci_database.DATA_DIR / "auth_token.json"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(json.dumps({
        "token": token,
        "username": username,
        "email": email
    }, indent=2), encoding="utf-8")


def _http_post_json(
    url: str,
    payload: dict,
    token: Optional[str] = None,
    timeout: float = 2.0
) -> Optional[dict]:
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CCI-System-Desktop/2.1"
    }
    auth_tok = token or get_stored_auth_token()
    if auth_tok:
        headers["Authorization"] = f"Bearer {auth_tok}"

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
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
    api_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    on_success: Optional[Callable[[dict], None]] = None
) -> threading.Thread:
    """
    Sincroniza un perfil en un hilo daemon desacoplado.
    Primero intenta HTTP contra el endpoint remoto de producción;
    si no responde o está offline, persiste directamente en SQLite local.
    """
    target_url = api_url or os.environ.get("CCI_API_URL", DEFAULT_API_URL)

    def _worker():
        endpoint = f"{target_url.rstrip('/')}/api/v1/profiles/sync"
        result = _http_post_json(endpoint, profile_data, token=auth_token, timeout=2.0)

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
    api_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    on_success: Optional[Callable[[dict], None]] = None
) -> threading.Thread:
    """
    Registra un récord arcade en un hilo daemon desacoplado.
    Intenta HTTP REST API y luego fallback a SQLite directo.
    """
    target_url = api_url or os.environ.get("CCI_API_URL", DEFAULT_API_URL)

    def _worker():
        payload = {
            "game_id": game_id,
            "player_name": player_name,
            "score": int(score),
            "level": int(level),
            "profile_id": profile_id,
        }
        endpoint = f"{target_url.rstrip('/')}/api/v1/leaderboards"
        result = _http_post_json(endpoint, payload, token=auth_token, timeout=2.0)

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
