"""
backend/config.py - Configuración de entorno centralizada para C.C.I. SYSTEM.
En producción (CCI_ENV=production), aplica validación fail-fast estricta y rechaza
cualquier valor ausente, corto, débil o de plantilla (REPLACE_WITH_*, *_REPLACE_ME, devkey, etc.)
sin generar silenciosamente credenciales de reemplazo.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

INSECURE_SECRET_PLACEHOLDERS = {
    "",
    "devkey",
    "secret",
    "password",
    "changeme",
    "secretkey1234567890abcdef",
    "cci-secret-key-change-in-production",
    "cci-dev-secret-key-0123456789abcdef0123456789abcdef",
    "cci_jwt_super_secret_signing_key_production",
    "cci_turn_shared_secret_production_2026",
    "cci_turn_static_secret_2026",
    "cci_prod_secret_2026",
    "cci_secret_password",
    "cci_redis_password",
    "cci_minio_secret_key",
    "minioadmin_secret_2026",
    "replace_with_openssl_rand_hex_32",
    "replace_with_livekit_api_key",
    "lk_prod_key_replace_me",
    "replace_with_livekit_api_secret_32_chars",
    "replace_with_coturn_shared_secret_32_chars",
    "replace_with_postgres_password",
    "replace_with_redis_password",
    "replace_with_minio_secret_key",
}

_PLACEHOLDER_PATTERNS = re.compile(
    r"(^replace_with_|_replace_me$|replace_with|replace_me|changeme|placeholder|example_secret|your_.*_here)",
    re.IGNORECASE,
)


def is_insecure_or_placeholder_secret(value: Optional[str], min_len: int = 16) -> bool:
    """
    Determina si un secreto o clave API es vacío, demasiado corto, repetitivo
    o coincide con cualquier marcador de plantilla (.env.example / dev defaults).
    """
    if value is None:
        return True
    cleaned = str(value).strip()
    if not cleaned or len(cleaned) < min_len:
        return True
    lower = cleaned.lower()
    if lower in INSECURE_SECRET_PLACEHOLDERS:
        return True
    if _PLACEHOLDER_PATTERNS.search(cleaned):
        return True
    # Rechazar cadenas triviales con un único carácter repetido (ej. 'aaaa...')
    if len(set(cleaned)) < 4:
        return True
    return False


@dataclass(frozen=True)
class AppConfig:
    env: str
    host: str
    port: int
    debug: bool
    secret_key: str
    cors_origins: str
    database_path: Path
    communities_database_path: Path
    sounds_storage_path: Path
    stun_server: str
    turn_server: str
    turn_username: str
    turn_credential: str
    turn_secret: str
    livekit_ws_url: str
    livekit_api_key: str
    livekit_api_secret: str
    recordings_path: Path
    max_recordings_mb: int

    @classmethod
    def validate_production_secrets(cls, env: Optional[str] = None) -> None:
        """
        Valida de forma estricta (fail-fast) que en producción estén configurados
        CCI_SECRET_KEY, LIVEKIT_API_KEY, LIVEKIT_API_SECRET y TURN_SECRET con valores reales.
        Jamás expone el valor del secreto en el mensaje de excepción.
        """
        active_env = (env or os.getenv("CCI_ENV", "development")).strip().lower()
        if active_env != "production":
            return

        jwt_secret = os.getenv("CCI_SECRET_KEY", "").strip()
        lk_key = os.getenv("LIVEKIT_API_KEY", "").strip()
        lk_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
        turn_secret = (os.getenv("TURN_SECRET") or os.getenv("CCI_TURN_CREDENTIAL") or "").strip()
        require_turn = os.getenv("CCI_REQUIRE_TURN", "true").strip().lower() not in ("false", "0", "no")

        if is_insecure_or_placeholder_secret(jwt_secret, min_len=32):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: CCI_SECRET_KEY ausente, menor a 32 caracteres o con valor de plantilla en CCI_ENV=production."
            )
        if is_insecure_or_placeholder_secret(lk_key, min_len=8):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: LIVEKIT_API_KEY ausente, corto o con valor de plantilla ('devkey' / 'REPLACE_WITH_*') en CCI_ENV=production."
            )
        if is_insecure_or_placeholder_secret(lk_secret, min_len=32):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: LIVEKIT_API_SECRET ausente, menor a 32 caracteres o con valor de plantilla en CCI_ENV=production."
            )
        if require_turn and is_insecure_or_placeholder_secret(turn_secret, min_len=32):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: TURN_SECRET ausente, menor a 32 caracteres o con valor de plantilla en CCI_ENV=production."
            )

    @classmethod
    def from_env(cls, strict_production: bool = True) -> AppConfig:
        env = os.getenv("CCI_ENV", "development").strip()
        is_prod = env.lower() == "production"

        if is_prod and strict_production:
            cls.validate_production_secrets(env)

        secret = os.getenv("CCI_SECRET_KEY", "").strip()
        data_dir = ROOT / ".cci-user-data"
        data_dir.mkdir(parents=True, exist_ok=True)

        if not is_prod and is_insecure_or_placeholder_secret(secret, min_len=16):
            secret = "cci-dev-secret-key-0123456789abcdef0123456789abcdef"

        cors = os.getenv("CCI_CORS_ORIGINS", "").strip()
        if not cors:
            if is_prod:
                cors = "https://ccisystem.org,https://api.ccisystem.org"
            else:
                cors = "*"

        db_path = Path(os.getenv("CCI_DATABASE_PATH", str(data_dir / "cci_system.sqlite3")))
        comm_db_env = os.getenv("CCI_COMMUNITIES_DB_PATH", "").strip()
        if comm_db_env:
            comm_db_path = Path(comm_db_env)
        elif "CCI_DATABASE_PATH" in os.environ:
            comm_db_path = db_path
        else:
            comm_db_path = data_dir / "cci_communities.sqlite3"

        sounds_dir = Path(os.getenv("CCI_SOUNDS_STORAGE_PATH", str(data_dir / "sounds")))
        turn_sec = (os.getenv("TURN_SECRET") or os.getenv("CCI_TURN_CREDENTIAL") or "").strip()

        return cls(
            env=env,
            host=os.getenv("CCI_HOST", "0.0.0.0"),
            port=int(os.getenv("CCI_PORT", "5050")),
            debug=os.getenv("CCI_DEBUG", "false").lower() in ("true", "1", "yes"),
            secret_key=secret,
            cors_origins=cors,
            database_path=db_path,
            communities_database_path=comm_db_path,
            sounds_storage_path=sounds_dir,
            stun_server=os.getenv("CCI_STUN_SERVER", "stun:turn.ccisystem.org:3478"),
            turn_server=os.getenv("CCI_TURN_SERVER", "turn:turn.ccisystem.org:3478"),
            turn_username=os.getenv("CCI_TURN_USERNAME", ""),
            turn_credential=turn_sec,
            turn_secret=turn_sec,
            livekit_ws_url=os.getenv("LIVEKIT_WS_URL", "ws://127.0.0.1:7880" if not is_prod else "wss://rtc.ccisystem.org"),
            livekit_api_key=os.getenv("LIVEKIT_API_KEY", "devkey" if not is_prod else ""),
            livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", "secretkey1234567890abcdef" if not is_prod else ""),
            recordings_path=Path(os.getenv("CCI_RECORDINGS_PATH", str(ROOT / "grabaciones"))),
            max_recordings_mb=int(os.getenv("CCI_MAX_RECORDINGS_STORAGE_MB", "2048")),
        )


config = AppConfig.from_env()
