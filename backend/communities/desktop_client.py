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
import json
import logging
import os
from pathlib import Path
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import socketio
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

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

    def download_attachment_bytes(self, attachment_id: str) -> bytes:
        url = f"{self.api_url}/api/v1/attachments/{attachment_id}"
        hdrs = {}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        try:
            resp = self._http.get(url, headers=hdrs, timeout=self.timeout)
        except requests.RequestException as exc:
            raise CommunityApiError(f"Error descargando adjunto: {exc}", status_code=0) from exc
        if resp.status_code >= 400:
            raise CommunityApiError(f"Adjunto no disponible (HTTP {resp.status_code})", status_code=resp.status_code)
        return bytes(resp.content)

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

    def emit_typing(self, channel_id: str, typing: bool = True) -> None:
        with self._lock:
            sio = self._sio
        if sio and sio.connected and channel_id:
            try:
                sio.emit("community:typing", {"channel_id": channel_id, "typing": bool(typing)})
            except Exception:
                pass

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


class _RestTaskSignals(QObject):
    succeeded = Signal(int, object)
    failed = Signal(int, str, int, str)  # task_id, message, status_code, code


class _RestWorker(QRunnable):
    """Worker thread para llamadas REST fuera del hilo GUI con soporte de cancelación."""

    def __init__(
        self,
        task_id: int,
        fn: Callable[[], Any],
        cancelled: threading.Event,
    ):
        super().__init__()
        self.setAutoDelete(False)
        self.task_id = task_id
        self.fn = fn
        self.cancelled = cancelled
        self.signals = _RestTaskSignals()

    def run(self) -> None:
        if self.cancelled.is_set():
            return
        try:
            res = self.fn()
            if self.cancelled.is_set():
                return
            self.signals.succeeded.emit(self.task_id, res)
        except CommunityApiError as exc:
            if not self.cancelled.is_set():
                self.signals.failed.emit(self.task_id, exc.message, exc.status_code, exc.code)
        except Exception as exc:
            if not self.cancelled.is_set():
                self.signals.failed.emit(self.task_id, str(exc), 0, "WORKER_ERROR")


