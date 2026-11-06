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
import time
from typing import Any, Callable, Dict, Optional, Tuple
from flask import g, request, jsonify, session
from flask_socketio import disconnect
import cci_database
from backend.config import config


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


def create_access_token(user_id: str, username: str, expires_in_seconds: int = 86400) -> str:
    """Genera un token seguro firmado con HMAC-SHA256."""
    now = time.time()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": str(user_id),
        "username": str(username),
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
    """Valida la firma criptográfica y vigencia temporal del token."""
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
        payload_bytes = _base64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None  # Expirado
        return payload
    except Exception:
        return None


# ==============================================================================
# 2. DECORADOR REST (@require_auth)
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
            "user_id": payload["user_id"],
            "username": payload["username"],
        }
        return fn(*args, **kwargs)

    return wrapper


# ==============================================================================
# 3. AUTENTICACIÓN Y AUTORIZACIÓN SOCKET.IO (@require_socket_auth)
# ==============================================================================

def authenticate_socket_connection(auth_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Verifica el handshake de conexión Socket.IO extrayendo el token de auth={'token': ...}
    o query params. Retorna el payload del usuario o None si es inválido.
    """
    token = None
    if isinstance(auth_data, dict):
        token = auth_data.get("token")
    if not token and request:
        token = request.args.get("token")

    if token:
        payload = verify_access_token(token)
        if payload:
            session["user_id"] = payload["user_id"]
            session["username"] = payload["username"]
            session["authenticated"] = True
            return payload

    return None


def require_socket_auth(fn: Callable) -> Callable:
    """
    Decorador para eventos Socket.IO.
    Garantiza que el socket esté autenticado, obtiene la identidad desde la sesión del servidor,
    y sobrescribe forzosamente cualquier campo de identidad en los datos recibidos (sender_id, user_id).
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        username = session.get("username", "Anon")

        if not user_id:
            # Fallback seguro para entorno de desarrollo local si no se activó token estricto
            client_ip = getattr(request, "remote_addr", "127.0.0.1")
            if config.env == "development" and client_ip in ("127.0.0.1", "localhost", "::1"):
                # Permitir desarrollo local asignando identidad ligada al socket_id
                user_id = f"dev_guest_{request.sid[:8]}" if hasattr(request, "sid") else "dev_guest"
                session["user_id"] = user_id
                session["username"] = username
            else:
                disconnect()
                return False

        # Si el primer argumento es un diccionario con el payload, forzar identidad del servidor
        if args and isinstance(args[0], dict):
            payload = args[0]
            # Neutralizar cualquier intento de suplantación de identidad en el payload
            payload["user_id"] = user_id
            payload["sender_id"] = user_id
            payload["sender_name"] = username

        return fn(*args, **kwargs)

    return wrapper


# ==============================================================================
# 4. VERIFICACIONES DE AUTORIZACIÓN POR RECURSO
# ==============================================================================

def check_group_membership(user_id: str, group_id: str) -> bool:
    """Verifica si el usuario es miembro activo del grupo en la base de datos."""
    if not user_id or not group_id:
        return False
    grp = cci_database.get_group_detail(group_id)
    if not grp:
        return False
    return any(m.get("user_id") == user_id for m in grp.get("members", []))


def check_recording_ownership(user_id: str, recording_id: str) -> bool:
    """Verifica si el usuario es el propietario de la grabación."""
    rec = cci_database.get_gameplay_recording_by_id(recording_id)
    if not rec:
        return False
    return rec.get("owner_id") == user_id


def check_room_participation(user_id: str, room_id: str) -> bool:
    """Verifica si el usuario pertenece a la sala de juego activa."""
    room = cci_database.get_game_room_detail(room_id)
    if not room:
        return False
    members = room.get("members", [])
    return any(m.get("user_id") == user_id for m in members)
