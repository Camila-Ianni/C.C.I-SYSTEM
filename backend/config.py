"""
backend/config.py - Configuración de entorno centralizada para C.C.I. SYSTEM.
Lee variables de entorno con fallbacks seguros para desarrollo y producción.
"""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    env: str
    host: str
    port: int
    debug: bool
    secret_key: str
    cors_origins: str
    database_path: Path
    stun_server: str
    turn_server: str
    turn_username: str
    turn_credential: str
    recordings_path: Path
    max_recordings_mb: int

    @classmethod
    def from_env(cls) -> AppConfig:
        env = os.getenv("CCI_ENV", "development")
        secret = os.getenv("CCI_SECRET_KEY", "").strip()
        data_dir = ROOT / ".cci-user-data"
        data_dir.mkdir(parents=True, exist_ok=True)
        key_file = data_dir / ".secret_key"

        if not secret or secret == "cci-secret-key-change-in-production":
            if env == "production":
                # En producción se requiere persistencia entre workers y reinicios
                if key_file.exists():
                    secret = key_file.read_text(encoding="utf-8").strip()
                else:
                    import secrets
                    secret = secrets.token_hex(32)
                    key_file.write_text(secret, encoding="utf-8")
                    try:
                        key_file.chmod(0o600)
                    except Exception:
                        pass
            else:
                secret = "cci-dev-secret-key-0123456789abcdef0123456789abcdef"

        cors = os.getenv("CCI_CORS_ORIGINS", "")
        if not cors:
            if env == "production":
                cors = "https://c-c-i-system.onrender.com,https://ccisystem.org"
            else:
                cors = "*"

        return cls(
            env=env,
            host=os.getenv("CCI_HOST", "0.0.0.0"),
            port=int(os.getenv("CCI_PORT", "5050")),
            debug=os.getenv("CCI_DEBUG", "false").lower() in ("true", "1", "yes"),
            secret_key=secret,
            cors_origins=cors,
            database_path=Path(os.getenv("CCI_DATABASE_PATH", str(ROOT / ".cci-user-data" / "cci_system.sqlite3"))),
            stun_server=os.getenv("CCI_STUN_SERVER", "stun:stun.l.google.com:19302"),
            turn_server=os.getenv("CCI_TURN_SERVER", ""),
            turn_username=os.getenv("CCI_TURN_USERNAME", ""),
            turn_credential=os.getenv("CCI_TURN_CREDENTIAL", ""),
            recordings_path=Path(os.getenv("CCI_RECORDINGS_PATH", str(ROOT / "grabaciones"))),
            max_recordings_mb=int(os.getenv("CCI_MAX_RECORDINGS_STORAGE_MB", "2048")),
        )


config = AppConfig.from_env()
