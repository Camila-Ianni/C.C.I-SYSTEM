"""
backend/communities/livekit_token.py - Emisor y validador de tokens JWT para LiveKit SFU.

Genera tokens conformes a la especificación oficial de LiveKit Server (RFC 7519 / HMAC-SHA256)
con concesiones granulares de sala (roomJoin, canPublish, canSubscribe, canPublishData).
Ningún secreto ni clave privada de LiveKit se expone al cliente.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data + padding)


class LiveKitTokenGenerator:
    """Generador autoritativo de credenciales de acceso para salas LiveKit Server."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, livekit_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LIVEKIT_API_KEY", "devkey")
        self.api_secret = api_secret or os.environ.get("LIVEKIT_API_SECRET", "secretkey1234567890abcdef")
        self.livekit_url = livekit_url or os.environ.get("LIVEKIT_URL", "ws://127.0.0.1:7880")

    def create_access_token(
        self,
        identity: str,
        name: str,
        room_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
        can_publish_data: bool = True,
        valid_for_seconds: int = 600,
    ) -> Dict[str, Any]:
        """Genera un token JWT firmado para conexión WebRTC a una sala LiveKit."""
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.api_key,
            "sub": str(identity),
            "name": str(name),
            "video": {
                "room": str(room_name),
                "roomJoin": True,
                "canPublish": bool(can_publish),
                "canSubscribe": bool(can_subscribe),
                "canPublishData": bool(can_publish_data),
            },
            "iat": now,
            "exp": now + valid_for_seconds,
        }

        header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        unsigned = f"{_base64url_encode(header_bytes)}.{_base64url_encode(payload_bytes)}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            unsigned.encode("utf-8"),
            hashlib.sha256
        ).digest()

        token_str = f"{unsigned}.{_base64url_encode(signature)}"
        return {
            "token": token_str,
            "url": self.livekit_url,
            "room_name": str(room_name),
            "identity": str(identity),
            "can_publish": can_publish,
            "expires_at": now + valid_for_seconds,
        }

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifica la firma HMAC-SHA256 y vigencia de un token LiveKit."""
        if not token or not isinstance(token, str):
            return None

        parts = token.split(".")
        if len(parts) != 3:
            return None

        unsigned = f"{parts[0]}.{parts[1]}"
        signature_candidate = _base64url_decode(parts[2])

        expected_sig = hmac.new(
            self.api_secret.encode("utf-8"),
            unsigned.encode("utf-8"),
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(signature_candidate, expected_sig):
            return None

        try:
            payload_bytes = _base64url_decode(parts[1])
            payload = json.loads(payload_bytes.decode("utf-8"))
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None

    # Alias de conveniencia
    verify_token = verify_access_token
