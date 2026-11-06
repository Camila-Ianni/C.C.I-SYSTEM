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
        return cls(
            env=os.getenv("CCI_ENV", "development"),
            host=os.getenv("CCI_HOST", "0.0.0.0"),
            port=int(os.getenv("CCI_PORT", "5050")),
            debug=os.getenv("CCI_DEBUG", "false").lower() in ("true", "1", "yes"),
            secret_key=os.getenv("CCI_SECRET_KEY", "cci-secret-key-change-in-production"),
            cors_origins=os.getenv("CCI_CORS_ORIGINS", "*"),
            database_path=Path(os.getenv("CCI_DATABASE_PATH", str(ROOT / ".cci-user-data" / "cci_system.sqlite3"))),
            stun_server=os.getenv("CCI_STUN_SERVER", "stun:stun.l.google.com:19302"),
            turn_server=os.getenv("CCI_TURN_SERVER", ""),
            turn_username=os.getenv("CCI_TURN_USERNAME", ""),
            turn_credential=os.getenv("CCI_TURN_CREDENTIAL", ""),
            recordings_path=Path(os.getenv("CCI_RECORDINGS_PATH", str(ROOT / "grabaciones"))),
            max_recordings_mb=int(os.getenv("CCI_MAX_RECORDINGS_STORAGE_MB", "2048")),
        )


config = AppConfig.from_env()
