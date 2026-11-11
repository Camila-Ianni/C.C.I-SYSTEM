"""backend/security_hardening.py - Controles de hardening para producción en C.C.I. SYSTEM.

Incluye:
1. Limitador de tasa (Sliding Window Rate Limiter) thread-safe sin dependencias externas.
2. Middleware de cabeceras HTTP de seguridad (HSTS, nosniff, X-Frame-Options,
   Referrer-Policy, Permissions-Policy y `Cache-Control: no-store` para auth/OAuth).
3. Validación estricta de Redirect URIs para OAuth 2.0 (anti Open Redirect).
"""
from __future__ import annotations

from collections import deque
import os
import threading
import time
from typing import Deque, Dict, Optional, Sequence, Tuple
from urllib.parse import urlparse


class SlidingWindowRateLimiter:
    """Rate limiter en memoria por clave (IP / usuario / endpoint) con ventana deslizante."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: Dict[str, Deque[float]] = {}

    def check(self, key: str, max_requests: int, window_seconds: float = 60.0) -> Tuple[bool, int]:
        """Registra un intento si está dentro del cupo. Retorna `(permitido, retry_after_sec)`."""
        if max_requests <= 0 or window_seconds <= 0:
            return True, 0
        now = time.monotonic()
        cutoff = now - float(window_seconds)
        with self._lock:
            dq = self._buckets.get(key)
            if dq is None:
                dq = deque()
                self._buckets[key] = dq
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= int(max_requests):
                oldest = dq[0]
                retry_after = max(1, int(window_seconds - (now - oldest)) + 1)
                return False, retry_after
            dq.append(now)
            return True, 0

    def reset(self, prefix: Optional[str] = None) -> None:
        with self._lock:
            if not prefix:
                self._buckets.clear()
                return
            for k in list(self._buckets.keys()):
                if k.startswith(prefix):
                    self._buckets.pop(k, None)


auth_rate_limiter = SlidingWindowRateLimiter()


def is_rate_limiting_enabled() -> bool:
    return os.getenv("CCI_RATE_LIMIT_ENABLED", "true").strip().lower() not in ("0", "false", "no")


def get_rate_limit(env_var: str, default_value: int) -> int:
    raw = os.getenv(env_var, "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return int(default_value)


def get_client_ip(req) -> str:
    forwarded = str(req.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    return str(getattr(req, "remote_addr", None) or "unknown")


def apply_security_headers(response, path: str = "", is_https: bool = False, is_production: bool = False):
    """Inyecta cabeceras estándar de hardening HTTP sin sobrescribir cabeceras ya definidas."""
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("X-XSS-Protection", "0")
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=(), payment=()")

    if is_https or is_production:
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    clean_path = str(path or "").lower()
    if clean_path.startswith("/api/v1/auth") or clean_path.startswith("/api/v1/integrations"):
        headers["Cache-Control"] = "no-store, max-age=0"
        headers["Pragma"] = "no-cache"
    return response


def validate_oauth_redirect_uri(
    redirect_uri: str,
    allowed_hosts: Sequence[str] = ("127.0.0.1", "localhost"),
) -> str:
    """Valida que `redirect_uri` sea un loopback local o HTTPS autorizado (anti Open Redirect)."""
    uri = str(redirect_uri or "").strip()
    if not uri or len(uri) > 512:
        raise ValueError("redirect_uri inválido")
    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()

    if scheme == "http":
        if host not in tuple(h.lower() for h in allowed_hosts):
            raise ValueError("redirect_uri HTTP solo permitido en loopback local")
        if parsed.port is None or parsed.port <= 0:
            raise ValueError("redirect_uri loopback requiere puerto explícito")
        return uri

    if scheme == "https":
        if not host:
            raise ValueError("redirect_uri HTTPS requiere host")
        extra = [
            h.strip().lower()
            for h in os.getenv("CCI_OAUTH_ALLOWED_REDIRECT_HOSTS", "ccisystem.org,api.ccisystem.org").split(",")
            if h.strip()
        ]
        if host not in set(extra) and host not in set(allowed_hosts):
            raise ValueError(f"Host redirect_uri no autorizado: {host}")
        return uri

    raise ValueError("Esquema de redirect_uri no soportado")