class CommunityController(QObject):
    """Controlador único de UI Qt <-> Backend REST + Socket.IO para Communities."""

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
    voice_state_changed = Signal(dict)
    realtime_status_changed = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        session_path: Optional[Path] = None,
        parent=None,
        heartbeat_interval_ms: int = 18000,
    ):
        super().__init__(parent)
        self.api_url = api_url.rstrip("/")
        self.session_path = session_path or default_session_path()
        self.api = CommunityApiClient(self.api_url)
        self.realtime = CommunityRealtimeBridge(self)
        self.session: Optional[CommunitySession] = None

        self.my_communities: List[Dict[str, Any]] = []
        self.public_communities: List[Dict[str, Any]] = []
        self.active_community: Optional[Dict[str, Any]] = None
        self.active_channels: List[Dict[str, Any]] = []
        self.active_channel: Optional[Dict[str, Any]] = None
        self.active_members: List[Dict[str, Any]] = []
        self.active_voice_channel: Optional[Dict[str, Any]] = None
        self.active_streams: List[Dict[str, Any]] = []
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
        self.last_health: Dict[str, Any] = {}

        self._heartbeat_interval_ms = max(0, int(heartbeat_interval_ms))
        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(self._heartbeat_interval_ms or 18000)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(4)
        self._next_task_id: int = 0
        self._pending_workers: Dict[int, Tuple[_RestWorker, Optional[str], int, threading.Event]] = {}
        self._op_generations: Dict[str, int] = {}

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

    # ------------------------------------------------------------------
    # Infraestructura Asíncrona para evitar bloqueo del hilo Qt GUI (P0-02)
    # ------------------------------------------------------------------
    def cancel_pending(self, category: Optional[str] = None) -> None:
        """Cancela operaciones REST en vuelo (todas o de una categoría específica)."""
        if category is None:
            for key in list(self._op_generations.keys()):
                self._op_generations[key] = self._op_generations.get(key, 0) + 1
            for tid, (_worker, _cat, _gen, ev) in list(self._pending_workers.items()):
                ev.set()
            self._pending_workers.clear()
        else:
            self._op_generations[category] = self._op_generations.get(category, 0) + 1
            for tid, (_worker, wcat, _gen, ev) in list(self._pending_workers.items()):
                if wcat == category:
                    ev.set()
                    self._pending_workers.pop(tid, None)
        self.loading_changed.emit(bool(self._pending_workers), "")

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
            for tid, (_w, wcat, _g, ev) in list(self._pending_workers.items()):
                if wcat == category:
                    ev.set()
                    self._pending_workers.pop(tid, None)

        cancel_ev = threading.Event()
        worker = _RestWorker(task_id=task_id, fn=fn, cancelled=cancel_ev)
        self._pending_workers[task_id] = (worker, category, gen, cancel_ev)
        self.loading_changed.emit(True, op_name)

        def _handle_ok(tid: int, result: Any) -> None:
            entry = self._pending_workers.pop(tid, None)
            self.loading_changed.emit(bool(self._pending_workers), "")
            if entry is None:
                return
            _w, cat, wgen, ev = entry
            if ev.is_set():
                return
            if cat and wgen != self._op_generations.get(cat, 0):
                return
            if on_success:
                on_success(result)

        def _handle_err(tid: int, message: str, status_code: int, code: str) -> None:
            entry = self._pending_workers.pop(tid, None)
            self.loading_changed.emit(bool(self._pending_workers), "")
            if entry is None:
                return
            _w, cat, wgen, ev = entry
            if ev.is_set():
                return
            if cat and wgen != self._op_generations.get(cat, 0):
                return
            err = CommunityApiError(message, status_code=status_code, code=code)
            if on_error:
                on_error(err)
            else:
                self.error_occurred.emit(err.message)

        worker.signals.succeeded.connect(_handle_ok)
        worker.signals.failed.connect(_handle_err)
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

    def logout(self) -> None:
        self._heartbeat_timer.stop()
        self.cancel_pending()
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
        self.active_voice_channel = None
        self.active_friends = []
        self.incoming_friend_requests = []
        self.active_activity_feed = []
        self.active_notifications = []
        self.unread_notifications_count = 0
        self._last_synced_msg_id = None
        self.clear_saved_session()
        self.voice_state_changed.emit({"connected": False, "channel": None, "media_ready": False})
        self.notifications_updated.emit([], 0)
        self.session_changed.emit(None)

    def shutdown(self) -> None:
        """Cierra timers, workers pendientes, actividad de juego y conexión realtime sin borrar la sesión persistida."""
        self._heartbeat_timer.stop()
        self.cancel_pending()
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
            text_channels = [c for c in channels if c.get("type") == "text"]
            first_msgs: List[Dict[str, Any]] = []
            first_ch_id = ""
            if text_channels:
                first_ch_id = str(text_channels[0]["id"])
                first_msgs = self.api.list_messages(first_ch_id, limit=50)
            return comm, channels, members, text_channels, first_ch_id, first_msgs

        def _apply(res):
            comm, channels, members, text_channels, first_ch_id, first_msgs = res
            self.active_community = comm
            self.active_channels = channels
            self.active_members = members
            self.realtime.join_community_room(community_id)
            payload = {"community": comm, "channels": channels, "members": members}
            self.community_opened.emit(payload)
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

    def report_game_activity(
        self,
        action: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.session:
            return None
        if action == "started":
            self._active_game_id = game_id
            self._active_game_title = title
        else:
            self._active_game_id = None
            self._active_game_title = None
        try:
            res = self.api.report_game_activity(
                action=action,
                game_id=game_id,
                title=title,
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
    # Voz y Streaming (P0.2: estado honesto sin peers ni LIVE simulado)
    # ------------------------------------------------------------------
    def join_voice_channel(self, channel_id: str) -> Dict[str, Any]:
        ch = next((c for c in self.active_channels if c["id"] == channel_id), None)
        if not ch:
            raise CommunityApiError("Canal de voz no encontrado.", status_code=404)

        cred = self.api.request_voice_token(channel_id)
        health = {}
        try:
            health = self.api.health()
        except Exception:
            health = self.last_health

        lk_reachable = health.get("livekit_media_plane") == "reachable"
        self.active_voice_channel = ch
        state = {
            "connected": True,
            "channel": ch,
            "token_issued": bool(cred.get("token")),
            "livekit_url": cred.get("url"),
            "media_ready": False,
            "livekit_media_plane": "reachable" if lk_reachable else "unreachable",
            "status_text": (
                f"Señalización activa en {ch['name']} — Audio RTC pendiente (Fase 4 SDK LiveKit)"
                if lk_reachable
                else f"Token emitido para {ch['name']} — Servidor LiveKit SFU no alcanzable (solo señalización)"
            ),
        }
        self.voice_state_changed.emit(state)
        return state

    def leave_voice_channel(self) -> None:
        if self.active_voice_channel:
            try:
                self.api.leave_voice(self.active_voice_channel["id"])
            except Exception:
                pass
        self.active_voice_channel = None
        self.voice_state_changed.emit({"connected": False, "channel": None, "media_ready": False})

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
        self.refresh_activity_and_notifications_async()

    def _on_rt_notification_received(self, payload: Dict[str, Any]) -> None:
        if self.session:
            self.refresh_activity_and_notifications_async()
