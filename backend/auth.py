"""
backend/auth.py - Sistema de autenticación centralizada y autorización de recursos para C.C.I. SYSTEM.

Resuelve la brecha crítica P0 identificada en la Auditoría:
1. Emisión y validación de tokens criptográficos firmados (HMAC-SHA256).
2. Decorador `@require_auth` para rutas REST con inyección obligatoria en `flask.g.current_user`.
3. Middleware y decorador `@require_socket_auth` para Socket.IO que deriva la identidad
   exclusivamente desde la sesión autenticada y sobreescribe cualquier ID del payload del cliente.
4. Verificaciones de autorización a nivel de recurso (pertenencia a grupo, propiedad de clip, sala).
"""
from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple
from flask import g, request, jsonify, session
from flask_socketio import disconnect
import cci_database
from backend.config import config

_REVOCATION_LOCK = threading.Lock()
_REVOKED_JTIS: Dict[str, float] = {}


def _ensure_revocation_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            exp REAL NOT NULL,
            revoked_at REAL NOT NULL
        );
        """
    )


def revoke_access_token(token_or_jti: Optional[str], exp: Optional[float] = None) -> bool:
    """Revoca un JWT activo por `jti` (o token crudo) en memoria y SQLite."""
    raw = str(token_or_jti or "").strip()
    if not raw:
        return False
    jti = raw
    exp_ts = float(exp) if exp is not None else (time.time() + 86400.0)
    if "." in raw:
        parts = raw.split(".")
        if len(parts) == 3:
            try:
                payload = json.loads(_base64url_decode(parts[1]).decode("utf-8"))
                jti = str(payload.get("jti") or hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24])
                if payload.get("exp"):
                    exp_ts = float(payload["exp"])
            except Exception:
                jti = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    if not jti:
        return False

    now = time.time()
    with _REVOCATION_LOCK:
        # Limpiar expirados en memoria para evitar crecimiento indefinido
        for k, v in list(_REVOKED_JTIS.items()):
            if v < now:
                _REVOKED_JTIS.pop(k, None)
        _REVOKED_JTIS[jti] = exp_ts

    try:
        with cci_database.get_db() as conn:
            _ensure_revocation_table(conn)
            conn.execute("DELETE FROM revoked_tokens WHERE exp < ?", (now,))
            conn.execute(
                "INSERT OR REPLACE INTO revoked_tokens (jti, exp, revoked_at) VALUES (?, ?, ?)",
                (jti, exp_ts, now),
            )
    except Exception:
        pass
    return True


def is_token_revoked(jti: Optional[str], raw_token: Optional[str] = None) -> bool:
    now = time.time()
    candidates = [c for c in (jti, hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:24] if raw_token else None) if c]
    if not candidates:
        return False

    with _REVOCATION_LOCK:
        for cand in candidates:
            exp_val = _REVOKED_JTIS.get(cand)
            if exp_val is not None and exp_val >= now:
                return True

    try:
        with cci_database.get_db() as conn:
            _ensure_revocation_table(conn)
            for cand in candidates:
                row = conn.execute(
                    "SELECT exp FROM revoked_tokens WHERE jti = ? AND exp >= ?",
                    (cand, now),
                ).fetchone()
                if row is not None:
                    with _REVOCATION_LOCK:
                        _REVOKED_JTIS[cand] = float(row["exp"])
                    return True
    except Exception:
        pass
    return False


# ==============================================================================
# 1. EMISIÓN Y VERIFICACIÓN DE TOKENS (HMAC-SHA256)
# ==============================================================================

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    try:
        padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
        return base64.urlsafe_b64decode(data + padding)
    except Exception:
        return b""


def create_access_token(user_id: str, username: str, expires_in_seconds: int = 86400, is_admin: bool = False) -> str:
    """Genera un token seguro firmado con HMAC-SHA256 con jti único."""
    now = time.time()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": str(user_id),
        "username": str(username),
        "is_admin": bool(is_admin),
        "jti": secrets.token_hex(12),
        "iss": "cci-system",
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    unsigned = f"{_base64url_encode(header_bytes)}.{_base64url_encode(payload_bytes)}"
    signature = hmac.new(
        config.secret_key.encode("utf-8"),
        unsigned.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return f"{unsigned}.{_base64url_encode(signature)}"


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Valida cabecera JWT, firma criptográfica, vigencia temporal y denylist de revocación."""
    if not token or not isinstance(token, str):
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    unsigned = f"{parts[0]}.{parts[1]}"
    signature_candidate = _base64url_decode(parts[2])

    expected_signature = hmac.new(
        config.secret_key.encode("utf-8"),
        unsigned.encode("utf-8"),
        hashlib.sha256
    ).digest()

    if not hmac.compare_digest(signature_candidate, expected_signature):
        return None

    try:
        header = json.loads(_base64url_decode(parts[0]).decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None
        payload_bytes = _base64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict) or not payload.get("user_id"):
            return None
        if float(payload.get("exp", 0)) < time.time():
            return None  # Expirado
        if is_token_revoked(payload.get("jti"), raw_token=token):
            return None  # Revocado explícitamente
        return payload
    except Exception:
        return None


# ==============================================================================
# 2. VALIDACIÓN DE CREDENCIALES CONTRA CUENTAS DE USUARIO
# ==============================================================================

