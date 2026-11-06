"""
backend/config.py - Configuración de entorno centralizada para C.C.I. SYSTEM.
Lee variables de entorno con fallbacks seguros para desarrollo y producción.
"""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parent.parent

INSECURE_SECRET_PLACEHOLDERS = {
    "",
    "devkey",
    "secret",
    "changeme",
    "secretkey1234567890abcdef",
    "cci-secret-key-change-in-production",
    "cci-dev-secret-key-0123456789abcdef0123456789abcdef",
    "cci_jwt_super_secret_signing_key_production",
    "cci_turn_shared_secret_production_2026",
    "cci_prod_secret_2026",
    "minioadmin_secret_2026",
}


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
    livekit_ws_url: str
    livekit_api_key: str
    livekit_api_secret: str
    recordings_path: Path
    max_recordings_mb: int

    @classmethod
    def validate_production_secrets(cls, env: Optional[str] = None) -> None:
        """Valida que en entorno de producción no se utilicen secretos por defecto o vacíos."""
        active_env = (env or os.getenv("CCI_ENV", "development")).strip().lower()
        if active_env != "production":
            return

        jwt_secret = os.getenv("CCI_SECRET_KEY", "").strip()
        lk_key = os.getenv("LIVEKIT_API_KEY", "").strip()
        lk_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()

        if jwt_secret in INSECURE_SECRET_PLACEHOLDERS or len(jwt_secret) < 16:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: CCI_SECRET_KEY ausente, inseguro o por defecto en CCI_ENV=production."
            )
        if lk_key in INSECURE_SECRET_PLACEHOLDERS:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: LIVEKIT_API_KEY ausente o con valor de desarrollo ('devkey') en CCI_ENV=production."
            )
        if lk_secret in INSECURE_SECRET_PLACEHOLDERS or len(lk_secret) < 16:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: LIVEKIT_API_SECRET ausente, corto o inseguro en CCI_ENV=production."
            )

    @classmethod
    def from_env(cls, strict_production: bool = False) -> AppConfig:
        env = os.getenv("CCI_ENV", "development").strip()
        if strict_production or os.getenv("CCI_STRICT_SECRETS", "").lower() in ("1", "true", "yes"):
            cls.validate_production_secrets(env)

        secret = os.getenv("CCI_SECRET_KEY", "").strip()
        data_dir = ROOT / ".cci-user-data"
        data_dir.mkdir(parents=True, exist_ok=True)
        key_file = data_dir / ".secret_key"

        if not secret or secret in INSECURE_SECRET_PLACEHOLDERS:
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

        db_path = Path(os.getenv("CCI_DATABASE_PATH", str(data_dir / "cci_system.sqlite3")))
        comm_db_env = os.getenv("CCI_COMMUNITIES_DB_PATH", "").strip()
        if comm_db_env:
            comm_db_path = Path(comm_db_env)
        elif "CCI_DATABASE_PATH" in os.environ:
            comm_db_path = db_path
        else:
            comm_db_path = data_dir / "cci_communities.sqlite3"

        sounds_dir = Path(os.getenv("CCI_SOUNDS_STORAGE_PATH", str(data_dir / "sounds")))

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
            stun_server=os.getenv("CCI_STUN_SERVER", "stun:stun.l.google.com:19302"),
            turn_server=os.getenv("CCI_TURN_SERVER", ""),
            turn_username=os.getenv("CCI_TURN_USERNAME", ""),
            turn_credential=os.getenv("CCI_TURN_CREDENTIAL", ""),
            livekit_ws_url=os.getenv("LIVEKIT_WS_URL", "ws://localhost:7880"),
            livekit_api_key=os.getenv("LIVEKIT_API_KEY", "devkey" if env != "production" else ""),
            livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", "secretkey1234567890abcdef" if env != "production" else ""),
            recordings_path=Path(os.getenv("CCI_RECORDINGS_PATH", str(ROOT / "grabaciones"))),
            max_recordings_mb=int(os.getenv("CCI_MAX_RECORDINGS_STORAGE_MB", "2048")),
        )


config = AppConfig.from_env()
