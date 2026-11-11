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
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import socketio
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_API_URL = os.getenv("CCI_API_URL", "http://127.0.0.1:5050").rstrip("/")

_started_local_ports: set[int] = set()
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


def ensure_local_backend_running(api_url: str = DEFAULT_API_URL, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Comprueba si el backend `/api/v1/health` responde.
    Si apunta a loopback y CCI_AUTO_START_BACKEND != '0', inicia `backend.server` en hilo daemon local.
    """
    base = api_url.rstrip("/")
    try:
        resp = requests.get(f"{base}/api/v1/health", timeout=1.2)
        if resp.status_code == 200:
            return True, "connected"
    except requests.RequestException:
        pass

    parsed = urlparse(base)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    is_loopback = host in ("127.0.0.1", "localhost")
    auto_start = os.getenv("CCI_AUTO_START_BACKEND", "1").strip().lower() not in ("0", "false", "no")

    if not (is_loopback and auto_start):
        return False, f"No se pudo conectar con {base}"

    with _local_server_lock:
        if port not in _started_local_ports:
            _started_local_ports.add(port)

            def _serve():
                try:
                    import cci_database
                    from backend.server import app as srv_app, socketio as srv_sio
                    cci_database.init_db()
                    srv_sio.run(
                        srv_app,
                        host="127.0.0.1",
                        port=port,
                        debug=False,
                        use_reloader=False,
                        allow_unsafe_werkzeug=True,
                        log_output=False,
                    )
                except Exception as exc:
                    logger.warning("Local backend thread exited: %s", exc)

            t = threading.Thread(target=_serve, daemon=True, name=f"CCI-LocalBackend-{port}")
            t.start()

    deadline = time.monotonic() + timeout
    last_err = f"Tiempo agotado conectando a {base}"
    while time.monotonic() < deadline:
        try:
            resp = requests.get(f"{base}/api/v1/health", timeout=0.8)
            if resp.status_code == 200:
                return True, "connected"
            last_err = f"Backend respondió HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_err = str(exc)
        time.sleep(0.12)
    return False, last_err


class CommunityApiClient:
    """Cliente HTTP síncrono (requests.Session) con Bearer JWT y manejo honesto de errores."""

    def __init__(self, api_url: str = DEFAULT_API_URL, timeout: float = 6.0):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._http = requests.Session()
        self.token: Optional[str] = None

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

    def list_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if before_id:
            params["before_id"] = before_id
        data = self._request("GET", f"/api/v1/channels/{channel_id}/messages", params=params)
        return list(data.get("messages") or [])

    def send_message(self, channel_id: str, content: str, reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"content": content}
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        data = self._request("POST", f"/api/v1/channels/{channel_id}/messages", json_body=payload)
        return dict(data.get("message") or {})

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

    def set_presence(self, status: str = "online", custom_status: Optional[str] = None) -> Dict[str, Any]:
        data = self._request(
            "POST",
            "/api/v1/users/presence",
            json_body={"status": status, "custom_status": custom_status},
        )
        return dict(data.get("presence") or {})

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
    channel_created = Signal(dict)
    member_joined = Signal(dict)
    member_left = Signal(dict)
    presence_updated = Signal(dict)

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


class CommunityController(QObject):
    """Controlador único de UI Qt <-> Backend REST + Socket.IO para Communities."""

    session_changed = Signal(object)       # CommunitySession | None
    backend_status_changed = Signal(bool, str)
    communities_updated = Signal(list, list)  # my_communities, public_communities
    community_opened = Signal(dict)        # community payload + channels + members
    channel_messages_loaded = Signal(str, list)  # channel_id, messages
    message_received = Signal(dict)
    message_updated = Signal(dict)
    message_deleted = Signal(dict)
    members_updated = Signal(list)
    voice_state_changed = Signal(dict)
    realtime_status_changed = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(self, api_url: str = DEFAULT_API_URL, session_path: Optional[Path] = None, parent=None):
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
        self.last_health: Dict[str, Any] = {}

        self.realtime.connected.connect(self._on_rt_connected)
        self.realtime.disconnected.connect(self._on_rt_disconnected)
        self.realtime.community_error.connect(self.error_occurred.emit)
        self.realtime.message_created.connect(self._on_rt_message_created)
        self.realtime.message_updated.connect(self._on_rt_message_updated)
        self.realtime.message_deleted.connect(self._on_rt_message_deleted)
        self.realtime.channel_created.connect(self._on_rt_channel_created)
        self.realtime.member_joined.connect(self._on_rt_member_change)
        self.realtime.member_left.connect(self._on_rt_member_change)
        self.realtime.presence_updated.connect(self._on_rt_presence_updated)

    # ------------------------------------------------------------------
    # Sesión & Salud
    # ------------------------------------------------------------------
    def check_backend(self, auto_start: bool = True) -> Tuple[bool, str]:
        if auto_start:
            ok, msg = ensure_local_backend_running(self.api_url)
        else:
            try:
                self.api.health()
                ok, msg = True, "connected"
            except CommunityApiError as exc:
                ok, msg = False, exc.message

        if ok:
            try:
                self.last_health = self.api.health()
            except Exception:
                self.last_health = {}
        else:
            self.last_health = {}

        self.backend_status_changed.emit(ok, msg)
        return ok, msg

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

    def logout(self) -> None:
        if self.active_voice_channel and self.session:
            try:
                self.api.leave_voice(self.active_voice_channel["id"])
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
        self.clear_saved_session()
        self.voice_state_changed.emit({"connected": False, "channel": None, "media_ready": False})
        self.session_changed.emit(None)

    def _activate_session(self, sess: CommunitySession, persist: bool) -> None:
        self.session = sess
        self.api.set_token(sess.token)
        if persist:
            self._save_session(sess)
        try:
            self.api.set_presence("online")
        except Exception:
            pass
        self.realtime.connect_with_token(self.api_url, sess.token)
        self.session_changed.emit(sess)

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

    def select_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        ch = next((c for c in self.active_channels if c["id"] == channel_id), None)
        if not ch:
            raise CommunityApiError("Canal no encontrado.", status_code=404)
        self.active_channel = ch
        self.realtime.join_channel_room(channel_id)
        msgs = self.api.list_messages(channel_id, limit=50)
        self.channel_messages_loaded.emit(channel_id, msgs)
        return msgs

    def send_message(self, content: str, reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.active_channel:
            raise CommunityApiError("Seleccioná un canal de texto primero.", status_code=400)
        return self.api.send_message(self.active_channel["id"], content=content, reply_to_id=reply_to_id)

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

    def _on_rt_disconnected(self, reason: str) -> None:
        self.realtime_status_changed.emit(False, reason)

    def _on_rt_message_created(self, msg: Dict[str, Any]) -> None:
        if self.active_channel and msg.get("channel_id") == self.active_channel["id"]:
            self.message_received.emit(msg)

    def _on_rt_message_updated(self, msg: Dict[str, Any]) -> None:
        if self.active_channel and msg.get("channel_id") == self.active_channel["id"]:
            self.message_updated.emit(msg)

    def _on_rt_message_deleted(self, payload: Dict[str, Any]) -> None:
        if self.active_channel and payload.get("channel_id") == self.active_channel["id"]:
            self.message_deleted.emit(payload)

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

    def _on_rt_member_change(self, payload: Dict[str, Any]) -> None:
        if self.active_community and payload.get("community_id") == self.active_community["id"]:
            try:
                self.refresh_members()
            except Exception:
                pass

    def _on_rt_presence_updated(self, presence: Dict[str, Any]) -> None:
        uid = str(presence.get("user_id") or "")
        if not uid or not self.active_members:
            return
        changed = False
        for m in self.active_members:
            if str(m.get("user_id")) == uid:
                m["presence_status"] = presence.get("status", "offline")
                m["custom_status"] = presence.get("custom_status")
                changed = True
        if changed:
            self.members_updated.emit(list(self.active_members))
