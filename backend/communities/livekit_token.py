"""
backend/communities/livekit_token.py - Emisor y validador de tokens JWT para LiveKit SFU.

Genera tokens conformes a la especificación oficial de LiveKit Server (RFC 7519 / HMAC-SHA256)
con concesiones granulares de sala (roomJoin, canPublish, canSubscribe, canPublishData)
y vigencia estricta <= 300 segundos (< 5 minutos, por defecto 240s).
En producción (CCI_ENV=production), aborta si no existen secretos reales configurados.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from backend.config import INSECURE_SECRET_PLACEHOLDERS


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data + padding)


class LiveKitTokenGenerator:
    """Generador autoritativo de credenciales de acceso efímeras para salas LiveKit Server."""

    DEFAULT_TOKEN_TTL_SECONDS = 240  # 4 minutos (< 5 min requeridos en Fase 0)
    MAX_TOKEN_TTL_SECONDS = 300      # Tope estricto de 5 minutos

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        livekit_url: Optional[str] = None,
    ):
        env = os.environ.get("CCI_ENV", "development").strip().lower()
        raw_key = api_key if api_key is not None else os.environ.get("LIVEKIT_API_KEY", "").strip()
        raw_secret = api_secret if api_secret is not None else os.environ.get("LIVEKIT_API_SECRET", "").strip()

        if env == "production":
            if not raw_key or raw_key in INSECURE_SECRET_PLACEHOLDERS:
                raise RuntimeError(
                    "CRITICAL SECURITY ERROR: LIVEKIT_API_KEY ausente o inseguro ('devkey') en CCI_ENV=production."
                )
            if not raw_secret or raw_secret in INSECURE_SECRET_PLACEHOLDERS or len(raw_secret) < 16:
                raise RuntimeError(
                    "CRITICAL SECURITY ERROR: LIVEKIT_API_SECRET ausente, corto o por defecto en CCI_ENV=production."
                )
            self.api_key = raw_key
            self.api_secret = raw_secret
        else:
            self.api_key = raw_key or "devkey"
            self.api_secret = raw_secret or "secretkey1234567890abcdef"

        self.livekit_url = (
            livekit_url
            or os.environ.get("LIVEKIT_WS_URL")
            or os.environ.get("LIVEKIT_URL")
            or "ws://127.0.0.1:7880"
        )

    def create_access_token(
        self,
        identity: str,
        name: str,
        room_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
        can_publish_data: bool = True,
        valid_for_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    ) -> Dict[str, Any]:
        """Genera un token JWT firmado para conexión WebRTC a una sala LiveKit (TTL <= 300s)."""
        if not identity or not str(identity).strip():
            raise ValueError("identity es obligatorio para emitir un token LiveKit")
        if not room_name or not str(room_name).strip():
            raise ValueError("room_name es obligatorio para emitir un token LiveKit")

        ttl = min(int(valid_for_seconds), self.MAX_TOKEN_TTL_SECONDS)
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.api_key,
            "sub": str(identity),
            "name": str(name),
            "nbf": now,
            "iat": now,
            "exp": now + ttl,
            "jti": f"{identity}:{room_name}:{now}",
            "video": {
                "room": str(room_name),
                "roomJoin": True,
                "canPublish": bool(can_publish),
                "canSubscribe": bool(can_subscribe),
                "canPublishData": bool(can_publish_data),
            },
        }

        header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        unsigned = f"{_base64url_encode(header_bytes)}.{_base64url_encode(payload_bytes)}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            unsigned.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        token_str = f"{unsigned}.{_base64url_encode(signature)}"
        return {
            "token": token_str,
            "url": self.livekit_url,
            "room_name": str(room_name),
            "identity": str(identity),
            "can_publish": bool(can_publish),
            "can_subscribe": bool(can_subscribe),
            "ttl_seconds": ttl,
            "expires_at": now + ttl,
        }

    def verify_access_token(
        self,
        token: str,
        expected_room: Optional[str] = None,
        expected_identity: Optional[str] = None,
        require_publish: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Verifica firma HMAC-SHA256, emisor (iss), sujeto (sub), sala, permisos y expiración."""
        if not token or not isinstance(token, str):
            return None

        parts = token.split(".")
        if len(parts) != 3:
            return None

        try:
            header = json.loads(_base64url_decode(parts[0]).decode("utf-8"))
            if header.get("alg") != "HS256" or header.get("typ") != "JWT":
                return None
            signature_candidate = _base64url_decode(parts[2])
        except Exception:
            return None

        unsigned = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            self.api_secret.encode("utf-8"),
            unsigned.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(signature_candidate, expected_sig):
            return None

        try:
            payload_bytes = _base64url_decode(parts[1])
            payload = json.loads(payload_bytes.decode("utf-8"))
            now = time.time()

            # 1. Validar emisor (iss) y sujeto (sub)
            if payload.get("iss") != self.api_key:
                return None
            sub = payload.get("sub")
            if not sub or not isinstance(sub, str):
                return None
            if expected_identity is not None and sub != str(expected_identity):
                return None

            # 2. Validar vigencia temporal (exp, iat, nbf) y tope de TTL <= 300s
            exp = payload.get("exp")
            iat = payload.get("iat", 0)
            nbf = payload.get("nbf", 0)
            if not isinstance(exp, (int, float)) or exp < now:
                return None
            if isinstance(nbf, (int, float)) and nbf > now + 5:
                return None
            if isinstance(iat, (int, float)) and iat > 0 and (exp - iat) > self.MAX_TOKEN_TTL_SECONDS:
                return None

            # 3. Validar concesiones de sala (video grant)
            video = payload.get("video")
            if not isinstance(video, dict) or video.get("roomJoin") is not True:
                return None
            room = video.get("room")
            if not room or not isinstance(room, str):
                return None
            if expected_room is not None and room != str(expected_room):
                return None
            if require_publish and video.get("canPublish") is not True:
                return None

            return payload
        except Exception:
            return None

    # Alias de conveniencia
    verify_token = verify_access_token
