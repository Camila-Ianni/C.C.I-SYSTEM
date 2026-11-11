"""
backend/communities/desktop_client.py - Cliente REST, Realtime Socket.IO y Controlador Qt real para CCI Communities.

Reemplaza los datos demo y fallbacks simulados de la interfaz desktop Qt por:
1. Autenticación real JWT Bearer contra `/api/v1/auth/register`, `/api/v1/auth/token` y `/api/v1/auth/me`.
2. Persistencia de sesión local por instancia (`CCI_SESSION_FILE` o `.cci-user-data/desktop_session.json`).
3. Consumo estricto de la API REST de Communities y Socket.IO en tiempo real con rooms autorizadas.
4. Estado honesto ante fallos de red, 401/403 o ausencia de plano multimedia LiveKit RTC.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import logging
import os
from pathlib import Path
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
import weakref

import requests
import socketio
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_API_URL = os.getenv("CCI_API_URL", "http://127.0.0.1:5050").rstrip("/")

_started_local_ports: set[int] = set()
_resolved_local_urls: Dict[str, str] = {}
_local_server_lock = threading.Lock()


class CommunityApiError(RuntimeError):
    """Error explícito de API o red sin enmascarar fallos como éxito."""

    def __init__(self, message: str, status_code: int = 0, code: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


@dataclass
class CommunitySession:
    api_url: str
    token: str
    user_id: str
    username: str


def default_session_path() -> Path:
    custom = os.getenv("CCI_SESSION_FILE", "").strip()
    if custom:
        return Path(custom)
    return ROOT_DIR / ".cci-user-data" / "desktop_session.json"


def _extract_invite_code(raw: str) -> str:
    cleaned = str(raw or "").strip()
    if "/invite/" in cleaned:
        cleaned = cleaned.rsplit("/invite/", 1)[-1].strip()
    elif cleaned.startswith("cci://invite/"):
        cleaned = cleaned[len("cci://invite/"):].strip()
    return cleaned.split("?")[0].strip("/")


def _is_tcp_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pick_free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _is_communities_backend(base_url: str, timeout: float = 1.2) -> Tuple[bool, str]:
    """Verifica que el servidor responda `/api/v1/communities/health` con JSON válido de C.C.I. Communities."""
    base = base_url.rstrip("/")
    try:
        resp = requests.get(f"{base}/api/v1/communities/health", timeout=timeout)
    except requests.RequestException as exc:
        return False, str(exc)

    if resp.status_code != 200:
        return False, f"El servidor en {base} no expone /api/v1/communities/health (HTTP {resp.status_code})"

    try:
        data = resp.json()
    except Exception:
        return False, f"Respuesta inválida en {base}/api/v1/communities/health"

    if not isinstance(data, dict) or "realtime_socketio" not in data:
        return False, f"Servicio inesperado en {base} (no corresponde a C.C.I. Communities)"

    return True, "connected"


def resolve_communities_backend(
    api_url: str = DEFAULT_API_URL,
    timeout: float = 5.0,
) -> Tuple[bool, str, str]:
    """
    Comprueba si un backend real de C.C.I. Communities responde en `api_url`.
    Si apunta a loopback y CCI_AUTO_START_BACKEND != '0':
      - Inicia `backend.server` en hilo daemon local.
      - Si el puerto configurado ya está ocupado por otro proceso que no sirve Communities
        (ej. `run_web.py` en :5050), levanta el backend en un puerto libre de loopback y
        devuelve la URL activa resuelta `(ok, msg, active_url)`.
    """
    base = api_url.rstrip("/")

    with _local_server_lock:
        cached = _resolved_local_urls.get(base)
    if cached:
        ok, msg = _is_communities_backend(cached, timeout=1.0)
        if ok:
            return True, msg, cached

    ok, probe_err = _is_communities_backend(base, timeout=1.2)
    if ok:
        return True, "connected", base

    parsed = urlparse(base)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    is_loopback = host in ("127.0.0.1", "localhost")
    auto_start = os.getenv("CCI_AUTO_START_BACKEND", "1").strip().lower() not in ("0", "false", "no")

    if not (is_loopback and auto_start):
        return False, probe_err or f"No se pudo conectar con {base}", base

    with _local_server_lock:
        cached = _resolved_local_urls.get(base)
        if cached:
            target_base = cached
            target_parsed = urlparse(target_base)
            target_port = int(target_parsed.port or port)
        else:
            port_busy = _is_tcp_port_open(host, port, timeout=0.35)
            target_port = _pick_free_loopback_port() if port_busy else port
            target_base = f"http://127.0.0.1:{target_port}"
            _resolved_local_urls[base] = target_base

        if target_port not in _started_local_ports:
            _started_local_ports.add(target_port)

            def _serve(listen_port: int = target_port):
                try:
                    import cci_database
                    from backend.server import app as srv_app, socketio as srv_sio
                    cci_database.init_db()
                    srv_sio.run(
                        srv_app,
                        host="127.0.0.1",
                        port=listen_port,
                        debug=False,
                        use_reloader=False,
                        allow_unsafe_werkzeug=True,
                        log_output=False,
                    )
                except Exception as exc:
                    logger.warning("Local backend thread exited: %s", exc)

            t = threading.Thread(target=_serve, daemon=True, name=f"CCI-LocalBackend-{target_port}")
            t.start()

    deadline = time.monotonic() + timeout
    last_err = f"Tiempo agotado conectando a {target_base}"
    while time.monotonic() < deadline:
        ok, err_msg = _is_communities_backend(target_base, timeout=0.8)
        if ok:
            return True, "connected", target_base
        last_err = err_msg
        time.sleep(0.12)

    with _local_server_lock:
        if _resolved_local_urls.get(base) == target_base:
            _resolved_local_urls.pop(base, None)
    return False, last_err, base


def ensure_local_backend_running(api_url: str = DEFAULT_API_URL, timeout: float = 5.0) -> Tuple[bool, str]:
    ok, msg, _active = resolve_communities_backend(api_url=api_url, timeout=timeout)
    return ok, msg


class CommunityApiClient:
    """Cliente HTTP síncrono (requests.Session) con Bearer JWT y manejo honesto de errores."""

    def __init__(self, api_url: str = DEFAULT_API_URL, timeout: float = 6.0):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._thread_local = threading.local()
        self.token: Optional[str] = None

    @property
    def _http(self) -> requests.Session:
        sess = getattr(self._thread_local, "session", None)
        if sess is None:
            sess = requests.Session()
            self._thread_local.session = sess
        return sess

    def set_token(self, token: Optional[str]) -> None:
        self.token = token.strip() if token else None

    def _headers(self) -> Dict[str, str]:
        hdrs = {"Accept": "application/json"}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        return hdrs

    def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        try:
            resp = self._http.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=json_body,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise CommunityApiError(f"Error de red conectando al servidor: {exc}", status_code=0, code="NETWORK_ERROR") from exc

        data: Dict[str, Any] = {}
        try:
            parsed = resp.json()
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            data = {}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or f"Error HTTP {resp.status_code}"
            err_code = str(data.get("code") or data.get("error") or f"HTTP_{resp.status_code}")
            raise CommunityApiError(str(err_msg), status_code=resp.status_code, code=err_code)

        return data

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/communities/health")

    def register(self, email: str, username: str, password: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/auth/register",
            json_body={"email": email, "username": username, "password": password},
        )

    def login(self, identifier: str, password: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/auth/token",
            json_body={"identifier": identifier, "password": password},
        )

    def get_me(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/auth/me")

    def list_communities(self, discover_public: bool = False) -> List[Dict[str, Any]]:
        params = {"visibility": "public"} if discover_public else None
        data = self._request("GET", "/api/v1/communities", params=params)
        return list(data.get("communities") or [])

    def create_community(self, name: str, description: str = "", visibility: str = "private") -> Dict[str, Any]:
        data = self._request(
            "POST",
            "/api/v1/communities",
            json_body={"name": name, "description": description, "visibility": visibility},
        )
        return dict(data.get("community") or {})

    def get_community(self, community_id: str) -> Dict[str, Any]:
        data = self._request("GET", f"/api/v1/communities/{community_id}")
        return dict(data.get("community") or {})

    def join_public_community(self, community_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/communities/{community_id}/join", json_body={})

    def create_invitation(
        self,
        community_id: str,
        max_uses: int = 0,
        expires_in_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"max_uses": max_uses}
        if expires_in_hours is not None:
            payload["expires_in_hours"] = expires_in_hours
        data = self._request("POST", f"/api/v1/communities/{community_id}/invitations", json_body=payload)
        return dict(data.get("invitation") or {})

    def list_invitations(self, community_id: str) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/api/v1/communities/{community_id}/invitations")
        return list(data.get("invitations") or [])

    def revoke_invitation(self, community_id: str, code: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/v1/communities/{community_id}/invitations/{code}")

    def moderate_member(
        self,
        community_id: str,
        target_id: str,
        action: str,
        duration_seconds: Optional[int] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        act = action.lower()
        if act not in ("kick", "mute", "unmute", "ban"):
            raise CommunityApiError(f"Acción de moderación inválida: {action}", status_code=400)
        body: Dict[str, Any] = {"target_user_id": target_id, "reason": reason}
        if act == "mute" and duration_seconds is not None:
            body["duration_minutes"] = max(1, int(round(float(duration_seconds) / 60.0)))
        return self._request(
            "POST",
            f"/api/v1/communities/{community_id}/moderation/{act}",
            json_body=body,
        )

    def join_via_invitation(self, raw_code_or_link: str) -> Dict[str, Any]:
        code = _extract_invite_code(raw_code_or_link)
        if not code:
            raise CommunityApiError("Ingresá un código o enlace de invitación válido.", status_code=400, code="INVALID_CODE")
        return self._request("POST", "/api/v1/invitations/join", json_body={"code": code})

    def leave_community(self, community_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/communities/{community_id}/leave", json_body={})

    def list_members(self, community_id: str) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/api/v1/communities/{community_id}/members")
        return list(data.get("members") or [])

    def list_channels(self, community_id: str) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/api/v1/communities/{community_id}/channels")
        return list(data.get("channels") or [])

    def create_channel(
        self,
        community_id: str,
        name: str,
        channel_type: str = "text",
        topic: str = "",
        is_private: bool = False,
    ) -> Dict[str, Any]:
        data = self._request(
            "POST",
            f"/api/v1/communities/{community_id}/channels",
            json_body={
                "name": name,
                "type": channel_type,
                "topic": topic,
                "is_private": is_private,
            },
        )
        return dict(data.get("channel") or {})

    def update_channel(
        self,
        community_id: str,
        channel_id: str,
        name: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if topic is not None:
            body["topic"] = topic
        data = self._request("PATCH", f"/api/v1/communities/{community_id}/channels/{channel_id}", json_body=body)
        return dict(data.get("channel") or {})

    def delete_channel(self, community_id: str, channel_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/v1/communities/{community_id}/channels/{channel_id}")

    def list_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if before_id:
            params["before_id"] = before_id
        if after_id:
            params["after_id"] = after_id
        data = self._request("GET", f"/api/v1/channels/{channel_id}/messages", params=params)
        return list(data.get("messages") or [])

    def send_message(
        self,
        channel_id: str,
        content: str,
        reply_to_id: Optional[str] = None,
        attachment_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"content": content}
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        if attachment_ids:
            payload["attachment_ids"] = list(attachment_ids)
        data = self._request("POST", f"/api/v1/channels/{channel_id}/messages", json_body=payload)
        return dict(data.get("message") or {})

    def toggle_reaction(self, channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/channels/{channel_id}/messages/{message_id}/reactions",
            json_body={"emoji": emoji},
        )

    def upload_attachment(self, channel_id: str, file_path: str | Path) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise CommunityApiError("Archivo adjunto no encontrado en disco.", status_code=400)
        url = f"{self.api_url}/api/v1/channels/{channel_id}/attachments"
        hdrs = {}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        try:
            with p.open("rb") as fh:
                resp = self._http.post(url, headers=hdrs, files={"file": (p.name, fh)}, timeout=max(self.timeout, 12.0))
        except requests.RequestException as exc:
            raise CommunityApiError(f"Error subiendo adjunto: {exc}", status_code=0, code="NETWORK_ERROR") from exc
        data: Dict[str, Any] = {}
        try:
            parsed = resp.json()
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            data = {}
        if resp.status_code >= 400:
            raise CommunityApiError(
                str(data.get("error") or data.get("message") or f"Error HTTP {resp.status_code}"),
                status_code=resp.status_code,
            )
        return dict(data.get("attachment") or {})

    def _download_bytes(self, path: str, label: str = "recurso") -> bytes:
        url = f"{self.api_url}{path}"
        hdrs = {}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        try:
            resp = self._http.get(url, headers=hdrs, timeout=self.timeout)
        except requests.RequestException as exc:
            raise CommunityApiError(f"Error descargando {label}: {exc}", status_code=0) from exc
        if resp.status_code >= 400:
            raise CommunityApiError(
                f"{label.capitalize()} no disponible (HTTP {resp.status_code})",
                status_code=resp.status_code,
            )
        return bytes(resp.content)

    def download_attachment_bytes(self, attachment_id: str) -> bytes:
        return self._download_bytes(f"/api/v1/attachments/{attachment_id}", label="adjunto")

    def edit_message(self, channel_id: str, message_id: str, content: str) -> Dict[str, Any]:
        data = self._request(
            "PATCH",
            f"/api/v1/channels/{channel_id}/messages/{message_id}",
            json_body={"content": content},
        )
        return dict(data.get("message") or {})

    def delete_message(self, channel_id: str, message_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/v1/channels/{channel_id}/messages/{message_id}")

    def get_presences(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        cleaned = [u for u in user_ids if u]
        if not cleaned:
            return {}
        data = self._request("GET", "/api/v1/users/presence", params={"user_ids": ",".join(cleaned)})
        return dict(data.get("presences") or {})

    def set_presence(
        self,
        status: str = "online",
        custom_status: Optional[str] = None,
        activity_visibility: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"status": status, "custom_status": custom_status}
        if activity_visibility is not None:
            body["activity_visibility"] = activity_visibility
        data = self._request("POST", "/api/v1/users/presence", json_body=body)
        return dict(data.get("presence") or {})

    def heartbeat_presence(self) -> Dict[str, Any]:
        data = self._request("POST", "/api/v1/users/presence/heartbeat", json_body={})
        return dict(data.get("presence") or {})

    def report_game_activity(
        self,
        action: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        visibility: str = "communities",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/users/activity/game",
            json_body={
                "action": action,
                "game_id": game_id,
                "title": title,
                "visibility": visibility,
            },
        )

    def get_activity_feed(self, limit: int = 40) -> List[Dict[str, Any]]:
        data = self._request("GET", "/api/v1/users/activity/feed", params={"limit": limit})
        return list(data.get("events") or [])

    def list_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        data = self._request(
            "GET",
            "/api/v1/users/notifications",
            params={"unread_only": "true" if unread_only else "false"},
        )
        return list(data.get("notifications") or [])

    def mark_notifications_read(self, notification_ids: Optional[List[str]] = None) -> int:
        data = self._request(
            "POST",
            "/api/v1/users/notifications/read",
            json_body={"notification_ids": notification_ids} if notification_ids else {},
        )
        return int(data.get("marked_read") or 0)

    def get_friends(self, user_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/friends/{user_id}")

    def send_friend_request(self, target_username: str) -> Dict[str, Any]:
        return self._request("POST", "/api/v1/friends/request", json_body={"target_username": target_username})

    def respond_friend_request(self, requester_id: str, action: str = "accept") -> Dict[str, Any]:
        return self._request("POST", "/api/v1/friends/respond", json_body={"requester_id": requester_id, "action": action})

    def request_voice_token(self, channel_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/channels/{channel_id}/voice-token", json_body={})

    def leave_voice(self, channel_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/channels/{channel_id}/voice-leave", json_body={})

    def list_voice_participants(self, channel_id: str) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/api/v1/channels/{channel_id}/voice-participants")
        return list(data.get("participants") or [])

    def list_active_streams(self, community_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"community_id": community_id} if community_id else None
        data = self._request("GET", "/api/v1/streams", params=params)
        return list(data.get("streams") or [])

    def get_stream_sources(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/streams/sources")

    def start_stream(
        self,
        channel_id: str,
        stream_type: str = "screen",
        title: Optional[str] = None,
        game_id: Optional[str] = None,
        resolution: str = "720p",
        fps: int = 30,
        bitrate_kbps: int = 2500,
        has_audio: bool = False,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "stream_type": stream_type,
            "resolution": resolution,
            "fps": int(fps),
            "bitrate_kbps": int(bitrate_kbps),
            "has_audio": bool(has_audio),
        }
        if title:
            body["title"] = title
        if game_id:
            body["game_id"] = game_id
        return self._request("POST", f"/api/v1/channels/{channel_id}/stream-start", json_body=body)

    def pause_stream(
        self,
        channel_id: str,
        session_id: Optional[str] = None,
        is_paused: bool = True,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"is_paused": bool(is_paused)}
        if session_id:
            body["session_id"] = session_id
        return self._request("POST", f"/api/v1/channels/{channel_id}/stream-pause", json_body=body)

    def stop_stream(self, channel_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if session_id:
            body["session_id"] = session_id
        return self._request("POST", f"/api/v1/channels/{channel_id}/stream-stop", json_body=body)

    def get_channel_stream(self, channel_id: str) -> Optional[Dict[str, Any]]:
        data = self._request("GET", f"/api/v1/channels/{channel_id}/stream")
        return data.get("stream")

    def list_sound_presets(self) -> List[Dict[str, Any]]:
        data = self._request("GET", "/api/v1/sounds/presets")
        return list(data.get("presets") or [])

    def list_community_sounds(self, community_id: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"search": search} if search else None
        data = self._request("GET", f"/api/v1/communities/{community_id}/sounds", params=params)
        return list(data.get("sounds") or [])

    def upload_sound(
        self,
        title: str,
        file_bytes: bytes,
        owner_type: str = "community",
        owner_id: Optional[str] = None,
        category_id: Optional[str] = None,
        volume_scale: float = 1.0,
        cooldown_seconds: int = 5,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "owner_type": owner_type,
            "title": title,
            "file_base64": base64.b64encode(file_bytes).decode("ascii"),
            "volume_scale": float(volume_scale),
            "cooldown_seconds": int(cooldown_seconds),
        }
        if owner_id:
            body["owner_id"] = owner_id
        if category_id:
            body["category_id"] = category_id
        return self._request("POST", "/api/v1/sounds", json_body=body)

    def authorize_sound_play(self, sound_id: str, channel_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/sounds/{sound_id}/play-authorize",
            json_body={"channel_id": channel_id},
        )

    def authorize_sound_preset(self, channel_id: str, preset_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/channels/{channel_id}/soundboard/authorize-preset",
            json_body={"preset_id": preset_id},
        )

    def download_sound_audio(self, sound_id: str) -> bytes:
        return self._download_bytes(f"/api/v1/sounds/{sound_id}/audio", label="audio de soundboard")

    def delete_sound(self, sound_id: str) -> bool:
        data = self._request("DELETE", f"/api/v1/sounds/{sound_id}")
        return bool(data.get("deleted"))


class CommunityRealtimeBridge(QObject):
    """Cliente Socket.IO en hilo separado que despacha eventos vía señales Qt."""

    connected = Signal()
    disconnected = Signal(str)
    community_error = Signal(str)
    message_created = Signal(dict)
    message_updated = Signal(dict)
    message_deleted = Signal(dict)
    reaction_updated = Signal(dict)
    channel_created = Signal(dict)
    channel_updated = Signal(dict)
    channel_deleted = Signal(dict)
    member_joined = Signal(dict)
    member_left = Signal(dict)
    presence_updated = Signal(dict)
    typing_updated = Signal(dict)
    activity_updated = Signal(dict)
    notification_received = Signal(dict)
    stream_started = Signal(dict)
    stream_paused = Signal(dict)
    stream_ended = Signal(dict)
    sound_played = Signal(dict)
    sound_stopped = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._sio: Optional[socketio.Client] = None
        self._api_url: str = ""
        self._token: str = ""
        self._active_community_id: Optional[str] = None
        self._active_channel_id: Optional[str] = None
        self._stop_flag = False

    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._sio and self._sio.connected)

    def connect_with_token(self, api_url: str, token: str) -> None:
        self.disconnect_sync()
        self._stop_flag = False
        self._api_url = api_url.rstrip("/")
        self._token = token

        sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=1,
            reconnection_delay_max=8,
            logger=False,
            engineio_logger=False,
        )

        @sio.event
        def connect():
            self._rejoin_active_rooms()
            self.connected.emit()

        @sio.event
        def disconnect():
            if not self._stop_flag:
                self.disconnected.emit("Socket.IO desconectado")

        @sio.on("community:error")
        def on_comm_error(data):
            msg = data.get("error", "Error de tiempo real") if isinstance(data, dict) else str(data)
            self.community_error.emit(str(msg))

        @sio.on("message:created")
        def on_msg_created(data):
            if isinstance(data, dict):
                self.message_created.emit(data)

        @sio.on("message:updated")
        def on_msg_updated(data):
            if isinstance(data, dict):
                self.message_updated.emit(data)

        @sio.on("message:deleted")
        def on_msg_deleted(data):
            if isinstance(data, dict):
                self.message_deleted.emit(data)

        @sio.on("channel:created")
        def on_chan_created(data):
            if isinstance(data, dict):
                self.channel_created.emit(data)

        @sio.on("community:member_joined")
        def on_mem_joined(data):
            if isinstance(data, dict):
                self.member_joined.emit(data)

        @sio.on("community:member_left")
        def on_mem_left(data):
            if isinstance(data, dict):
                self.member_left.emit(data)

        @sio.on("presence:updated")
        def on_pres_upd(data):
            if isinstance(data, dict):
                self.presence_updated.emit(data)

        @sio.on("message:reaction_updated")
        def on_react_upd(data):
            if isinstance(data, dict):
                self.reaction_updated.emit(data)

        @sio.on("channel:updated")
        def on_chan_upd(data):
            if isinstance(data, dict):
                self.channel_updated.emit(data)

        @sio.on("channel:deleted")
        def on_chan_del(data):
            if isinstance(data, dict):
                self.channel_deleted.emit(data)

        @sio.on("typing:updated")
        def on_typing_upd(data):
            if isinstance(data, dict):
                self.typing_updated.emit(data)

        @sio.on("activity:game_started")
        def on_act_start(data):
            if isinstance(data, dict):
                self.activity_updated.emit({"event": "started", **data})

        @sio.on("activity:game_stopped")
        def on_act_stop(data):
            if isinstance(data, dict):
                self.activity_updated.emit({"event": "stopped", **data})

        @sio.on("notification:created")
        def on_notif_created(data):
            if isinstance(data, dict):
                self.notification_received.emit(data)

        @sio.on("stream.started")
        def on_stream_started(data):
            if isinstance(data, dict):
                self.stream_started.emit(data)

        @sio.on("stream.paused")
        def on_stream_paused(data):
            if isinstance(data, dict):
                self.stream_paused.emit({"is_paused": True, **data})

        @sio.on("stream.resumed")
        def on_stream_resumed(data):
            if isinstance(data, dict):
                self.stream_paused.emit({"is_paused": False, **data})

        @sio.on("stream.ended")
        def on_stream_ended(data):
            if isinstance(data, dict):
                self.stream_ended.emit(data)

        @sio.on("sound.played")
        def on_sound_played(data):
            if isinstance(data, dict):
                self.sound_played.emit(data)

        @sio.on("sound.stopped")
        def on_sound_stopped(data):
            if isinstance(data, dict):
                self.sound_stopped.emit(data)

        with self._lock:
            self._sio = sio

        def _connect_worker():
            try:
                sio.connect(
                    self._api_url,
                    auth={"token": self._token},
                    wait_timeout=5,
                )
            except Exception as exc:
                if not self._stop_flag:
                    self.disconnected.emit(str(exc))

        threading.Thread(target=_connect_worker, daemon=True, name="CCI-RealtimeConnect").start()

    def _rejoin_active_rooms(self) -> None:
        with self._lock:
            sio = self._sio
            comm_id = self._active_community_id
            ch_id = self._active_channel_id
        if not sio or not sio.connected:
            return
        try:
            if comm_id:
                sio.emit("community:join", {"community_id": comm_id})
            if ch_id:
                sio.emit("community:channel:join", {"channel_id": ch_id})
        except Exception:
            pass

    def join_community_room(self, community_id: str) -> None:
        with self._lock:
            prev = self._active_community_id
            self._active_community_id = community_id
            sio = self._sio
        if sio and sio.connected:
            try:
                if prev and prev != community_id:
                    sio.emit("community:leave", {"community_id": prev})
                if community_id:
                    sio.emit("community:join", {"community_id": community_id})
            except Exception:
                pass

    def join_channel_room(self, channel_id: str) -> None:
        with self._lock:
            prev = self._active_channel_id
            self._active_channel_id = channel_id
            sio = self._sio
        if sio and sio.connected:
            try:
                if prev and prev != channel_id:
                    sio.emit("community:channel:leave", {"channel_id": prev})
                if channel_id:
                    sio.emit("community:channel:join", {"channel_id": channel_id})
            except Exception:
                pass

    def _emit_socket(self, event_name: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            sio = self._sio
        if sio and sio.connected:
            try:
                sio.emit(event_name, payload)
            except Exception:
                pass

    def emit_typing(self, channel_id: str, typing: bool = True) -> None:
        if channel_id:
            self._emit_socket("community:typing", {"channel_id": channel_id, "typing": bool(typing)})

    def emit_voice_presence(self, channel_id: str, joined: bool = True) -> None:
        if channel_id:
            ev = "community:voice:join" if joined else "community:voice:leave"
            self._emit_socket(ev, {"channel_id": channel_id})

    def emit_voice_mute(self, channel_id: str, is_muted: bool) -> None:
        if channel_id:
            self._emit_socket("community:voice:mute", {"channel_id": channel_id, "is_muted": bool(is_muted)})

    def emit_stream_start(
        self,
        channel_id: str,
        stream_type: str = "screen",
        title: str = "Stream",
        resolution: str = "720p",
        fps: int = 30,
    ) -> None:
        if channel_id:
            self._emit_socket("community:stream:start", {
                "channel_id": channel_id,
                "stream_type": stream_type,
                "title": title,
                "resolution": resolution,
                "fps": int(fps),
            })

    def emit_stream_pause(self, channel_id: str, is_paused: bool = True) -> None:
        if channel_id:
            self._emit_socket("community:stream:pause", {"channel_id": channel_id, "is_paused": bool(is_paused)})

    def emit_stream_stop(self, channel_id: str) -> None:
        if channel_id:
            self._emit_socket("community:stream:stop", {"channel_id": channel_id})

    def emit_sound_play(
        self,
        channel_id: str,
        sound_id: str,
        title: str = "",
        volume_scale: float = 1.0,
    ) -> None:
        if channel_id and sound_id:
            self._emit_socket("community:sound:play", {
                "channel_id": channel_id,
                "sound_id": sound_id,
                "title": title,
                "volume_scale": float(volume_scale),
            })

    def emit_sound_stop(self, channel_id: str, sound_id: str) -> None:
        if channel_id and sound_id:
            self._emit_socket("community:sound:stop", {
                "channel_id": channel_id,
                "sound_id": sound_id,
            })

    def disconnect_sync(self) -> None:
        self._stop_flag = True
        with self._lock:
            sio = self._sio
            self._sio = None
            self._active_community_id = None
            self._active_channel_id = None
        if sio:
            try:
                sio.disconnect()
            except Exception:
                pass


class _RestWorker(QRunnable):
    """Worker thread para llamadas REST fuera del hilo GUI sin crear QObjects transitorios."""

    def __init__(
        self,
        ctrl_ref: "weakref.ref[CommunityController]",
        task_id: int,
        fn: Callable[[], Any],
        cancelled: threading.Event,
    ):
        super().__init__()
        self.setAutoDelete(False)
        self.ctrl_ref = ctrl_ref
        self.task_id = task_id
        self.fn = fn
        self.cancelled = cancelled

    def run(self) -> None:
        if self.cancelled.is_set():
            return
        try:
            res = self.fn()
            if self.cancelled.is_set():
                return
            ctrl = self.ctrl_ref()
            if ctrl is not None:
                ctrl._worker_ok.emit(self.task_id, res)
        except CommunityApiError as exc:
            if not self.cancelled.is_set():
                ctrl = self.ctrl_ref()
                if ctrl is not None:
                    ctrl._worker_err.emit(self.task_id, exc.message, exc.status_code, exc.code)
        except Exception as exc:
            if not self.cancelled.is_set():
                ctrl = self.ctrl_ref()
                if ctrl is not None:
                    ctrl._worker_err.emit(self.task_id, str(exc), 0, "WORKER_ERROR")


class CommunityController(QObject):
    """Controlador único de UI Qt <-> Backend REST + Socket.IO para Communities."""

    _worker_ok = Signal(int, object)
    _worker_err = Signal(int, str, int, str)  # task_id, message, status_code, code

    session_changed = Signal(object)       # CommunitySession | None
    backend_status_changed = Signal(bool, str)
    loading_changed = Signal(bool, str)    # is_loading, operation_name
    communities_updated = Signal(list, list)  # my_communities, public_communities
    community_opened = Signal(dict)        # community payload + channels + members
    channel_messages_loaded = Signal(str, list)  # channel_id, messages
    messages_synced = Signal(str, list)          # channel_id, missed_messages
    message_received = Signal(dict)
    message_updated = Signal(dict)
    message_deleted = Signal(dict)
    reaction_updated = Signal(dict)
    typing_updated = Signal(dict)
    members_updated = Signal(list)
    friends_updated = Signal(list, list)         # friends, incoming_requests
    activity_feed_updated = Signal(list)
    notifications_updated = Signal(list, int)    # notifications, unread_count
    presence_self_changed = Signal(str, str)     # status, activity_visibility
    game_activity_changed = Signal(dict)         # {"action": "started"|"stopped", "game_id": ..., "title": ...}
    _watcher_started_sig = Signal(dict)
    _watcher_stopped_sig = Signal(dict)
    voice_state_changed = Signal(dict)
    voice_participants_updated = Signal(list)
    stream_state_changed = Signal(dict)
    remote_video_frame_received = Signal(str, int, int, bytes)
    remote_stream_ended = Signal(str)
    active_streams_updated = Signal(list)
    soundboard_loaded = Signal(list)
    soundboard_event = Signal(dict)
    realtime_status_changed = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        session_path: Optional[Path] = None,
        parent=None,
        heartbeat_interval_ms: int = 18000,
        enable_voice_audio_io: Optional[bool] = None,
        enable_game_watcher: bool = True,
        game_watch_interval_sec: float = 1.0,
    ):
        super().__init__(parent)
        self.api_url = api_url.rstrip("/")
        self.session_path = session_path or default_session_path()
        self.api = CommunityApiClient(self.api_url)
        self.realtime = CommunityRealtimeBridge(self)
        self.session: Optional[CommunitySession] = None

        from backend.communities.voice_engine import DesktopVoiceEngine
        self.voice_engine = DesktopVoiceEngine(enable_audio_io=enable_voice_audio_io)
        self._active_voice_cred: Optional[Dict[str, Any]] = None
        self._active_voice_reachable: bool = False
        ctrl_ref = weakref.ref(self)

        def _on_voice_participants(parts: List[Dict[str, Any]]) -> None:
            ctrl = ctrl_ref()
            if ctrl is not None:
                ctrl._on_voice_engine_participants_changed(parts)

        def _on_voice_state(diag: Dict[str, Any]) -> None:
            ctrl = ctrl_ref()
            if ctrl is not None:
                ctrl._on_voice_engine_state_changed(diag)

        def _on_remote_video(pid: str, width: int, height: int, rgba: bytes) -> None:
            ctrl = ctrl_ref()
            if ctrl is not None:
                ctrl.remote_video_frame_received.emit(str(pid), int(width), int(height), rgba)

        def _on_remote_stream_end(pid: str) -> None:
            ctrl = ctrl_ref()
            if ctrl is not None:
                ctrl.remote_stream_ended.emit(str(pid))

        self.voice_engine.on_participants_changed = _on_voice_participants
        self.voice_engine.on_state_changed = _on_voice_state
        self.voice_engine.on_remote_video_frame = _on_remote_video
        self.voice_engine.on_remote_stream_ended = _on_remote_stream_end

        self.my_communities: List[Dict[str, Any]] = []
        self.public_communities: List[Dict[str, Any]] = []
        self.active_community: Optional[Dict[str, Any]] = None
        self.active_channels: List[Dict[str, Any]] = []
        self.active_channel: Optional[Dict[str, Any]] = None
        self.active_members: List[Dict[str, Any]] = []
        self.active_voice_channel: Optional[Dict[str, Any]] = None
        self.active_stream_session: Optional[Dict[str, Any]] = None
        self._stream_watching_channel_id: Optional[str] = None
        self.active_streams: List[Dict[str, Any]] = []
        self.active_soundboard_sounds: List[Dict[str, Any]] = []
        self._sound_audio_cache: Dict[str, bytes] = {}
        self.active_friends: List[Dict[str, Any]] = []
        self.incoming_friend_requests: List[Dict[str, Any]] = []
        self.active_activity_feed: List[Dict[str, Any]] = []
        self.active_notifications: List[Dict[str, Any]] = []
        self.unread_notifications_count: int = 0
        self.current_presence_status: str = "online"
        self.activity_visibility: str = "communities"
        self._last_synced_msg_id: Optional[str] = None
        self._active_game_id: Optional[str] = None
        self._active_game_title: Optional[str] = None
        self._active_game_pid: Optional[int] = None
        self._enable_game_watcher: bool = bool(enable_game_watcher)
        self._catalog_synced_to_watcher: bool = False
        self.last_health: Dict[str, Any] = {}

        from backend.communities.game_watcher import GameProcessWatcher

        def _on_watch_started(payload: Dict[str, Any]) -> None:
            ctrl = ctrl_ref()
            if ctrl is not None:
                ctrl._watcher_started_sig.emit(dict(payload))

        def _on_watch_stopped(payload: Dict[str, Any]) -> None:
            ctrl = ctrl_ref()
            if ctrl is not None:
                ctrl._watcher_stopped_sig.emit(dict(payload))

        self.game_watcher = GameProcessWatcher(
            on_game_started=_on_watch_started,
            on_game_stopped=_on_watch_stopped,
            poll_interval_sec=game_watch_interval_sec,
        )
        self._watcher_started_sig.connect(self._on_watcher_game_started, Qt.QueuedConnection)
        self._watcher_stopped_sig.connect(self._on_watcher_game_stopped, Qt.QueuedConnection)

        self._heartbeat_interval_ms = max(0, int(heartbeat_interval_ms))
        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(self._heartbeat_interval_ms or 18000)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(4)
        self._next_task_id: int = 0
        self._pending_workers: Dict[int, Tuple[Any, Optional[str], int, threading.Event, Any, Any]] = {}
        self._op_generations: Dict[str, int] = {}
        self._worker_ok.connect(self._on_worker_succeeded)
        self._worker_err.connect(self._on_worker_failed)

        self.realtime.connected.connect(self._on_rt_connected)
        self.realtime.disconnected.connect(self._on_rt_disconnected)
        self.realtime.community_error.connect(self.error_occurred.emit)
        self.realtime.message_created.connect(self._on_rt_message_created)
        self.realtime.message_updated.connect(self._on_rt_message_updated)
        self.realtime.message_deleted.connect(self._on_rt_message_deleted)
        self.realtime.reaction_updated.connect(self._on_rt_reaction_updated)
        self.realtime.channel_created.connect(self._on_rt_channel_created)
        self.realtime.channel_updated.connect(self._on_rt_channel_updated)
        self.realtime.channel_deleted.connect(self._on_rt_channel_deleted)
        self.realtime.member_joined.connect(self._on_rt_member_change)
        self.realtime.member_left.connect(self._on_rt_member_change)
        self.realtime.presence_updated.connect(self._on_rt_presence_updated)
        self.realtime.typing_updated.connect(self._on_rt_typing_updated)
        self.realtime.activity_updated.connect(self._on_rt_activity_updated)
        self.realtime.notification_received.connect(self._on_rt_notification_received)
        self.realtime.stream_started.connect(self._on_rt_stream_started)
        self.realtime.stream_paused.connect(self._on_rt_stream_paused)
        self.realtime.stream_ended.connect(self._on_rt_stream_ended)
        self.realtime.sound_played.connect(self._on_rt_sound_played)
        self.realtime.sound_stopped.connect(self._on_rt_sound_stopped)

    # ------------------------------------------------------------------
    # Infraestructura Asíncrona para evitar bloqueo del hilo Qt GUI (P0-02)
    # ------------------------------------------------------------------
    def cancel_pending(self, category: Optional[str] = None) -> None:
        """Cancela operaciones REST en vuelo (todas o de una categoría específica)."""
        if category is None:
            for key in list(self._op_generations.keys()):
                self._op_generations[key] = self._op_generations.get(key, 0) + 1
            for tid, entry in list(self._pending_workers.items()):
                entry[3].set()
            self._pending_workers.clear()
        else:
            self._op_generations[category] = self._op_generations.get(category, 0) + 1
            for tid, entry in list(self._pending_workers.items()):
                if entry[1] == category:
                    entry[3].set()
                    self._pending_workers.pop(tid, None)
        self.loading_changed.emit(bool(self._pending_workers), "")

    def _on_worker_succeeded(self, tid: int, result: Any) -> None:
        entry = self._pending_workers.pop(tid, None)
        self.loading_changed.emit(bool(self._pending_workers), "")
        if entry is None:
            return
        _w, cat, wgen, ev, on_success, _on_error = entry
        if ev.is_set():
            return
        if cat and wgen != self._op_generations.get(cat, 0):
            return
        if on_success:
            on_success(result)

    def _on_worker_failed(self, tid: int, message: str, status_code: int, code: str) -> None:
        entry = self._pending_workers.pop(tid, None)
        self.loading_changed.emit(bool(self._pending_workers), "")
        if entry is None:
            return
        _w, cat, wgen, ev, _on_success, on_error = entry
        if ev.is_set():
            return
        if cat and wgen != self._op_generations.get(cat, 0):
            return
        err = CommunityApiError(message, status_code=status_code, code=code)
        if on_error:
            on_error(err)
        else:
            self.error_occurred.emit(err.message)

    def run_async(
        self,
        op_name: str,
        fn: Callable[[], Any],
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
        category: Optional[str] = None,
    ) -> int:
        """Ejecuta una llamada REST bloqueante en QThreadPool y despacha resultados al hilo Qt."""
        self._next_task_id += 1
        task_id = self._next_task_id
        gen = 0
        if category:
            gen = self._op_generations.get(category, 0) + 1
            self._op_generations[category] = gen
            for tid, entry in list(self._pending_workers.items()):
                if entry[1] == category:
                    entry[3].set()
                    self._pending_workers.pop(tid, None)

        cancel_ev = threading.Event()
        worker = _RestWorker(ctrl_ref=weakref.ref(self), task_id=task_id, fn=fn, cancelled=cancel_ev)
        self._pending_workers[task_id] = (worker, category, gen, cancel_ev, on_success, on_error)
        self.loading_changed.emit(True, op_name)
        self._thread_pool.start(worker)
        return task_id

    # ------------------------------------------------------------------
    # Sesión & Salud
    # ------------------------------------------------------------------
    def _apply_backend_result(self, ok: bool, msg: str, active_url: str, health: Dict[str, Any]) -> None:
        if ok and active_url and active_url != self.api_url:
            logger.info("Communities backend redirigido de %s a %s", self.api_url, active_url)
            self.api_url = active_url
            self.api.api_url = active_url
            if self.session is not None:
                self.session.api_url = active_url
        self.last_health = health if ok else {}
        self.backend_status_changed.emit(ok, msg)

    def check_backend(self, auto_start: bool = True) -> Tuple[bool, str]:
        if auto_start:
            ok, msg, active_url = resolve_communities_backend(self.api_url)
        else:
            ok, msg = _is_communities_backend(self.api_url, timeout=self.api.timeout)
            active_url = self.api_url

        health: Dict[str, Any] = {}
        if ok:
            try:
                old_url = self.api.api_url
                self.api.api_url = active_url.rstrip("/")
                health = self.api.health()
                self.api.api_url = old_url
            except Exception:
                health = {}
        self._apply_backend_result(ok, msg, active_url, health)
        return ok, msg

    def check_backend_async(self, auto_start: bool = True, on_done: Optional[Callable[[bool, str], None]] = None) -> int:
        base_url = self.api_url

        def _work() -> Tuple[bool, str, str, Dict[str, Any]]:
            if auto_start:
                ok, msg, active_url = resolve_communities_backend(base_url)
            else:
                ok, msg = _is_communities_backend(base_url, timeout=self.api.timeout)
                active_url = base_url
            health: Dict[str, Any] = {}
            if ok:
                try:
                    resp = requests.get(f"{active_url.rstrip('/')}/api/v1/communities/health", timeout=self.api.timeout)
                    if resp.status_code == 200:
                        parsed = resp.json()
                        if isinstance(parsed, dict):
                            health = parsed
                except Exception:
                    health = {}
            return ok, msg, active_url, health

        def _done(res: Tuple[bool, str, str, Dict[str, Any]]) -> None:
            ok, msg, active_url, health = res
            self._apply_backend_result(ok, msg, active_url, health)
            if on_done:
                on_done(ok, msg)

        return self.run_async("check_backend", _work, on_success=_done, category="check_backend")

    def restore_session(self) -> Optional[CommunitySession]:
        ok, msg = self.check_backend()
        if not ok:
            self.session = None
            self.session_changed.emit(None)
            return None

        if not self.session_path.exists():
            self.session = None
            self.session_changed.emit(None)
            return None

        try:
            raw = json.loads(self.session_path.read_text(encoding="utf-8"))
            token = str(raw.get("token") or "").strip()
            if not token:
                raise ValueError("Empty token")
            self.api.set_token(token)
            me = self.api.get_me()
            user = me.get("user") or {}
            sess = CommunitySession(
                api_url=self.api_url,
                token=token,
                user_id=str(user["user_id"]),
                username=str(user["username"]),
            )
            self._activate_session(sess, persist=False)
            return sess
        except Exception:
            self.clear_saved_session()
            self.api.set_token(None)
            self.session = None
            self.session_changed.emit(None)
            return None

    def register(self, email: str, username: str, password: str) -> CommunitySession:
        ok, msg = self.check_backend()
        if not ok:
            raise CommunityApiError(f"Servidor no disponible: {msg}", status_code=0, code="OFFLINE")
        res = self.api.register(email=email, username=username, password=password)
        token = str(res.get("token") or "")
        if not token:
            res = self.api.login(identifier=email, password=password)
            token = str(res["token"])
        sess = CommunitySession(
            api_url=self.api_url,
            token=token,
            user_id=str(res["user_id"]),
            username=str(res["username"]),
        )
        self._activate_session(sess, persist=True)
        return sess

    def login(self, identifier: str, password: str) -> CommunitySession:
        ok, msg = self.check_backend()
        if not ok:
            raise CommunityApiError(f"Servidor no disponible: {msg}", status_code=0, code="OFFLINE")
        res = self.api.login(identifier=identifier, password=password)
        sess = CommunitySession(
            api_url=self.api_url,
            token=str(res["token"]),
            user_id=str(res["user_id"]),
            username=str(res["username"]),
        )
        self._activate_session(sess, persist=True)
        return sess

    def restore_session_async(self, on_done: Optional[Callable[[Optional[CommunitySession]], None]] = None) -> int:
        base_url = self.api_url
        sess_path = self.session_path

        def _work():
            ok, msg, active_url = resolve_communities_backend(base_url)
            if not ok:
                return False, msg, active_url, {}, None, None
            if not sess_path.exists():
                return True, msg, active_url, {}, None, None
            raw = json.loads(sess_path.read_text(encoding="utf-8"))
            token = str(raw.get("token") or "").strip()
            if not token:
                raise ValueError("Empty token")
            tmp = CommunityApiClient(active_url, timeout=self.api.timeout)
            tmp.set_token(token)
            me = tmp.get_me()
            user = me.get("user") or {}
            health = tmp.health()
            return True, msg, active_url, health, token, user

        def _done(res):
            ok, msg, active_url, health, token, user = res
            self._apply_backend_result(ok, msg, active_url, health)
            if not ok or not token or not user:
                self.session = None
                self.session_changed.emit(None)
                if on_done:
                    on_done(None)
                return
            sess = CommunitySession(
                api_url=self.api_url,
                token=token,
                user_id=str(user["user_id"]),
                username=str(user["username"]),
            )
            self._activate_session(sess, persist=False)
            if on_done:
                on_done(sess)

        def _err(_err: CommunityApiError):
            self.clear_saved_session()
            self.api.set_token(None)
            self.session = None
            self.session_changed.emit(None)
            if on_done:
                on_done(None)

        return self.run_async("restore_session", _work, on_success=_done, on_error=_err, category="auth")

    def register_async(
        self,
        email: str,
        username: str,
        password: str,
        on_success: Optional[Callable[[CommunitySession], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        base_url = self.api_url

        def _work():
            ok, msg, active_url = resolve_communities_backend(base_url)
            if not ok:
                raise CommunityApiError(f"Servidor no disponible: {msg}", status_code=0, code="OFFLINE")
            tmp = CommunityApiClient(active_url, timeout=self.api.timeout)
            res = tmp.register(email=email, username=username, password=password)
            token = str(res.get("token") or "")
            if not token:
                res = tmp.login(identifier=email, password=password)
                token = str(res["token"])
            health = {}
            try:
                health = tmp.health()
            except Exception:
                pass
            return active_url, health, token, res

        def _done(payload):
            active_url, health, token, res = payload
            self._apply_backend_result(True, "connected", active_url, health)
            sess = CommunitySession(
                api_url=self.api_url,
                token=token,
                user_id=str(res["user_id"]),
                username=str(res["username"]),
            )
            self._activate_session(sess, persist=True)
            if on_success:
                on_success(sess)

        return self.run_async("register", _work, on_success=_done, on_error=on_error, category="auth")

    def login_async(
        self,
        identifier: str,
        password: str,
        on_success: Optional[Callable[[CommunitySession], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        base_url = self.api_url

        def _work():
            ok, msg, active_url = resolve_communities_backend(base_url)
            if not ok:
                raise CommunityApiError(f"Servidor no disponible: {msg}", status_code=0, code="OFFLINE")
            tmp = CommunityApiClient(active_url, timeout=self.api.timeout)
            res = tmp.login(identifier=identifier, password=password)
            health = {}
            try:
                health = tmp.health()
            except Exception:
                pass
            return active_url, health, res

        def _done(payload):
            active_url, health, res = payload
            self._apply_backend_result(True, "connected", active_url, health)
            sess = CommunitySession(
                api_url=self.api_url,
                token=str(res["token"]),
                user_id=str(res["user_id"]),
                username=str(res["username"]),
            )
            self._activate_session(sess, persist=True)
            if on_success:
                on_success(sess)

        return self.run_async("login", _work, on_success=_done, on_error=on_error, category="auth")

    def _cleanup_active_stream_sync(self) -> None:
        sess = self.active_stream_session
        ch = self.active_voice_channel
        self.active_stream_session = None
        self._stream_watching_channel_id = None
        if self.voice_engine.is_screen_sharing:
            try:
                self.voice_engine.stop_screen_share()
            except Exception:
                pass
        if sess and self.session:
            ch_id = str(sess.get("channel_id") or (ch or {}).get("id") or "")
            if ch_id:
                self.realtime.emit_stream_stop(ch_id)
                try:
                    self.api.stop_stream(ch_id, session_id=sess.get("id"))
                except Exception:
                    pass

    def _stop_active_game_sync(self) -> None:
        self.game_watcher.stop()
        if self._active_game_title and self.session:
            try:
                self.api.report_game_activity(
                    "stopped",
                    game_id=self._active_game_id,
                    title=self._active_game_title,
                    visibility=self.activity_visibility,
                )
            except Exception:
                pass
        self._active_game_id = None
        self._active_game_title = None
        self._active_game_pid = None

    def logout(self) -> None:
        self._heartbeat_timer.stop()
        self.cancel_pending()
        self._stop_active_game_sync()
        self._cleanup_active_stream_sync()
        self.voice_engine.disconnect()
        if self.active_voice_channel and self.session:
            try:
                self.api.leave_voice(self.active_voice_channel["id"])
            except Exception:
                pass
        if self.session:
            try:
                self.api.set_presence("offline")
            except Exception:
                pass
        self.realtime.disconnect_sync()
        self.api.set_token(None)
        self.session = None
        self.my_communities = []
        self.public_communities = []
        self.active_community = None
        self.active_channels = []
        self.active_channel = None
        self.active_members = []
        self.active_soundboard_sounds = []
        self._sound_audio_cache.clear()
        self.active_voice_channel = None
        self._active_voice_cred = None
        self._active_voice_reachable = False
        self.active_friends = []
        self.incoming_friend_requests = []
        self.active_activity_feed = []
        self.active_notifications = []
        self.unread_notifications_count = 0
        self._last_synced_msg_id = None
        self.clear_saved_session()
        self.stream_state_changed.emit({"live": False, "watching": False, "channel_id": None, "session": None})
        self.voice_state_changed.emit({"connected": False, "channel": None, "media_ready": False, "screen_live": False})
        self.notifications_updated.emit([], 0)
        self.session_changed.emit(None)

    def shutdown(self) -> None:
        """Cierra timers, workers pendientes, actividad de juego y conexión realtime sin borrar la sesión persistida."""
        self._heartbeat_timer.stop()
        self.cancel_pending()
        self._stop_active_game_sync()
        self._cleanup_active_stream_sync()
        self.voice_engine.disconnect()
        if self.active_voice_channel and self.session:
            try:
                self.api.leave_voice(self.active_voice_channel["id"])
            except Exception:
                pass
        if self.session:
            try:
                self.api.set_presence("offline")
            except Exception:
                pass
        self.realtime.disconnect_sync()
        self._thread_pool.waitForDone(1000)

    def _activate_session(self, sess: CommunitySession, persist: bool) -> None:
        self.session = sess
        self.api.set_token(sess.token)
        self.voice_engine.set_identity(sess.user_id, sess.username)
        if persist:
            self._save_session(sess)
        self.run_async(
            "set_presence_init",
            lambda: self.api.set_presence(
                self.current_presence_status,
                activity_visibility=self.activity_visibility,
            ),
            on_error=lambda _e: None,
            category="presence_sync",
        )
        self.realtime.connect_with_token(self.api_url, sess.token)
        if self._heartbeat_interval_ms > 0:
            self._heartbeat_timer.start()
        if self._enable_game_watcher:
            if not self._catalog_synced_to_watcher:
                self.sync_library_games_to_watcher()
            self.game_watcher.start()
        self.session_changed.emit(sess)
        self.presence_self_changed.emit(self.current_presence_status, self.activity_visibility)
        self.refresh_activity_and_notifications_async()

    def _save_session(self, sess: CommunitySession) -> None:
        try:
            self.session_path.parent.mkdir(parents=True, exist_ok=True)
            self.session_path.write_text(
                json.dumps(
                    {
                        "api_url": sess.api_url,
                        "token": sess.token,
                        "user_id": sess.user_id,
                        "username": sess.username,
                    }
                ),
                encoding="utf-8",
            )
            try:
                os.chmod(self.session_path, 0o600)
            except Exception:
                pass
        except Exception as exc:
            logger.warning("Failed to persist desktop session: %s", exc)

    def clear_saved_session(self) -> None:
        try:
            if self.session_path.exists():
                self.session_path.unlink()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Comunidades, canales, miembros y chat
    # ------------------------------------------------------------------
    def refresh_communities(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not self.session:
            raise CommunityApiError("Sesión no iniciada.", status_code=401, code="UNAUTHORIZED")
        mine = self.api.list_communities(discover_public=False)
        public = self.api.list_communities(discover_public=True)
        try:
            self.active_streams = self.api.list_active_streams()
        except Exception:
            self.active_streams = []
        self.my_communities = mine
        self.public_communities = public
        self.communities_updated.emit(mine, public)
        return mine, public

    def create_community(self, name: str, description: str = "", visibility: str = "private") -> Dict[str, Any]:
        comm = self.api.create_community(name=name, description=description, visibility=visibility)
        self.refresh_communities()
        return self.open_community(comm["id"])

    def join_public_community(self, community_id: str) -> Dict[str, Any]:
        self.api.join_public_community(community_id)
        self.refresh_communities()
        return self.open_community(community_id)

    def join_by_invitation(self, code_or_link: str) -> Dict[str, Any]:
        res = self.api.join_via_invitation(code_or_link)
        comm_id = res["community"]["id"]
        self.refresh_communities()
        return self.open_community(comm_id)

    def create_invitation(self, community_id: str) -> Dict[str, Any]:
        return self.api.create_invitation(community_id)

    def list_invitations(self, community_id: str) -> List[Dict[str, Any]]:
        return self.api.list_invitations(community_id)

    def revoke_invitation(self, community_id: str, code: str) -> bool:
        return self.api.revoke_invitation(community_id, code)

    def moderate_member(
        self,
        community_id: str,
        user_id: str,
        action: str,
        duration_seconds: Optional[int] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        res = self.api.moderate_member(
            community_id,
            user_id,
            action,
            duration_seconds=duration_seconds,
            reason=reason,
        )
        self.refresh_members()
        return res

    def leave_community(self, community_id: str) -> None:
        self.api.leave_community(community_id)
        if self.active_community and self.active_community["id"] == community_id:
            self.active_community = None
            self.active_channels = []
            self.active_channel = None
            self.active_members = []
        self.active_soundboard_sounds = []
        self._sound_audio_cache.clear()
        self.refresh_communities()

    def open_community(self, community_id: str) -> Dict[str, Any]:
        comm = self.api.get_community(community_id)
        channels = self.api.list_channels(community_id)
        members = self.api.list_members(community_id)
        members = self._attach_presences(members)

        self.active_community = comm
        self.active_channels = channels
        self.active_members = members
        self.realtime.join_community_room(community_id)

        payload = {
            "community": comm,
            "channels": channels,
            "members": members,
        }
        self.community_opened.emit(payload)

        text_channels = [c for c in channels if c.get("type") == "text"]
        if text_channels:
            self.select_channel(text_channels[0]["id"])
        else:
            self.active_channel = None
            self.channel_messages_loaded.emit("", [])
        return payload

    def create_channel(self, name: str, channel_type: str = "text", topic: str = "") -> Dict[str, Any]:
        if not self.active_community:
            raise CommunityApiError("No hay una comunidad abierta.", status_code=400)
        ch = self.api.create_channel(
            community_id=self.active_community["id"],
            name=name,
            channel_type=channel_type,
            topic=topic,
        )
        self.open_community(self.active_community["id"])
        if ch.get("type") == "text":
            self.select_channel(ch["id"])
        return ch

    def update_channel(self, channel_id: str, name: Optional[str] = None, topic: Optional[str] = None) -> Dict[str, Any]:
        if not self.active_community:
            raise CommunityApiError("No hay una comunidad abierta.", status_code=400)
        ch = self.api.update_channel(self.active_community["id"], channel_id, name=name, topic=topic)
        for i, existing in enumerate(self.active_channels):
            if existing["id"] == channel_id:
                self.active_channels[i] = ch
                break
        if self.active_channel and self.active_channel["id"] == channel_id:
            self.active_channel = ch
        self.community_opened.emit({
            "community": self.active_community,
            "channels": list(self.active_channels),
            "members": list(self.active_members),
        })
        return ch

    def delete_channel(self, channel_id: str) -> bool:
        if not self.active_community:
            raise CommunityApiError("No hay una comunidad abierta.", status_code=400)
        self.api.delete_channel(self.active_community["id"], channel_id)
        self.active_channels = [c for c in self.active_channels if c["id"] != channel_id]
        if self.active_channel and self.active_channel["id"] == channel_id:
            self.active_channel = None
            self._last_synced_msg_id = None
            self.channel_messages_loaded.emit("", [])
        self.community_opened.emit({
            "community": self.active_community,
            "channels": list(self.active_channels),
            "members": list(self.active_members),
        })
        return True

    def select_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        ch = next((c for c in self.active_channels if c["id"] == channel_id), None)
        if not ch:
            raise CommunityApiError("Canal no encontrado.", status_code=404)
        self.active_channel = ch
        self.realtime.join_channel_room(channel_id)
        msgs = self.api.list_messages(channel_id, limit=50)
        self._last_synced_msg_id = msgs[-1]["id"] if msgs else None
        self.channel_messages_loaded.emit(channel_id, msgs)
        return msgs

    def load_older_messages(self, before_id: str, limit: int = 40) -> List[Dict[str, Any]]:
        if not self.active_channel:
            return []
        return self.api.list_messages(self.active_channel["id"], limit=limit, before_id=before_id)

    def send_message(
        self,
        content: str,
        reply_to_id: Optional[str] = None,
        attachment_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.active_channel:
            raise CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
        return self.api.send_message(
            self.active_channel["id"],
            content=content,
            reply_to_id=reply_to_id,
            attachment_ids=attachment_ids,
        )

    def edit_message(self, message_id: str, content: str) -> Dict[str, Any]:
        if not self.active_channel:
            raise CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
        return self.api.edit_message(self.active_channel["id"], message_id, content)

    def delete_message(self, message_id: str) -> bool:
        if not self.active_channel:
            raise CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
        return self.api.delete_message(self.active_channel["id"], message_id)

    def toggle_reaction(self, message_id: str, emoji: str) -> Dict[str, Any]:
        if not self.active_channel:
            raise CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
        return self.api.toggle_reaction(self.active_channel["id"], message_id, emoji)

    def upload_attachment(self, file_path: str) -> Dict[str, Any]:
        if not self.active_channel:
            raise CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
        return self.api.upload_attachment(self.active_channel["id"], file_path)

    def emit_typing(self, typing: bool = True) -> None:
        if self.active_channel:
            self.realtime.emit_typing(self.active_channel["id"], typing=typing)

    # ------------------------------------------------------------------
    # Presencia, Actividad de Juego, Notificaciones y Amigos (Fase 3 / Unificación)
    # ------------------------------------------------------------------
    def _send_heartbeat(self) -> None:
        if not self.session:
            return
        st = self.current_presence_status
        vis = self.activity_visibility
        self.run_async(
            "heartbeat",
            lambda: self.api.heartbeat_presence(status=st, activity_visibility=vis),
            on_error=lambda _e: None,
            category="heartbeat",
        )

    def refresh_communities_async(
        self,
        on_done: Optional[Callable[[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        if not self.session:
            err = CommunityApiError("Sesión no iniciada.", status_code=401, code="UNAUTHORIZED")
            if on_error:
                on_error(err)
            else:
                self.error_occurred.emit(err.message)
            return 0

        def _work():
            mine = self.api.list_communities(discover_public=False)
            public = self.api.list_communities(discover_public=True)
            try:
                streams = self.api.list_active_streams()
            except Exception:
                streams = []
            return mine, public, streams

        def _apply(res):
            mine, public, streams = res
            self.my_communities = mine
            self.public_communities = public
            self.active_streams = streams
            self.communities_updated.emit(mine, public)
            if on_done:
                on_done((mine, public))

        return self.run_async("refresh_communities", _work, on_success=_apply, on_error=on_error, category="communities")

    def open_community_async(
        self,
        community_id: str,
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        self.cancel_pending("select_channel")

        def _work():
            comm = self.api.get_community(community_id)
            channels = self.api.list_channels(community_id)
            members = self.api.list_members(community_id)
            members = self._attach_presences(members)
            try:
                streams = self.api.list_active_streams(community_id)
            except Exception:
                streams = []
            text_channels = [c for c in channels if c.get("type") == "text"]
            first_msgs: List[Dict[str, Any]] = []
            first_ch_id = ""
            if text_channels:
                first_ch_id = str(text_channels[0]["id"])
                first_msgs = self.api.list_messages(first_ch_id, limit=50)
            return comm, channels, members, streams, text_channels, first_ch_id, first_msgs

        def _apply(res):
            comm, channels, members, streams, text_channels, first_ch_id, first_msgs = res
            self.active_community = comm
            self.active_channels = channels
            self.active_members = members
            self.active_streams = streams
            self.realtime.join_community_room(community_id)
            payload = {"community": comm, "channels": channels, "members": members, "streams": streams}
            self.community_opened.emit(payload)
            self.active_streams_updated.emit(streams)
            if text_channels:
                self.active_channel = text_channels[0]
                self.realtime.join_channel_room(first_ch_id)
                self._last_synced_msg_id = first_msgs[-1]["id"] if first_msgs else None
                self.channel_messages_loaded.emit(first_ch_id, first_msgs)
            else:
                self.active_channel = None
                self._last_synced_msg_id = None
                self.channel_messages_loaded.emit("", [])
            if on_done:
                on_done(payload)

        return self.run_async("open_community", _work, on_success=_apply, on_error=on_error, category="open_community")

    def select_channel_async(
        self,
        channel_id: str,
        on_done: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        ch = next((c for c in self.active_channels if c["id"] == channel_id), None)
        if not ch:
            err = CommunityApiError("Canal no encontrado.", status_code=404)
            if on_error:
                on_error(err)
            else:
                self.error_occurred.emit(err.message)
            return 0

        def _work():
            return self.api.list_messages(channel_id, limit=50)

        def _apply(msgs: List[Dict[str, Any]]):
            self.active_channel = ch
            self.realtime.join_channel_room(channel_id)
            self._last_synced_msg_id = msgs[-1]["id"] if msgs else None
            self.channel_messages_loaded.emit(channel_id, msgs)
            if on_done:
                on_done(msgs)

        return self.run_async("select_channel", _work, on_success=_apply, on_error=on_error, category="select_channel")

    def load_older_messages_async(
        self,
        before_id: str,
        limit: int = 40,
        on_done: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        if not self.active_channel:
            if on_done:
                on_done([])
            return 0
        ch_id = str(self.active_channel["id"])
        return self.run_async(
            "load_older_messages",
            lambda: self.api.list_messages(ch_id, limit=limit, before_id=before_id),
            on_success=on_done,
            on_error=on_error,
            category="older_messages",
        )

    def send_message_async(
        self,
        content: str,
        reply_to_id: Optional[str] = None,
        attachment_ids: Optional[List[str]] = None,
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        if not self.active_channel:
            err = CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
            if on_error:
                on_error(err)
            else:
                self.error_occurred.emit(err.message)
            return 0
        ch_id = str(self.active_channel["id"])
        return self.run_async(
            "send_message",
            lambda: self.api.send_message(ch_id, content=content, reply_to_id=reply_to_id, attachment_ids=attachment_ids),
            on_success=on_done,
            on_error=on_error,
        )

    def refresh_friends_async(
        self,
        on_done: Optional[Callable[[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        if not self.session:
            if on_done:
                on_done(([], []))
            return 0
        uid = str(self.session.user_id)

        def _work():
            data = self.api.get_friends(uid)
            friends = list(data.get("friends") or [])
            pending_raw = data.get("pending")
            if isinstance(pending_raw, dict):
                incoming = list(pending_raw.get("incoming") or [])
            else:
                incoming = list(data.get("incoming_requests") or [])
            return friends, incoming

        def _apply(res):
            friends, incoming = res
            self.active_friends = friends
            self.incoming_friend_requests = incoming
            self.friends_updated.emit(friends, incoming)
            if on_done:
                on_done((friends, incoming))

        return self.run_async("refresh_friends", _work, on_success=_apply, on_error=on_error, category="friends")

    def refresh_activity_and_notifications_async(self) -> int:
        if not self.session:
            return 0

        def _work():
            feed = self.api.get_activity_feed(limit=30)
            notifs = self.api.list_notifications()
            return feed, notifs

        def _apply(res):
            feed, notifs = res
            self.active_activity_feed = feed
            self.activity_feed_updated.emit(feed)
            unread = sum(1 for n in notifs if not n.get("is_read"))
            self.active_notifications = notifs
            self.unread_notifications_count = unread
            self.notifications_updated.emit(notifs, unread)

        return self.run_async(
            "refresh_activity",
            _work,
            on_success=_apply,
            on_error=lambda _e: None,
            category="activity_notifs",
        )

    def refresh_members_async(self) -> int:
        if not self.active_community:
            return 0
        cid = str(self.active_community["id"])

        def _work():
            members = self.api.list_members(cid)
            return self._attach_presences(members)

        def _apply(members):
            if self.active_community and str(self.active_community["id"]) == cid:
                self.active_members = members
                self.members_updated.emit(members)

        return self.run_async("refresh_members", _work, on_success=_apply, on_error=lambda _e: None, category="members")

    def set_status(self, status: str, custom_status: Optional[str] = None, activity_visibility: Optional[str] = None) -> Dict[str, Any]:
        self.current_presence_status = status
        if activity_visibility is not None:
            self.activity_visibility = activity_visibility
        res = self.api.set_presence(
            status=status,
            custom_status=custom_status,
            activity_visibility=self.activity_visibility,
        )
        self.presence_self_changed.emit(self.current_presence_status, self.activity_visibility)
        if self.active_community:
            try:
                self.refresh_members()
            except Exception:
                pass
        return res

    def set_activity_visibility(self, visibility: str) -> Dict[str, Any]:
        return self.set_status(self.current_presence_status, activity_visibility=visibility)

    # ------------------------------------------------------------------
    # Watcher real de juegos (P1-D: launcher + procesos del SO)
    # ------------------------------------------------------------------

    def register_watched_game(
        self,
        game_id: str,
        title: str,
        executable_names: Sequence[str] = (),
        cmdline_tokens: Sequence[str] = (),
        rom_paths: Sequence[str] = (),
    ) -> None:
        self.game_watcher.register_game_rule(
            game_id=game_id,
            title=title,
            executable_names=executable_names,
            cmdline_tokens=cmdline_tokens,
            rom_paths=rom_paths,
        )

    def set_watched_games(self, games: List[Dict[str, Any]]) -> int:
        self._catalog_synced_to_watcher = True
        return self.game_watcher.set_catalog_games(games)

    def sync_library_games_to_watcher(self, games: Optional[List[Dict[str, Any]]] = None) -> None:
        if games is not None:
            self.set_watched_games(games)
            return

        def _load_catalog() -> List[Dict[str, Any]]:
            from backend.games.scanner_service import GameLibraryScannerService
            return list(GameLibraryScannerService.get_instance().get_games())

        try:
            from backend.games.scanner_service import GameLibraryScannerService
            if GameLibraryScannerService._instance is not None:
                self.set_watched_games(list(GameLibraryScannerService._instance.get_games()))
                return
        except Exception:
            return

        self.run_async(
            "sync_game_watcher_catalog",
            _load_catalog,
            on_success=lambda items: self.set_watched_games(items),
            on_error=lambda _e: None,
            category="game_watcher_catalog",
        )

    def set_game_watcher_enabled(self, enabled: bool) -> None:
        self._enable_game_watcher = bool(enabled)
        if self._enable_game_watcher and self.session is not None:
            if not self._catalog_synced_to_watcher:
                self.sync_library_games_to_watcher()
            self.game_watcher.start()
        else:
            self.game_watcher.stop()

    def poll_game_watcher(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Ejecuta un barrido inmediato del watcher (útil en tests deterministas o bajo demanda)."""
        transitions = self.game_watcher.poll_once()
        return transitions

    def _apply_local_game_state(
        self,
        action: str,
        game_id: Optional[str],
        title: Optional[str],
        source: str = "manual",
        pid: Optional[int] = None,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        act = str(action or "").strip().lower()
        if act == "started":
            gid = str(game_id or title or "").strip() or None
            clean_title = str(title or gid or "").strip() or None
            self._active_game_id = gid
            self._active_game_title = clean_title
            self._active_game_pid = pid
        else:
            gid = str(game_id or self._active_game_id or title or "").strip() or None
            clean_title = str(title or self._active_game_title or gid or "Juego").strip()
            self._active_game_id = None
            self._active_game_title = None
            self._active_game_pid = None
        self.game_activity_changed.emit({
            "action": act,
            "game_id": gid,
            "title": clean_title,
            "source": source,
            "pid": pid,
        })
        return act, gid, clean_title

    def _on_watcher_game_started(self, payload: Dict[str, Any]) -> None:
        self.report_game_activity_async(
            "started",
            game_id=payload.get("game_id"),
            title=payload.get("title"),
            source=str(payload.get("source") or "process"),
            pid=payload.get("pid"),
        )

    def _on_watcher_game_stopped(self, payload: Dict[str, Any]) -> None:
        self.report_game_activity_async(
            "stopped",
            game_id=payload.get("game_id"),
            title=payload.get("title"),
            source=str(payload.get("source") or "process"),
            pid=payload.get("pid"),
        )

    def notify_game_launched(
        self,
        game_id: str,
        title: str,
        pid: Optional[int] = None,
        rom_path: Optional[str] = None,
        executable: Optional[str] = None,
        cmdline_tokens: Sequence[str] = (),
    ) -> Optional[Dict[str, Any]]:
        if rom_path or executable or cmdline_tokens:
            self.game_watcher.register_game_rule(
                game_id=str(game_id or title),
                title=str(title or game_id),
                executable_names=(executable,) if executable else (),
                cmdline_tokens=tuple(cmdline_tokens),
                rom_paths=(rom_path,) if rom_path else (),
            )
        payload = self.game_watcher.notify_launcher_started(
            game_id=str(game_id or title),
            title=str(title or game_id),
            pid=pid,
        )
        if payload is not None:
            self.report_game_activity_async(
                "started",
                game_id=payload.get("game_id"),
                title=payload.get("title"),
                source="launcher",
                pid=pid,
            )
        return payload

    def notify_game_exited(
        self,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        pid: Optional[int] = None,
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        payload = self.game_watcher.notify_launcher_stopped(
            game_id=game_id,
            title=title,
            pid=pid,
            force=force,
        )
        if payload is not None:
            self.report_game_activity_async(
                "stopped",
                game_id=payload.get("game_id"),
                title=payload.get("title"),
                source="launcher",
                pid=pid,
            )
        return payload

    def report_game_activity_async(
        self,
        action: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        source: str = "manual",
        pid: Optional[int] = None,
    ) -> int:
        if not self.session:
            return 0
        act = str(action or "").strip().lower()
        if act == "started":
            clean_gid = str(game_id or title or "").strip() or None
            clean_title = str(title or clean_gid or "").strip() or None
            if (
                self._active_game_title == clean_title
                and self._active_game_id == clean_gid
                and clean_title is not None
            ):
                return 0
        act, gid, clean_title = self._apply_local_game_state(act, game_id, title, source=source, pid=pid)
        vis = self.activity_visibility

        def _work():
            return self.api.report_game_activity(
                action=act,
                game_id=gid,
                title=clean_title,
                visibility=vis,
            )

        def _done(_res: Dict[str, Any]) -> None:
            if not self.session:
                return
            self.refresh_activity_and_notifications_async()
            self.refresh_friends_async()
            if self.active_community:
                self.refresh_members_async()

        return self.run_async(
            "report_game_activity",
            _work,
            on_success=_done,
            on_error=lambda _e: None,
            category="activity_game",
        )

    def report_game_activity(
        self,
        action: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.session:
            return None
        act, gid, clean_title = self._apply_local_game_state(action, game_id, title, source="manual")
        try:
            res = self.api.report_game_activity(
                action=act,
                game_id=gid,
                title=clean_title,
                visibility=self.activity_visibility,
            )
            self.refresh_activity_and_notifications()
            return res
        except Exception:
            return None

    def refresh_activity_and_notifications(self) -> None:
        if not self.session:
            return
        try:
            feed = self.api.get_activity_feed(limit=30)
            self.active_activity_feed = feed
            self.activity_feed_updated.emit(feed)
        except Exception:
            pass
        try:
            notifs = self.api.list_notifications()
            unread = sum(1 for n in notifs if not n.get("is_read"))
            self.active_notifications = notifs
            self.unread_notifications_count = unread
            self.notifications_updated.emit(notifs, unread)
        except Exception:
            pass

    def mark_all_notifications_read(self) -> None:
        if not self.session:
            return
        self.api.mark_notifications_read(None)
        self.refresh_activity_and_notifications()

    def refresh_friends(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not self.session:
            return [], []
        data = self.api.get_friends(self.session.user_id)
        friends = list(data.get("friends") or [])
        pending_raw = data.get("pending")
        if isinstance(pending_raw, dict):
            incoming = list(pending_raw.get("incoming") or [])
        else:
            incoming = list(data.get("incoming_requests") or [])
        self.active_friends = friends
        self.incoming_friend_requests = incoming
        self.friends_updated.emit(friends, incoming)
        return friends, incoming

    def send_friend_request(self, target_username: str) -> Dict[str, Any]:
        res = self.api.send_friend_request(target_username=target_username)
        self.refresh_friends()
        return res

    def respond_friend_request(self, from_user_id: str, accept: bool = True) -> Dict[str, Any]:
        res = self.api.respond_friend_request(
            requester_id=from_user_id,
            action="accept" if accept else "reject",
        )
        self.refresh_friends()
        return res

    def refresh_members(self) -> List[Dict[str, Any]]:
        if not self.active_community:
            return []
        members = self.api.list_members(self.active_community["id"])
        members = self._attach_presences(members)
        self.active_members = members
        self.members_updated.emit(members)
        return members

    def _attach_presences(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        uids = [str(m.get("user_id")) for m in members if m.get("user_id")]
        pres_map: Dict[str, Dict[str, Any]] = {}
        try:
            pres_map = self.api.get_presences(uids)
        except Exception:
            pres_map = {}
        out: List[Dict[str, Any]] = []
        for m in members:
            item = dict(m)
            uid = str(item.get("user_id", ""))
            p = pres_map.get(uid) or {}
            item["presence_status"] = p.get("status", "offline")
            item["custom_status"] = p.get("custom_status")
            item["activity_type"] = p.get("activity_type")
            item["activity_title"] = p.get("activity_title")
            item["activity_game_id"] = p.get("activity_game_id")
            out.append(item)
        return out

    # ------------------------------------------------------------------
    # Voz LiveKit WebRTC (P1-A) y fallback honesto a señalización
    # ------------------------------------------------------------------
    @staticmethod
    def _is_ws_url_reachable(ws_url: str, timeout: float = 0.25) -> bool:
        try:
            from urllib.parse import urlparse
            import socket
            parsed = urlparse(str(ws_url or ""))
            host = parsed.hostname
            if not host:
                return False
            port = parsed.port or (443 if parsed.scheme == "wss" else 7880)
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def _build_voice_state(
        self,
        ch: Dict[str, Any],
        cred: Optional[Dict[str, Any]],
        lk_reachable: bool,
    ) -> Dict[str, Any]:
        diag = self.voice_engine.get_diagnostics()
        media_ready = bool(diag.get("media_transport_active"))
        err = diag.get("last_error")
        if media_ready:
            lat = diag.get("latency_ms")
            lat_txt = f" ({lat:.0f} ms)" if isinstance(lat, (int, float)) else ""
            status_text = f"Audio WebRTC activo en {ch['name']}{lat_txt} — LiveKit SFU"
        elif lk_reachable and err:
            status_text = f"Solo señalización en {ch['name']} — Error RTC: {err}"
        elif lk_reachable:
            status_text = f"Token LiveKit emitido para {ch['name']} — Conectando audio WebRTC..."
        else:
            status_text = f"Token emitido para {ch['name']} — Servidor LiveKit SFU no alcanzable (solo señalización)"

        return {
            "connected": True,
            "channel": ch,
            "token_issued": bool((cred or {}).get("token")),
            "livekit_url": (cred or {}).get("url"),
            "room_name": (cred or {}).get("room_name"),
            "media_ready": media_ready,
            "livekit_media_plane": "reachable" if lk_reachable else "unreachable",
            "is_muted": bool(diag.get("is_muted")),
            "is_deafened": bool(diag.get("is_deafened")),
            "is_speaking": bool(diag.get("is_speaking")),
            "can_publish": bool(diag.get("can_publish", True)),
            "screen_live": bool(diag.get("is_screen_sharing")),
            "remote_screen_active": bool(diag.get("remote_screen_active")),
            "stream_session": self.active_stream_session,
            "latency_ms": diag.get("latency_ms"),
            "participants": self.voice_engine.list_participants(),
            "diagnostics": diag,
            "status_text": status_text,
        }

    def _on_voice_engine_participants_changed(self, participants: List[Dict[str, Any]]) -> None:
        if self.active_voice_channel is not None:
            self.voice_participants_updated.emit(participants)

    def _on_voice_engine_state_changed(self, diag: Dict[str, Any]) -> None:
        if self.active_voice_channel is not None and diag.get("is_connected"):
            state = self._build_voice_state(
                self.active_voice_channel,
                self._active_voice_cred,
                self._active_voice_reachable,
            )
            self.voice_state_changed.emit(state)

    def _connect_voice_worker(
        self,
        ch: Dict[str, Any],
        enable_audio_io: Optional[bool] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        channel_id = str(ch["id"])
        cred = self.api.request_voice_token(channel_id)
        health = {}
        try:
            health = self.api.health()
        except Exception:
            health = self.last_health

        lk_url = str(cred.get("url") or "")
        lk_reachable = (health.get("livekit_media_plane") == "reachable") or self._is_ws_url_reachable(lk_url)
        comm_id = str(ch.get("community_id") or (self.active_community or {}).get("id") or "")

        self.active_voice_channel = ch
        self._active_voice_cred = cred
        self._active_voice_reachable = lk_reachable
        if self.session:
            self.voice_engine.set_identity(self.session.user_id, self.session.username)

        self.voice_engine.connect(
            community_id=comm_id,
            channel_name=str(ch.get("name") or channel_id),
            token_info=cred if lk_reachable else None,
            enable_audio_io=enable_audio_io,
            connect_timeout=4.0,
        )
        return cred, lk_reachable

    def join_voice_channel(
        self,
        channel_id: str,
        enable_audio_io: Optional[bool] = None,
    ) -> Dict[str, Any]:
        ch = next((c for c in self.active_channels if c["id"] == channel_id), None)
        if not ch:
            raise CommunityApiError("Canal de voz no encontrado.", status_code=404)

        cred, lk_reachable = self._connect_voice_worker(ch, enable_audio_io=enable_audio_io)
        self.realtime.emit_voice_presence(channel_id, joined=True)
        state = self._build_voice_state(ch, cred, lk_reachable)
        self.voice_state_changed.emit(state)
        return state

    def join_voice_channel_async(
        self,
        channel_id: str,
        on_success: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
        enable_audio_io: Optional[bool] = None,
    ) -> int:
        ch = next((c for c in self.active_channels if c["id"] == channel_id), None)
        if not ch:
            err = CommunityApiError("Canal de voz no encontrado.", status_code=404)
            self.error_occurred.emit(err.message)
            if on_error:
                on_error(err)
            return -1

        def _done(res: Tuple[Dict[str, Any], bool]) -> None:
            cred, lk_reachable = res
            self.realtime.emit_voice_presence(str(ch["id"]), joined=True)
            state = self._build_voice_state(ch, cred, lk_reachable)
            self.voice_state_changed.emit(state)
            if on_success:
                on_success(state)

        return self.run_async(
            "join_voice",
            lambda: self._connect_voice_worker(ch, enable_audio_io=enable_audio_io),
            on_success=_done,
            on_error=on_error,
            category="voice",
        )

    def set_voice_mute(self, muted: Optional[bool] = None) -> bool:
        res = self.voice_engine.set_mute(muted)
        if self.active_voice_channel:
            self.realtime.emit_voice_mute(str(self.active_voice_channel["id"]), res)
        return res

    def set_voice_deafen(self, deafened: Optional[bool] = None) -> bool:
        res = self.voice_engine.set_deafen(deafened)
        if self.active_voice_channel:
            self.realtime.emit_voice_mute(str(self.active_voice_channel["id"]), self.voice_engine.is_muted)
        return res

    def get_voice_diagnostics(self) -> Dict[str, Any]:
        return self.voice_engine.get_diagnostics()

    def leave_voice_channel(self) -> None:
        self._cleanup_active_stream_sync()
        ch = self.active_voice_channel
        self.active_voice_channel = None
        self._active_voice_cred = None
        self._active_voice_reachable = False
        self.voice_engine.disconnect()
        if ch:
            ch_id = str(ch["id"])
            self.realtime.emit_voice_presence(ch_id, joined=False)
            self.run_async(
                "leave_voice",
                lambda: self.api.leave_voice(ch_id),
                on_error=lambda _e: None,
                category="voice_leave",
            )
        self.stream_state_changed.emit({"live": False, "watching": False, "channel_id": None, "session": None})
        self.voice_state_changed.emit({"connected": False, "channel": None, "media_ready": False, "screen_live": False})

    # ------------------------------------------------------------------
    # Streaming real de pantalla / juego sobre LiveKit WebRTC (P1-B)
    # ------------------------------------------------------------------
    def get_stream_sources(self) -> Dict[str, Any]:
        from backend.communities.stream_adapter import detect_available_capture_sources
        local_sources = detect_available_capture_sources(force_headless=False)
        if self.session:
            try:
                remote_info = self.api.get_stream_sources()
                local_sources["capture_limits"] = remote_info.get("capture_limits") or {}
            except Exception:
                pass
        return local_sources

    def _build_stream_state(
        self,
        live: bool,
        ch: Optional[Dict[str, Any]] = None,
        session_data: Optional[Dict[str, Any]] = None,
        watching: bool = False,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        diag = self.voice_engine.get_diagnostics()
        return {
            "live": bool(live and diag.get("is_screen_sharing")),
            "watching": bool(watching),
            "channel_id": str(ch["id"]) if ch and ch.get("id") else (session_data or {}).get("channel_id"),
            "channel": ch,
            "session": session_data,
            "source_id": diag.get("screen_share_source_id"),
            "width": diag.get("screen_share_width"),
            "height": diag.get("screen_share_height"),
            "fps": diag.get("screen_share_fps"),
            "tx_frames": diag.get("screen_tx_frames"),
            "rx_frames": diag.get("screen_rx_frames"),
            "error": error,
        }

    def _start_screen_share_worker(
        self,
        ch: Dict[str, Any],
        source_id: str,
        resolution: str,
        fps: int,
        bitrate_kbps: int,
        with_audio: bool,
        title: Optional[str],
        stream_type: str,
        frame_provider: Optional[Callable[[], Optional[tuple[int, int, bytes]]]],
        window_widget: Any,
        enable_audio_io: Optional[bool],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        from backend.communities.stream_adapter import parse_resolution_dimensions

        channel_id = str(ch["id"])
        if not (
            self.active_voice_channel
            and str(self.active_voice_channel.get("id")) == channel_id
            and self.voice_engine.is_connected
        ):
            self._connect_voice_worker(ch, enable_audio_io=enable_audio_io)
            self.realtime.emit_voice_presence(channel_id, joined=True)

        if not self.voice_engine.media_transport_active:
            raise CommunityApiError(
                "Servidor LiveKit SFU no disponible para publicar pantalla en tiempo real.",
                status_code=503,
                code="RTC_MEDIA_UNAVAILABLE",
            )

        session_data = self.api.start_stream(
            channel_id=channel_id,
            stream_type=stream_type,
            title=title or f"Pantalla de {self.session.username if self.session else 'Usuario'}",
            resolution=resolution,
            fps=int(fps),
            bitrate_kbps=int(bitrate_kbps),
            has_audio=bool(with_audio),
        )
        w, h = parse_resolution_dimensions(resolution)
        published = self.voice_engine.start_screen_share(
            source_id=source_id,
            width=w,
            height=h,
            fps=int(fps),
            with_audio=bool(with_audio),
            max_bitrate=max(250, int(bitrate_kbps)) * 1000,
            frame_provider=frame_provider,
            window_widget=window_widget,
        )
        if not published:
            try:
                self.api.stop_stream(channel_id, session_id=session_data.get("id"))
            except Exception:
                pass
            raise CommunityApiError(
                self.voice_engine.last_error or "LiveKit SFU no confirmó la publicación del track de pantalla.",
                status_code=503,
                code="RTC_STREAM_PUBLISH_FAILED",
            )
        return ch, session_data

    def start_screen_share(
        self,
        channel_id: Optional[str] = None,
        source_id: str = "screen:0",
        resolution: str = "720p",
        fps: int = 30,
        bitrate_kbps: int = 2500,
        with_audio: bool = False,
        title: Optional[str] = None,
        stream_type: str = "screen",
        frame_provider: Optional[Callable[[], Optional[tuple[int, int, bytes]]]] = None,
        window_widget: Any = None,
        enable_audio_io: Optional[bool] = None,
    ) -> Dict[str, Any]:
        target_id = str(channel_id or (self.active_voice_channel or {}).get("id") or "")
        ch = next((c for c in self.active_channels if str(c.get("id")) == target_id), None) or self.active_voice_channel
        if not ch:
            raise CommunityApiError("Conéctate a un canal de voz antes de compartir pantalla.", status_code=400)

        ch_obj, session_data = self._start_screen_share_worker(
            ch=ch,
            source_id=source_id,
            resolution=resolution,
            fps=fps,
            bitrate_kbps=bitrate_kbps,
            with_audio=with_audio,
            title=title,
            stream_type=stream_type,
            frame_provider=frame_provider,
            window_widget=window_widget,
            enable_audio_io=enable_audio_io,
        )
        self.active_stream_session = session_data
        self.realtime.emit_stream_start(
            str(ch_obj["id"]),
            stream_type=stream_type,
            title=str(session_data.get("title") or title or "Pantalla"),
            resolution=resolution,
            fps=int(fps),
        )
        state = self._build_stream_state(live=True, ch=ch_obj, session_data=session_data)
        self.stream_state_changed.emit(state)
        self.voice_state_changed.emit(
            self._build_voice_state(ch_obj, self._active_voice_cred, self._active_voice_reachable)
        )
        return state

    def start_screen_share_async(
        self,
        channel_id: Optional[str] = None,
        source_id: str = "screen:0",
        resolution: str = "720p",
        fps: int = 30,
        bitrate_kbps: int = 2500,
        with_audio: bool = False,
        title: Optional[str] = None,
        stream_type: str = "screen",
        frame_provider: Optional[Callable[[], Optional[tuple[int, int, bytes]]]] = None,
        window_widget: Any = None,
        enable_audio_io: Optional[bool] = None,
        on_success: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        target_id = str(channel_id or (self.active_voice_channel or {}).get("id") or "")
        ch = next((c for c in self.active_channels if str(c.get("id")) == target_id), None) or self.active_voice_channel
        if not ch:
            err = CommunityApiError("Conéctate a un canal de voz antes de compartir pantalla.", status_code=400)
            self.error_occurred.emit(err.message)
            self.stream_state_changed.emit(self._build_stream_state(live=False, error=err.message))
            if on_error:
                on_error(err)
            return -1

        def _done(res: Tuple[Dict[str, Any], Dict[str, Any]]) -> None:
            ch_obj, session_data = res
            self.active_stream_session = session_data
            self.realtime.emit_stream_start(
                str(ch_obj["id"]),
                stream_type=stream_type,
                title=str(session_data.get("title") or title or "Pantalla"),
                resolution=resolution,
                fps=int(fps),
            )
            state = self._build_stream_state(live=True, ch=ch_obj, session_data=session_data)
            self.stream_state_changed.emit(state)
            self.voice_state_changed.emit(
                self._build_voice_state(ch_obj, self._active_voice_cred, self._active_voice_reachable)
            )
            if on_success:
                on_success(state)

        def _err(api_err: CommunityApiError) -> None:
            self.active_stream_session = None
            self.stream_state_changed.emit(self._build_stream_state(live=False, ch=ch, error=api_err.message))
            if self.active_voice_channel:
                self.voice_state_changed.emit(
                    self._build_voice_state(self.active_voice_channel, self._active_voice_cred, self._active_voice_reachable)
                )
            if on_error:
                on_error(api_err)

        return self.run_async(
            "start_screen_share",
            lambda: self._start_screen_share_worker(
                ch=ch,
                source_id=source_id,
                resolution=resolution,
                fps=fps,
                bitrate_kbps=bitrate_kbps,
                with_audio=with_audio,
                title=title,
                stream_type=stream_type,
                frame_provider=frame_provider,
                window_widget=window_widget,
                enable_audio_io=enable_audio_io,
            ),
            on_success=_done,
            on_error=_err,
            category="screen_share",
        )

    def stop_screen_share(self) -> Dict[str, Any]:
        sess = self.active_stream_session
        ch = self.active_voice_channel
        self.active_stream_session = None
        self.voice_engine.stop_screen_share()
        ch_id = str((sess or {}).get("channel_id") or (ch or {}).get("id") or "")
        if ch_id and self.session:
            self.realtime.emit_stream_stop(ch_id)
            try:
                self.api.stop_stream(ch_id, session_id=(sess or {}).get("id"))
            except Exception:
                pass
        state = self._build_stream_state(live=False, ch=ch, session_data=None)
        self.stream_state_changed.emit(state)
        if self.active_voice_channel:
            self.voice_state_changed.emit(
                self._build_voice_state(self.active_voice_channel, self._active_voice_cred, self._active_voice_reachable)
            )
        return state

    def stop_screen_share_async(
        self,
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> int:
        sess = self.active_stream_session
        ch = self.active_voice_channel
        self.active_stream_session = None
        self.voice_engine.stop_screen_share()
        ch_id = str((sess or {}).get("channel_id") or (ch or {}).get("id") or "")
        state = self._build_stream_state(live=False, ch=ch, session_data=None)
        self.stream_state_changed.emit(state)
        if self.active_voice_channel:
            self.voice_state_changed.emit(
                self._build_voice_state(self.active_voice_channel, self._active_voice_cred, self._active_voice_reachable)
            )

        def _work():
            if ch_id and self.session:
                self.realtime.emit_stream_stop(ch_id)
                try:
                    self.api.stop_stream(ch_id, session_id=(sess or {}).get("id"))
                except Exception:
                    pass
            return state

        return self.run_async(
            "stop_screen_share",
            _work,
            on_success=lambda st: on_done(st) if on_done else None,
            on_error=lambda _e: on_done(state) if on_done else None,
            category="screen_share_stop",
        )

    def watch_stream(
        self,
        channel_id: str,
        enable_audio_io: Optional[bool] = None,
    ) -> Dict[str, Any]:
        ch = next((c for c in self.active_channels if str(c.get("id")) == str(channel_id)), None)
        if not ch:
            raise CommunityApiError("Canal de transmisión no encontrado.", status_code=404)
        stream_info = self.api.get_channel_stream(str(channel_id))
        if not (
            self.active_voice_channel
            and str(self.active_voice_channel.get("id")) == str(channel_id)
            and self.voice_engine.is_connected
        ):
            self._connect_voice_worker(ch, enable_audio_io=enable_audio_io)
            self.realtime.emit_voice_presence(str(channel_id), joined=True)
            self.voice_state_changed.emit(
                self._build_voice_state(ch, self._active_voice_cred, self._active_voice_reachable)
            )
        self._stream_watching_channel_id = str(channel_id)
        state = self._build_stream_state(
            live=bool(self.voice_engine.is_screen_sharing),
            ch=ch,
            session_data=stream_info,
            watching=True,
        )
        self.stream_state_changed.emit(state)
        latest = self.voice_engine.get_latest_remote_video_frame()
        if latest is not None:
            pid, fw, fh, rgba = latest
            self.remote_video_frame_received.emit(pid, fw, fh, rgba)
        return state

    def stop_watching_stream(self) -> None:
        self._stream_watching_channel_id = None
        state = self._build_stream_state(
            live=bool(self.voice_engine.is_screen_sharing),
            ch=self.active_voice_channel,
            session_data=self.active_stream_session,
            watching=False,
        )
        self.stream_state_changed.emit(state)

    def push_screen_video_frame(self, width: int, height: int, rgba_bytes: bytes) -> bool:
        return self.voice_engine.push_video_frame(width, height, rgba_bytes)

    def push_screen_audio_frame(self, samples: Any) -> bool:
        return self.voice_engine.push_screen_audio_frame(samples)

    # ------------------------------------------------------------------
    # Soundboard RTC (P1-C)
    # ------------------------------------------------------------------
    def load_soundboard(self, community_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.session:
            raise CommunityApiError("Sesión no iniciada.", status_code=401)
        presets = [dict(p, is_preset=True) for p in self.api.list_sound_presets()]
        cid = str(community_id or (self.active_community or {}).get("id") or "")
        uploaded: List[Dict[str, Any]] = []
        if cid:
            try:
                for item in self.api.list_community_sounds(cid):
                    entry = dict(item)
                    entry["is_preset"] = False
                    uploaded.append(entry)
            except Exception:
                uploaded = []
        combined = presets + uploaded
        self.active_soundboard_sounds = combined
        self.soundboard_loaded.emit(list(combined))
        return combined

    def load_soundboard_async(
        self,
        community_id: Optional[str] = None,
        on_done: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        return self.run_async(
            "load_soundboard",
            lambda: self.load_soundboard(community_id=community_id),
            on_success=on_done,
            on_error=on_error,
            category="soundboard_load",
        )

    def upload_sound_file(
        self,
        file_path: str,
        title: Optional[str] = None,
        owner_type: str = "community",
        community_id: Optional[str] = None,
        volume_scale: float = 1.0,
        cooldown_seconds: int = 5,
    ) -> Dict[str, Any]:
        if not self.session:
            raise CommunityApiError("Sesión no iniciada.", status_code=401)
        p = Path(file_path)
        if not p.is_file():
            raise CommunityApiError("Archivo de audio no encontrado.", status_code=400)
        file_bytes = p.read_bytes()
        cid = str(community_id or (self.active_community or {}).get("id") or "")
        created = self.api.upload_sound(
            title=(title or p.stem or "Sonido").strip(),
            file_bytes=file_bytes,
            owner_type=owner_type,
            owner_id=cid if owner_type == "community" else None,
            volume_scale=volume_scale,
            cooldown_seconds=cooldown_seconds,
        )
        sid = str(created.get("id") or "")
        if sid:
            self._sound_audio_cache[sid] = file_bytes
        self.load_soundboard(community_id=cid or None)
        return created

    def upload_sound_file_async(
        self,
        file_path: str,
        title: Optional[str] = None,
        owner_type: str = "community",
        community_id: Optional[str] = None,
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        return self.run_async(
            "upload_sound",
            lambda: self.upload_sound_file(
                file_path=file_path,
                title=title,
                owner_type=owner_type,
                community_id=community_id,
            ),
            on_success=on_done,
            on_error=on_error,
            category="soundboard_upload",
        )

    def _prepare_soundboard_effect_worker(
        self,
        sound_id: str,
        target_channel_id: str,
        volume_scale: Optional[float],
    ) -> Tuple[Dict[str, Any], Any, float]:
        from backend.communities.sound_audio import (
            decode_audio_bytes_to_pcm,
            get_soundboard_preset,
            synthesize_preset_pcm,
        )

        preset = get_soundboard_preset(sound_id)
        if preset is not None:
            auth = self.api.authorize_sound_preset(target_channel_id, str(preset["id"]))
            vol = float(volume_scale if volume_scale is not None else auth.get("volume_scale", 0.75))
            pcm = synthesize_preset_pcm(
                str(preset["id"]),
                volume_scale=vol,
                sample_rate=self.voice_engine.SAMPLE_RATE,
            )
            return auth, pcm, vol

        auth = self.api.authorize_sound_play(sound_id, target_channel_id)
        vol = float(volume_scale if volume_scale is not None else auth.get("volume_scale", 1.0))
        cached = self._sound_audio_cache.get(sound_id)
        if cached is None:
            cached = self.api.download_sound_audio(sound_id)
            self._sound_audio_cache[sound_id] = cached
        try:
            pcm = decode_audio_bytes_to_pcm(
                cached,
                volume_scale=vol,
                target_sample_rate=self.voice_engine.SAMPLE_RATE,
            )
        except Exception as exc:
            raise CommunityApiError(
                f"No se pudo decodificar el audio '{auth.get('title') or sound_id}': {exc}",
                status_code=422,
                code="AUDIO_DECODE_FAILED",
            ) from exc
        return auth, pcm, vol

    def play_soundboard_effect(
        self,
        sound_id: str,
        channel_id: Optional[str] = None,
        volume_scale: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self.session:
            raise CommunityApiError("Sesión no iniciada.", status_code=401)
        ch = self.active_voice_channel
        target_id = str(channel_id or (ch or {}).get("id") or "")
        if not target_id or not self.voice_engine.is_connected:
            raise CommunityApiError("Conéctate a un canal de voz antes de usar el soundboard.", status_code=400)
        if not self.voice_engine.media_transport_active:
            raise CommunityApiError(
                "Transporte WebRTC LiveKit no activo para transmitir audio del soundboard.",
                status_code=503,
                code="RTC_MEDIA_UNAVAILABLE",
            )
        if self.voice_engine.is_muted or self.voice_engine.is_deafened:
            raise CommunityApiError(
                "Desactiva silencio/ensordecido para reproducir efectos en el canal de voz.",
                status_code=400,
                code="VOICE_MUTED",
            )

        auth, pcm, eff_vol = self._prepare_soundboard_effect_worker(sound_id, target_id, volume_scale)
        eff_id = str(auth.get("sound_id") or sound_id)
        title = str(auth.get("title") or eff_id)
        injected = self.voice_engine.play_soundboard_pcm(
            pcm,
            sound_id=eff_id,
            title=title,
            volume_scale=1.0,
        )
        if not injected:
            raise CommunityApiError(
                self.voice_engine.last_error or "No se pudo inyectar el efecto en el track RTC.",
                status_code=503,
                code="RTC_SOUNDBOARD_FAILED",
            )
        self.realtime.emit_sound_play(target_id, eff_id, title=title, volume_scale=eff_vol)
        res = {
            **auth,
            "channel_id": target_id,
            "rtc_injected": True,
            "user_id": self.session.user_id,
        }
        self.soundboard_event.emit({"action": "played", **res})
        return res

    def play_soundboard_effect_async(
        self,
        sound_id: str,
        channel_id: Optional[str] = None,
        volume_scale: Optional[float] = None,
        on_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[CommunityApiError], None]] = None,
    ) -> int:
        return self.run_async(
            "play_soundboard",
            lambda: self.play_soundboard_effect(
                sound_id=sound_id,
                channel_id=channel_id,
                volume_scale=volume_scale,
            ),
            on_success=on_done,
            on_error=on_error,
            category="soundboard_play",
        )

    def stop_soundboard_effect(
        self,
        sound_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> int:
        active_id = sound_id or self.voice_engine._active_sound_id
        removed = self.voice_engine.stop_soundboard_audio(sound_id=sound_id)
        ch_id = str(channel_id or (self.active_voice_channel or {}).get("id") or "")
        if removed > 0 and ch_id and active_id and self.session:
            self.realtime.emit_sound_stop(ch_id, str(active_id))
            self.soundboard_event.emit({
                "action": "stopped",
                "channel_id": ch_id,
                "sound_id": str(active_id),
                "user_id": self.session.user_id,
            })
        return removed

    def _on_rt_connected(self) -> None:
        self.realtime_status_changed.emit(True, "Realtime Socket.IO conectado")
        # Recuperación automática tras reconexión fuera del hilo GUI sin duplicar
        if self.session and self.active_channel and self._last_synced_msg_id:
            ch_id = str(self.active_channel["id"])
            since_id = str(self._last_synced_msg_id)

            def _apply_missed(missed: List[Dict[str, Any]]) -> None:
                if missed and self.active_channel and str(self.active_channel["id"]) == ch_id:
                    self._last_synced_msg_id = missed[-1]["id"]
                    self.messages_synced.emit(ch_id, missed)

            self.run_async(
                "sync_missed_messages",
                lambda: self.api.list_messages(ch_id, limit=100, after_id=since_id),
                on_success=_apply_missed,
                on_error=lambda _e: None,
                category="sync_missed",
            )

    def _on_rt_disconnected(self, reason: str) -> None:
        self.realtime_status_changed.emit(False, reason)

    def _on_rt_message_created(self, msg: Dict[str, Any]) -> None:
        if self.active_channel and msg.get("channel_id") == self.active_channel["id"]:
            if msg.get("id"):
                self._last_synced_msg_id = str(msg["id"])
            self.message_received.emit(msg)

    def _on_rt_message_updated(self, msg: Dict[str, Any]) -> None:
        if self.active_channel and msg.get("channel_id") == self.active_channel["id"]:
            self.message_updated.emit(msg)

    def _on_rt_message_deleted(self, payload: Dict[str, Any]) -> None:
        if self.active_channel and payload.get("channel_id") == self.active_channel["id"]:
            self.message_deleted.emit(payload)

    def _on_rt_reaction_updated(self, payload: Dict[str, Any]) -> None:
        if self.active_channel and payload.get("channel_id") == self.active_channel["id"]:
            self.reaction_updated.emit(payload)

    def _on_rt_channel_created(self, payload: Dict[str, Any]) -> None:
        if self.active_community and payload.get("community_id") == self.active_community["id"]:
            ch = payload.get("channel")
            if ch and not any(c["id"] == ch["id"] for c in self.active_channels):
                self.active_channels.append(ch)
                self.community_opened.emit({
                    "community": self.active_community,
                    "channels": list(self.active_channels),
                    "members": list(self.active_members),
                })

    def _on_rt_channel_updated(self, payload: Dict[str, Any]) -> None:
        ch = payload.get("channel") or {}
        if self.active_community and payload.get("community_id") == self.active_community["id"] and ch.get("id"):
            for i, existing in enumerate(self.active_channels):
                if existing["id"] == ch["id"]:
                    self.active_channels[i] = ch
                    break
            if self.active_channel and self.active_channel["id"] == ch["id"]:
                self.active_channel = ch
            self.community_opened.emit({
                "community": self.active_community,
                "channels": list(self.active_channels),
                "members": list(self.active_members),
            })

    def _on_rt_channel_deleted(self, payload: Dict[str, Any]) -> None:
        ch_id = payload.get("channel_id")
        if self.active_community and payload.get("community_id") == self.active_community["id"] and ch_id:
            self.active_channels = [c for c in self.active_channels if c["id"] != ch_id]
            if self.active_channel and self.active_channel["id"] == ch_id:
                self.active_channel = None
                self._last_synced_msg_id = None
                self.channel_messages_loaded.emit("", [])
            self.community_opened.emit({
                "community": self.active_community,
                "channels": list(self.active_channels),
                "members": list(self.active_members),
            })

    def _on_rt_member_change(self, payload: Dict[str, Any]) -> None:
        if self.active_community and payload.get("community_id") == self.active_community["id"]:
            self.refresh_members_async()

    def _on_rt_presence_updated(self, presence: Dict[str, Any]) -> None:
        uid = str(presence.get("user_id") or "")
        if not uid:
            return
        changed = False
        for m in self.active_members:
            if str(m.get("user_id")) == uid:
                m["presence_status"] = presence.get("status", "offline")
                m["custom_status"] = presence.get("custom_status")
                m["activity_type"] = presence.get("activity_type")
                m["activity_title"] = presence.get("activity_title")
                m["activity_game_id"] = presence.get("activity_game_id")
                changed = True
        if changed:
            self.members_updated.emit(list(self.active_members))

        friends_changed = False
        raw_status = str(presence.get("status") or "offline")
        legacy_status = {"idle": "away", "dnd": "busy"}.get(raw_status, raw_status)
        if legacy_status == "invisible":
            legacy_status = "offline"
        raw_game = presence.get("activity_title") or presence.get("game")
        game_title = None if legacy_status == "offline" else raw_game
        for f in self.active_friends:
            fid = str(f.get("friend_id") or f.get("user_id") or "")
            if fid == uid:
                f["presence"] = legacy_status
                f["presence_status"] = raw_status
                f["current_game"] = game_title
                f["activity_type"] = None if legacy_status == "offline" else presence.get("activity_type")
                f["activity_title"] = game_title
                f["activity_game_id"] = None if legacy_status == "offline" else presence.get("activity_game_id")
                friends_changed = True
        if friends_changed:
            self.friends_updated.emit(list(self.active_friends), list(self.incoming_friend_requests))

    def _on_rt_typing_updated(self, payload: Dict[str, Any]) -> None:
        if self.active_channel and payload.get("channel_id") == self.active_channel["id"]:
            self.typing_updated.emit(payload)

    def _on_rt_activity_updated(self, payload: Dict[str, Any]) -> None:
        if not self.session:
            return
        # Inserción push inmediata en el feed local (sin necesidad de esperar refresh manual)
        if isinstance(payload, dict) and (payload.get("game_title") or payload.get("title") or payload.get("game_id")):
            item = dict(payload)
            if item.get("title") and not item.get("game_title"):
                item["game_title"] = item.get("title")
            if item.get("game_title") and not item.get("title"):
                item["title"] = item.get("game_title")
            ev_id = str(item.get("id") or "")
            existing = list(self.active_activity_feed or [])
            if not ev_id or not any(str(prev.get("id") or "") == ev_id for prev in existing):
                updated_feed = [item] + existing
                self.active_activity_feed = updated_feed[:30]
                self.activity_feed_updated.emit(list(self.active_activity_feed))

            uid = str(item.get("user_id") or "")
            ev_kind = str(item.get("event") or item.get("event_type") or "")
            is_start = "started" in ev_kind
            is_stop = "stopped" in ev_kind
            if uid and (is_start or is_stop):
                friends_changed = False
                for f in self.active_friends:
                    fid = str(f.get("friend_id") or f.get("user_id") or "")
                    if fid == uid:
                        f["current_game"] = (item.get("game_title") or item.get("title")) if is_start else None
                        f["activity_title"] = f["current_game"]
                        f["activity_type"] = "playing" if is_start else None
                        f["activity_game_id"] = item.get("game_id") if is_start else None
                        friends_changed = True
                if friends_changed:
                    self.friends_updated.emit(list(self.active_friends), list(self.incoming_friend_requests))
        self.refresh_activity_and_notifications_async()

    def _on_rt_notification_received(self, payload: Dict[str, Any]) -> None:
        if self.session:
            self.refresh_activity_and_notifications_async()

    def _refresh_active_streams_async(self) -> None:
        if not self.session or not self.active_community:
            return
        comm_id = str(self.active_community.get("id") or "")
        if not comm_id:
            return

        def _apply(streams: List[Dict[str, Any]]) -> None:
            self.active_streams = list(streams or [])
            self.active_streams_updated.emit(list(self.active_streams))

        self.run_async(
            "refresh_streams",
            lambda: self.api.list_active_streams(comm_id),
            on_success=_apply,
            on_error=lambda _e: None,
            category="streams",
        )

    def _on_rt_stream_started(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return
        ch_id = str(payload.get("channel_id") or "")
        if ch_id and not any(str(s.get("channel_id")) == ch_id for s in self.active_streams):
            self.active_streams.append(dict(payload))
            self.active_streams_updated.emit(list(self.active_streams))
        self._refresh_active_streams_async()
        if self.active_voice_channel and str(self.active_voice_channel.get("id")) == ch_id:
            self.stream_state_changed.emit(
                self._build_stream_state(
                    live=bool(self.voice_engine.is_screen_sharing),
                    ch=self.active_voice_channel,
                    session_data=payload,
                    watching=True,
                )
            )

    def _on_rt_stream_paused(self, payload: Dict[str, Any]) -> None:
        self._refresh_active_streams_async()

    def _on_rt_stream_ended(self, payload: Dict[str, Any]) -> None:
        ch_id = str((payload or {}).get("channel_id") or "")
        uid = str((payload or {}).get("user_id") or "")
        if ch_id:
            self.active_streams = [s for s in self.active_streams if str(s.get("channel_id")) != ch_id]
            self.active_streams_updated.emit(list(self.active_streams))
        if self._stream_watching_channel_id == ch_id:
            self._stream_watching_channel_id = None
        if uid:
            self.remote_stream_ended.emit(uid)
        elif ch_id:
            self.remote_stream_ended.emit(ch_id)
        if self.active_voice_channel and str(self.active_voice_channel.get("id")) == ch_id:
            self.stream_state_changed.emit(
                self._build_stream_state(
                    live=bool(self.voice_engine.is_screen_sharing),
                    ch=self.active_voice_channel,
                    session_data=self.active_stream_session,
                    watching=False,
                )
            )

    def _on_rt_sound_played(self, payload: Dict[str, Any]) -> None:
        if isinstance(payload, dict):
            self.soundboard_event.emit({"action": "played", **payload})

    def _on_rt_sound_stopped(self, payload: Dict[str, Any]) -> None:
        if isinstance(payload, dict):
            self.soundboard_event.emit({"action": "stopped", **payload})