def authenticate_user_credentials(
    identifier: str,
    password: str,
    db_path: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Autentica identidad y contraseña contra la tabla de cuentas SQLite.
    Acepta email o nombre de usuario. Retorna datos de cuenta o None.
    """
    if not identifier or not password:
        return None
    return cci_database.authenticate_account(identifier, password, db_path=db_path)


# ==============================================================================
# 3. REGISTRO DE CONEXIONES Y MAPEADO DE SOCKETS
# ==============================================================================

_socket_to_user: Dict[str, str] = {}
_user_to_sockets: Dict[str, set] = {}


def register_socket(sid: str, user_id: str) -> None:
    """Vincula de forma autoritativa un socket ID a un user_id autenticado."""
    if not sid or not user_id:
        return
    _socket_to_user[sid] = user_id
    if user_id not in _user_to_sockets:
        _user_to_sockets[user_id] = set()
    _user_to_sockets[user_id].add(sid)


def unregister_socket(sid: str) -> None:
    """Remueve la vinculación de socket al desconectarse."""
    user_id = _socket_to_user.pop(sid, None)
    if user_id and user_id in _user_to_sockets:
        _user_to_sockets[user_id].discard(sid)
        if not _user_to_sockets[user_id]:
            _user_to_sockets.pop(user_id, None)


def get_user_by_socket(sid: str) -> Optional[str]:
    """Obtiene el user_id autenticado vinculado a un socket_id."""
    return _socket_to_user.get(sid)


def get_sockets_by_user(user_id: str) -> set:
    """Obtiene el conjunto de socket_ids activos de un usuario."""
    return _user_to_sockets.get(user_id, set()).copy()


# ==============================================================================
# 4. DECORADOR REST (@require_auth)
# ==============================================================================

def require_auth(fn: Callable) -> Callable:
    """
    Protege rutas REST. Exige cabecera 'Authorization: Bearer <token>' o cookie 'cci_token'.
    Inyecta el usuario autenticado en `flask.g.current_user` y prohíbe suplantaciones.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "cci_token" in request.cookies:
            token = request.cookies.get("cci_token")

        payload = verify_access_token(token) if token else None
        if not payload:
            return jsonify({
                "success": False,
                "error": "Autenticación requerida. Proporcione un token Bearer válido.",
                "code": "UNAUTHORIZED",
            }), 401

        g.current_user = {
            "user_id": str(payload["user_id"]),
            "username": str(payload["username"]),
            "is_admin": bool(payload.get("is_admin", False)),
        }
        g.current_token_raw = token
        g.current_token_payload = payload
        return fn(*args, **kwargs)

    return wrapper


# ==============================================================================
# 5. AUTENTICACIÓN Y AUTORIZACIÓN SOCKET.IO (@require_socket_auth)
# ==============================================================================

def authenticate_socket_connection(auth_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Verifica el handshake de conexión Socket.IO extrayendo el token de auth={'token': ...}
    o query params. Retorna el payload del usuario o None si es inválido.
    Rechaza estrictamente si no hay credencial válida.
    """
    token = None
    if isinstance(auth_data, dict):
        token = auth_data.get("token")
    if not token and request:
        token = request.args.get("token")

    if token:
        payload = verify_access_token(token)
        if payload:
            user_id = str(payload["user_id"])
            username = str(payload["username"])
            session["user_id"] = user_id
            session["username"] = username
            session["authenticated"] = True
            if hasattr(request, "sid"):
                register_socket(request.sid, user_id)
            return payload

    return None


def require_socket_auth(fn: Callable) -> Callable:
    """
    Decorador para eventos Socket.IO.
    Garantiza que el socket esté autenticado, obtiene la identidad desde la sesión del servidor,
    y sobrescribe forzosamente cualquier campo de actor/identidad (user_id, sender_id, requester_id, owner_id, actor_id, host_id).
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        username = session.get("username", "Anon")

        if not user_id or not session.get("authenticated"):
            # Sin token válido autenticado: desconectar inmediatamente
            disconnect()
            return False

        # Si el primer argumento es un diccionario con el payload, forzar identidad del servidor
        if args and isinstance(args[0], dict):
            payload = args[0]
            # Neutralizar cualquier intento de suplantación de identidad en el payload
            payload["user_id"] = user_id
            payload["sender_id"] = user_id
            payload["requester_id"] = user_id
            payload["owner_id"] = user_id
            payload["actor_id"] = user_id
            payload["host_id"] = user_id
            payload["sender_name"] = username

        return fn(*args, **kwargs)

    return wrapper


# ==============================================================================
# 6. VERIFICACIONES DE AUTORIZACIÓN POR RECURSO
# ==============================================================================

def check_group_membership(user_id: str, group_id: str) -> bool:
    """Verifica si el usuario es miembro activo del grupo en la base de datos."""
    if not user_id or not group_id:
        return False
    grp = cci_database.get_group_detail(group_id)
    if not grp:
        return False
    return any(str(m.get("user_id")) == str(user_id) for m in grp.get("members", []))


def check_recording_ownership(user_id: str, recording_id: str) -> bool:
    """Verifica si el usuario es el propietario de la grabación."""
    rec = cci_database.get_gameplay_recording_by_id(recording_id)
    if not rec:
        return False
    return str(rec.get("owner_id")) == str(user_id)


def check_room_participation(user_id: str, room_id: str) -> bool:
    """Verifica si el usuario pertenece a la sala de juego activa."""
    room = cci_database.get_game_room(room_id)
    if not room:
        return False
    members = room.get("members", [])
    return any(str(m.get("user_id")) == str(user_id) for m in members)


def check_call_participation(user_id: str, session_id: str) -> bool:
    """
    Verifica si el usuario pertenece a la sesión de llamada de voz activa o a la sala correspondiente.
    Falla cerrada estrictamente: si la llamada/sala no existe o el usuario no está en ella, devuelve False.
    """
    if not user_id or not session_id:
        return False
    from backend.voice_service import VoiceService
    svc = VoiceService.get_instance()
    call = getattr(svc, "_active_calls", {}).get(session_id)
    if call and str(user_id) in call.participants:
        return True
    return check_room_participation(user_id, session_id)
