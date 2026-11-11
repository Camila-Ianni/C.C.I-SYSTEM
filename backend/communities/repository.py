"""
backend/communities/repository.py - Capa de persistencia relacional para CCI Communities.

Motor activo y soportado en esta entrega: SQLite 3 en modo WAL (`PRAGMA journal_mode=WAL`,
`PRAGMA foreign_keys=ON`, `PRAGMA busy_timeout=10000`) sobre archivo persistente en disco
(`.cci-user-data/cci_communities.sqlite3` o `/data/cci_communities.sqlite3` en Docker),
con soporte aislado para pruebas herméticas (`allow_memory=True`).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

from backend.config import config


def _resolve_default_communities_db_path(requested_path: Optional[str] = None, allow_memory: bool = False) -> str:
    """Resuelve la ruta de base de datos persistente para Communities evitando :memory: por defecto."""
    env = os.getenv("CCI_ENV", config.env).strip().lower()
    if requested_path:
        raw = str(requested_path).strip()
        if raw == ":memory:":
            if env == "production" and not allow_memory:
                raise RuntimeError(
                    "CRITICAL ERROR: CommunitiesRepository no permite db_path=':memory:' en producción (CCI_ENV=production)."
                )
            return ":memory:"
        return raw

    comm_env = os.getenv("CCI_COMMUNITIES_DB_PATH", "").strip()
    if comm_env:
        if comm_env == ":memory:" and env == "production" and not allow_memory:
            raise RuntimeError(
                "CRITICAL ERROR: CCI_COMMUNITIES_DB_PATH=':memory:' prohibido en producción (CCI_ENV=production)."
            )
        return comm_env

    db_env = os.getenv("CCI_DATABASE_PATH", "").strip()
    if db_env:
        if db_env == ":memory:":
            if env == "production" and not allow_memory:
                raise RuntimeError(
                    "CRITICAL ERROR: CCI_DATABASE_PATH=':memory:' prohibido en producción (CCI_ENV=production)."
                )
            return ":memory:"
        candidate = Path(db_env)
        # Si el archivo ya existe y pertenece al esquema legacy cci_database (messages con sender_id),
        # derivar archivo hermano para no colisionar con la tabla messages de cci_database.
        if candidate.exists():
            try:
                with sqlite3.connect(str(candidate)) as probe:
                    cols = [r[1] for r in probe.execute("PRAGMA table_info(messages)").fetchall()]
                    if cols and "sender_id" in cols and "channel_id" not in cols:
                        candidate = candidate.with_name(f"{candidate.stem}_communities{candidate.suffix or '.sqlite3'}")
            except Exception:
                pass
        return str(candidate)

    default_path = Path(config.communities_database_path)
    if default_path.exists():
        try:
            with sqlite3.connect(str(default_path)) as probe:
                cols = [r[1] for r in probe.execute("PRAGMA table_info(messages)").fetchall()]
                if cols and "sender_id" in cols and "channel_id" not in cols:
                    default_path = default_path.parent / "cci_communities.sqlite3"
        except Exception:
            pass
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return str(default_path)


class CommunitiesRepository:
    """Repositorio de base de datos relacional para comunidades, canales, roles e invitaciones."""

    _instance: Optional[CommunitiesRepository] = None
    _lock = threading.RLock()

    def __init__(self, db_path: Optional[str] = None, allow_memory: bool = False):
        resolved = _resolve_default_communities_db_path(db_path, allow_memory=allow_memory)
        self.db_path = resolved
        self._is_memory = resolved == ":memory:" or "mode=memory" in resolved
        self._use_uri = False
        self._connect_target = resolved
        self._temp_mem_file: Optional[str] = None
        self._all_connections: List[sqlite3.Connection] = []
        self._tx_lock = threading.RLock()
        self._wal_initialized = False

        if resolved == ":memory:":
            # Respaldar el modo efímero de pruebas con un archivo temporal WAL aislado por instancia
            # para permitir conexiones independientes por hilo sin bloqueos de tabla ni pérdida de esquema entre hilos.
            import tempfile
            fd, tmp_path = tempfile.mkstemp(prefix="cci_comm_ephemeral_", suffix=".sqlite3")
            os.close(fd)
            self._temp_mem_file = tmp_path
            self._connect_target = tmp_path
        elif resolved.startswith("file:"):
            self._use_uri = True
        else:
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._init_schema()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> CommunitiesRepository:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    def close(self) -> None:
        """Cierra de forma limpia las conexiones de base de datos del repositorio."""
        with self._tx_lock:
            if hasattr(self._local, "conn") and self._local.conn is not None:
                try:
                    self._local.conn.close()
                except Exception:
                    pass
                self._local.conn = None
            for conn in list(self._all_connections):
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_connections.clear()
            if self._temp_mem_file:
                for suffix in ("", "-wal", "-shm"):
                    try:
                        p = Path(self._temp_mem_file + suffix)
                        if p.exists():
                            p.unlink()
                    except Exception:
                        pass
                self._temp_mem_file = None

    @classmethod
    def reset_instance(cls, db_path: Optional[str] = None) -> CommunitiesRepository:
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = cls(db_path)
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.execute("SELECT 1;")
                return conn
            except Exception:
                self._local.conn = None

        with self._tx_lock:
            conn = sqlite3.connect(
                self._connect_target,
                timeout=15.0,
                check_same_thread=False,
                uri=self._use_uri,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            if not self._wal_initialized:
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                    self._wal_initialized = True
                except Exception:
                    pass
            try:
                conn.execute("PRAGMA synchronous = NORMAL;")
            except Exception:
                pass
            self._local.conn = conn
            self._all_connections.append(conn)
            return conn

    def check_health(self) -> bool:
        """Verifica conectividad real e integridad básica del esquema."""
        conn = self._get_connection()
        row = conn.execute("SELECT COUNT(*) AS cnt FROM permissions;").fetchone()
        return bool(row and row["cnt"] > 0)

    def _init_schema(self) -> None:
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS communities (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                icon_url TEXT,
                banner_url TEXT,
                visibility TEXT NOT NULL DEFAULT 'private',
                max_members INTEGER NOT NULL DEFAULT 500,
                max_streams_per_channel INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                deleted_at REAL NULL
            );

            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#99AAB5',
                position INTEGER NOT NULL DEFAULT 0,
                is_default INTEGER NOT NULL DEFAULT 0,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                UNIQUE (community_id, name)
            );

            CREATE TABLE IF NOT EXISTS permissions (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id TEXT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                allowed INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (role_id, permission_id)
            );

            CREATE TABLE IF NOT EXISTS community_members (
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                nickname TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                joined_at REAL NOT NULL,
                PRIMARY KEY (community_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS member_roles (
                community_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                PRIMARY KEY (community_id, user_id, role_id),
                FOREIGN KEY (community_id, user_id) REFERENCES community_members(community_id, user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS channel_categories (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                category_id TEXT REFERENCES channel_categories(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                topic TEXT,
                position INTEGER NOT NULL DEFAULT 0,
                is_private INTEGER NOT NULL DEFAULT 0,
                max_participants INTEGER NOT NULL DEFAULT 0,
                bitrate_kbps INTEGER NOT NULL DEFAULT 64,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                deleted_at REAL NULL,
                UNIQUE (community_id, name)
            );

            CREATE TABLE IF NOT EXISTS channel_permission_overrides (
                channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                permission_id TEXT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                allow INTEGER NOT NULL DEFAULT 0,
                deny INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (channel_id, target_type, target_id, permission_id)
            );

            CREATE TABLE IF NOT EXISTS invitations (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                inviter_id TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 0,
                uses_count INTEGER NOT NULL DEFAULT 0,
                expires_at REAL NULL,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
                author_id TEXT NOT NULL,
                content TEXT NOT NULL,
                reply_to_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                edited_at REAL NULL,
                deleted_at REAL NULL
            );

            CREATE TABLE IF NOT EXISTS message_attachments (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                storage_key TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum_sha256 TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_presence (
                user_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'offline',
                custom_status TEXT,
                last_seen REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS voice_sessions (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                livekit_room_name TEXT NOT NULL,
                livekit_participant_id TEXT NOT NULL,
                is_muted INTEGER NOT NULL DEFAULT 0,
                is_deafened INTEGER NOT NULL DEFAULT 0,
                is_screen_sharing INTEGER NOT NULL DEFAULT 0,
                joined_at REAL NOT NULL,
                left_at REAL NULL
            );

            CREATE TABLE IF NOT EXISTS sound_categories (
                id TEXT PRIMARY KEY,
                scope_type TEXT NOT NULL,
                scope_id TEXT NULL,
                name TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sound_assets (
                id TEXT PRIMARY KEY,
                category_id TEXT REFERENCES sound_categories(id) ON DELETE SET NULL,
                owner_type TEXT NOT NULL,
                owner_id TEXT NULL,
                uploader_id TEXT NOT NULL,
                storage_key TEXT NOT NULL,
                title TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0.0,
                file_size_bytes INTEGER NOT NULL,
                format TEXT NOT NULL DEFAULT 'mp3',
                volume_scale REAL NOT NULL DEFAULT 1.0,
                cooldown_seconds INTEGER NOT NULL DEFAULT 5,
                checksum_sha256 TEXT NOT NULL,
                created_at REAL NOT NULL,
                deleted_at REAL NULL
            );

            CREATE TABLE IF NOT EXISTS sound_permissions (
                sound_asset_id TEXT NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
                role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                can_play INTEGER NOT NULL DEFAULT 1,
                can_manage INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (sound_asset_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS user_sound_favorites (
                user_id TEXT NOT NULL,
                sound_id TEXT NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
                hotkey TEXT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (user_id, sound_id)
            );

            CREATE TABLE IF NOT EXISTS sound_play_events (
                id TEXT PRIMARY KEY,
                sound_id TEXT NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                played_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stream_sessions (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                stream_type TEXT NOT NULL DEFAULT 'screen',
                title TEXT NOT NULL,
                game_id TEXT NULL,
                resolution TEXT NOT NULL DEFAULT '1080p',
                fps INTEGER NOT NULL DEFAULT 60,
                bitrate_kbps INTEGER NOT NULL DEFAULT 4500,
                has_audio INTEGER NOT NULL DEFAULT 1,
                is_paused INTEGER NOT NULL DEFAULT 0,
                livekit_track_id TEXT NULL,
                started_at REAL NOT NULL,
                ended_at REAL NULL
            );

            CREATE TABLE IF NOT EXISTS moderation_actions (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                actor_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NULL,
                expires_at REAL NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                reporter_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                resolution_notes TEXT NULL,
                resolved_by TEXT NULL,
                created_at REAL NOT NULL,
                resolved_at REAL NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                actor_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_id TEXT NULL,
                details_json TEXT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_communities_owner ON communities(owner_id);
            CREATE INDEX IF NOT EXISTS idx_channels_community ON channels(community_id, position);
            CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_members_user ON community_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_community_created ON audit_log(community_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_voice_sessions_channel ON voice_sessions(channel_id, left_at);
            CREATE INDEX IF NOT EXISTS idx_stream_sessions_channel ON stream_sessions(channel_id, ended_at);

            CREATE TABLE IF NOT EXISTS message_reactions (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                emoji TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(message_id, user_id, emoji)
            );

            CREATE TABLE IF NOT EXISTS activity_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                game_id TEXT NULL,
                title TEXT NULL,
                metadata_json TEXT NULL,
                visibility TEXT NOT NULL DEFAULT 'communities',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                actor_id TEXT NULL,
                community_id TEXT NULL,
                channel_id TEXT NULL,
                message_id TEXT NULL,
                title TEXT NOT NULL,
                body TEXT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS staged_attachments (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                uploader_id TEXT NOT NULL,
                storage_key TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum_sha256 TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS spotify_oauth_states (
                state TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                redirect_uri TEXT NOT NULL,
                scopes TEXT NOT NULL,
                share_presence INTEGER NOT NULL DEFAULT 1,
                code_challenge TEXT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS spotify_connections (
                user_id TEXT PRIMARY KEY,
                spotify_user_id TEXT NULL,
                display_name TEXT NULL,
                scopes TEXT NOT NULL,
                token_ciphertext TEXT NULL,
                expires_at REAL NULL,
                opt_in_enabled INTEGER NOT NULL DEFAULT 0,
                share_presence INTEGER NOT NULL DEFAULT 1,
                current_track TEXT NULL,
                current_artist TEXT NULL,
                connected_at REAL NULL,
                updated_at REAL NOT NULL,
                revoked_at REAL NULL
            );

            CREATE INDEX IF NOT EXISTS idx_reactions_message ON message_reactions(message_id);
            CREATE INDEX IF NOT EXISTS idx_activity_user_created ON activity_events(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON user_notifications(user_id, is_read, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_spotify_states_user ON spotify_oauth_states(user_id, expires_at);
            """)

            # Migración aditiva segura para user_presence (TTL + actividad real de juego)
            presence_cols = {
                r[1] for r in conn.execute("PRAGMA table_info(user_presence)").fetchall()
            }
            for col_name, col_def in (
                ("activity_type", "TEXT NULL"),
                ("activity_title", "TEXT NULL"),
                ("activity_game_id", "TEXT NULL"),
                ("activity_started_at", "REAL NULL"),
                ("activity_visibility", "TEXT NOT NULL DEFAULT 'communities'"),
                ("expires_at", "REAL NOT NULL DEFAULT 0"),
            ):
                if col_name not in presence_cols:
                    conn.execute(f"ALTER TABLE user_presence ADD COLUMN {col_name} {col_def}")

            # Sembrar catálogo canónico de permisos
            canonical_permissions = [
                ("community.manage", "community", "Editar información y ajustes de la comunidad"),
                ("community.view", "community", "Ver canales y contenido de la comunidad"),
                ("community.invites.create", "community", "Generar enlaces de invitación"),
                ("community.roles.manage", "community", "Crear y asignar roles inferiores"),
                ("community.members.kick", "moderation", "Expulsar miembros de la comunidad"),
                ("community.members.ban", "moderation", "Prohibir permanentemente el acceso a miembros"),
                ("channels.manage", "channels", "Crear, editar y eliminar canales"),
                ("messages.read", "chat", "Leer historial y mensajes en canales de texto"),
                ("messages.send", "chat", "Enviar mensajes en canales de texto"),
                ("messages.manage", "chat", "Eliminar y fijar mensajes de otros miembros"),
                ("messages.attachments", "chat", "Subir imágenes y archivos adjuntos"),
                ("voice.connect", "voice", "Conectarse a salas de voz"),
                ("voice.speak", "voice", "Transmitir audio por micrófono"),
                ("voice.stream", "voice", "Transmitir pantalla o juego en vivo"),
                ("voice.mute_members", "voice", "Silenciar a otros participantes en la sala"),
                ("soundboard.play", "soundboard", "Reproducir sonidos en salas de voz"),
                ("soundboard.manage", "soundboard", "Subir y administrar sonidos de la comunidad"),
            ]
            for pid, cat, desc in canonical_permissions:
                conn.execute(
                    "INSERT OR IGNORE INTO permissions (id, category, description) VALUES (?, ?, ?)",
                    (pid, cat, desc)
                )

    # =========================================================================
    # COMUNIDADES
    # =========================================================================

    def create_community(
        self,
        owner_id: str,
        name: str,
        slug: str,
        description: Optional[str] = None,
        visibility: str = "private",
        icon_url: Optional[str] = None,
        banner_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        comm_id = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO communities (id, owner_id, name, slug, description, icon_url, banner_url, visibility, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (comm_id, owner_id, name, slug, description, icon_url, banner_url, visibility, now, now)
            )
            # Agregar al propietario como miembro
            conn.execute(
                "INSERT INTO community_members (community_id, user_id, joined_at) VALUES (?, ?, ?)",
                (comm_id, owner_id, now)
            )
        return self.get_community(comm_id)  # type: ignore

    def get_community(self, community_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM communities WHERE id = ? AND deleted_at IS NULL",
            (community_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_community_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM communities WHERE slug = ? AND deleted_at IS NULL",
            (slug,)
        ).fetchone()
        return dict(row) if row else None

    def list_communities_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT c.* FROM communities c
            INNER JOIN community_members m ON c.id = m.community_id
            WHERE m.user_id = ? AND m.status = 'active' AND c.deleted_at IS NULL
            ORDER BY c.created_at ASC
            """,
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def list_public_communities(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM communities WHERE visibility = 'public' AND deleted_at IS NULL ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_community(self, community_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed = {"name", "description", "icon_url", "banner_url", "visibility", "max_members", "max_streams_per_channel"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_community(community_id)

        updates["updated_at"] = time.time()
        clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [community_id]

        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(f"UPDATE communities SET {clause} WHERE id = ? AND deleted_at IS NULL", values)
        return self.get_community(community_id)

    def delete_community(self, community_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE communities SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (now, community_id)
            )
            return cur.rowcount > 0

    def transfer_ownership(self, community_id: str, new_owner_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE communities SET owner_id = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
                (new_owner_id, now, community_id)
            )
            return cur.rowcount > 0

    # =========================================================================
    # ROLES Y PERMISOS
    # =========================================================================

    def create_role(
        self,
        community_id: str,
        name: str,
        color: str = "#99AAB5",
        position: int = 0,
        is_default: bool = False,
        is_admin: bool = False,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        role_id = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO roles (id, community_id, name, color, position, is_default, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (role_id, community_id, name, color, position, int(is_default), int(is_admin), now)
            )
            if permissions:
                for pid in permissions:
                    conn.execute(
                        "INSERT OR REPLACE INTO role_permissions (role_id, permission_id, allowed) VALUES (?, ?, 1)",
                        (role_id, pid)
                    )
        return self.get_role(role_id)  # type: ignore

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        perms = conn.execute(
            "SELECT permission_id FROM role_permissions WHERE role_id = ? AND allowed = 1",
            (role_id,)
        ).fetchall()
        res["permissions"] = [p[0] for p in perms]
        res["is_default"] = bool(res["is_default"])
        res["is_admin"] = bool(res["is_admin"])
        return res

    def list_roles(self, community_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM roles WHERE community_id = ? ORDER BY position ASC, created_at ASC",
            (community_id,)
        ).fetchall()
        result = []
        for r in rows:
            role = dict(r)
            perms = conn.execute(
                "SELECT permission_id FROM role_permissions WHERE role_id = ? AND allowed = 1",
                (role["id"],)
            ).fetchall()
            role["permissions"] = [p[0] for p in perms]
            role["is_default"] = bool(role["is_default"])
            role["is_admin"] = bool(role["is_admin"])
            result.append(role)
        return result

    def update_role(self, role_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed = {"name", "color", "position", "is_admin"}
        updates = {k: v for k, v in fields.items() if k in allowed}

        conn = self._get_connection()
        with self._tx_lock, conn:
            if updates:
                clause = ", ".join(f"{k} = ?" for k in updates)
                conn.execute(f"UPDATE roles SET {clause} WHERE id = ?", list(updates.values()) + [role_id])

            if "permissions" in fields:
                conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
                for pid in fields["permissions"]:
                    conn.execute(
                        "INSERT INTO role_permissions (role_id, permission_id, allowed) VALUES (?, ?, 1)",
                        (role_id, pid)
                    )
        return self.get_role(role_id)

    def delete_role(self, role_id: str) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute("DELETE FROM roles WHERE id = ? AND is_default = 0", (role_id,))
            return cur.rowcount > 0

    # =========================================================================
    # MIEMBROS Y ASIGNACIÓN DE ROLES
    # =========================================================================

    def add_member(self, community_id: str, user_id: str, nickname: Optional[str] = None) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO community_members (community_id, user_id, nickname, status, joined_at)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (community_id, user_id, nickname, now)
            )
            # Asignar rol por defecto (@everyone) si existe
            default_role = conn.execute(
                "SELECT id FROM roles WHERE community_id = ? AND is_default = 1",
                (community_id,)
            ).fetchone()
            if default_role:
                conn.execute(
                    "INSERT OR IGNORE INTO member_roles (community_id, user_id, role_id) VALUES (?, ?, ?)",
                    (community_id, user_id, default_role[0])
                )
        return True

    def remove_member(self, community_id: str, user_id: str) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "DELETE FROM community_members WHERE community_id = ? AND user_id = ?",
                (community_id, user_id)
            )
            return cur.rowcount > 0

    def get_member(self, community_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM community_members WHERE community_id = ? AND user_id = ?",
            (community_id, user_id)
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        roles = conn.execute(
            """
            SELECT r.* FROM roles r
            INNER JOIN member_roles mr ON r.id = mr.role_id
            WHERE mr.community_id = ? AND mr.user_id = ?
            ORDER BY r.position ASC
            """,
            (community_id, user_id)
        ).fetchall()
        res["roles"] = [dict(r) for r in roles]
        return res

    def list_members(self, community_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM community_members WHERE community_id = ? AND status = 'active' ORDER BY joined_at ASC",
            (community_id,)
        ).fetchall()
        res = []
        for r in rows:
            m = dict(r)
            roles = conn.execute(
                """
                SELECT r.id, r.name, r.color, r.position FROM roles r
                INNER JOIN member_roles mr ON r.id = mr.role_id
                WHERE mr.community_id = ? AND mr.user_id = ?
                ORDER BY r.position ASC
                """,
                (community_id, m["user_id"])
            ).fetchall()
            m["roles"] = [dict(ro) for ro in roles]
            res.append(m)
        return res

    def assign_role_to_member(self, community_id: str, user_id: str, role_id: str) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                "INSERT OR IGNORE INTO member_roles (community_id, user_id, role_id) VALUES (?, ?, ?)",
                (community_id, user_id, role_id)
            )
        return True

    def remove_role_from_member(self, community_id: str, user_id: str, role_id: str) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "DELETE FROM member_roles WHERE community_id = ? AND user_id = ? AND role_id = ?",
                (community_id, user_id, role_id)
            )
            return cur.rowcount > 0

    # =========================================================================
    # CANALES Y SOBRESCRITURAS DE PERMISOS
    # =========================================================================

    def create_channel(
        self,
        community_id: str,
        name: str,
        channel_type: str = "text",
        category_id: Optional[str] = None,
        topic: Optional[str] = None,
        is_private: bool = False,
        max_participants: int = 0,
        bitrate_kbps: int = 64,
        position: int = 0,
    ) -> Dict[str, Any]:
        chan_id = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO channels (id, community_id, category_id, name, type, topic, position, is_private, max_participants, bitrate_kbps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (chan_id, community_id, category_id, name, channel_type, topic, position, int(is_private), max_participants, bitrate_kbps, now, now)
            )
        return self.get_channel(chan_id)  # type: ignore

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM channels WHERE id = ? AND deleted_at IS NULL", (channel_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        res["is_private"] = bool(res["is_private"])
        return res

    def list_channels(self, community_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM channels WHERE community_id = ? AND deleted_at IS NULL ORDER BY position ASC, created_at ASC",
            (community_id,)
        ).fetchall()
        result = []
        for r in rows:
            c = dict(r)
            c["is_private"] = bool(c["is_private"])
            result.append(c)
        return result

    def update_channel(self, channel_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed = {"name", "topic", "position", "is_private", "max_participants", "bitrate_kbps", "category_id"}
        updates = {k: (int(v) if isinstance(v, bool) else v) for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_channel(channel_id)

        updates["updated_at"] = time.time()
        clause = ", ".join(f"{k} = ?" for k in updates)
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(f"UPDATE channels SET {clause} WHERE id = ? AND deleted_at IS NULL", list(updates.values()) + [channel_id])
        return self.get_channel(channel_id)

    def delete_channel(self, channel_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute("UPDATE channels SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL", (now, channel_id))
            return cur.rowcount > 0

    def set_channel_override(
        self,
        channel_id: str,
        target_type: str,
        target_id: str,
        permission_id: str,
        allow: bool = False,
        deny: bool = False,
    ) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO channel_permission_overrides (channel_id, target_type, target_id, permission_id, allow, deny)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (channel_id, target_type, target_id, permission_id, int(allow), int(deny))
            )
        return True

    def get_channel_overrides(self, channel_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM channel_permission_overrides WHERE channel_id = ?",
            (channel_id,)
        ).fetchall()
        return [{**dict(r), "allow": bool(r["allow"]), "deny": bool(r["deny"])} for r in rows]

    # =========================================================================
    # INVITACIONES
    # =========================================================================

    def create_invitation(
        self,
        community_id: str,
        inviter_id: str,
        max_uses: int = 0,
        expires_in_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        inv_id = str(uuid.uuid4())
        code = uuid.uuid4().hex[:10].upper()
        now = time.time()
        expires_at = (now + expires_in_hours * 3600) if expires_in_hours else None

        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO invitations (id, community_id, inviter_id, code, max_uses, uses_count, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (inv_id, community_id, inviter_id, code, max_uses, expires_at, now)
            )
        return self.get_invitation_by_code(code)  # type: ignore

    def get_invitation_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM invitations WHERE code = ? AND is_revoked = 0", (code,)).fetchone()
        return dict(row) if row else None

    def consume_invitation(self, code: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            inv = self.get_invitation_by_code(code)
            if not inv:
                return False
            if inv["expires_at"] and inv["expires_at"] < now:
                return False
            if inv["max_uses"] > 0 and inv["uses_count"] >= inv["max_uses"]:
                return False

            conn.execute(
                "UPDATE invitations SET uses_count = uses_count + 1 WHERE code = ?",
                (code,)
            )
            return True

    def list_invitations(self, community_id: str, include_revoked: bool = False) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        if include_revoked:
            rows = conn.execute(
                """
                SELECT * FROM invitations
                WHERE community_id = ?
                ORDER BY created_at DESC
                """,
                (community_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM invitations
                WHERE community_id = ? AND COALESCE(is_revoked, 0) = 0
                ORDER BY created_at DESC
                """,
                (community_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["is_revoked"] = bool(d.get("is_revoked"))
            out.append(d)
        return out

    def revoke_invitation(self, community_id: str, code: str) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE invitations SET is_revoked = 1 WHERE community_id = ? AND code = ?",
                (community_id, code),
            )
            return cur.rowcount > 0

    # =========================================================================
    # MENSAJERÍA, HISTORIAL Y ADJUNTOS
    # =========================================================================

    def create_message(
        self,
        channel_id: str,
        author_id: str,
        content: str,
        reply_to_id: Optional[str] = None,
        is_pinned: bool = False,
    ) -> Dict[str, Any]:
        msg_id = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO messages (id, channel_id, author_id, content, reply_to_id, is_pinned, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, channel_id, author_id, content, reply_to_id, int(is_pinned), now)
            )
        return self.get_message(msg_id)  # type: ignore

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ? AND deleted_at IS NULL",
            (message_id,)
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        res["is_pinned"] = bool(res["is_pinned"])
        return res

    def add_message_attachment(
        self,
        attachment_id: str,
        message_id: str,
        storage_key: str,
        filename: str,
        content_type: str = "image/png",
        size_bytes: int = 0,
        checksum_sha256: str = "",
    ) -> Dict[str, Any]:
        """Registra un archivo o captura adjunta vinculada a un mensaje en SQLite WAL."""
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO message_attachments (id, message_id, storage_key, filename, content_type, size_bytes, checksum_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (attachment_id, message_id, storage_key, filename, content_type, size_bytes, checksum_sha256, now),
            )
        return {
            "id": attachment_id,
            "message_id": message_id,
            "storage_key": storage_key,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "checksum_sha256": checksum_sha256,
            "created_at": now,
        }

    def list_message_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """Recupera los archivos o capturas adjuntas asociadas a un mensaje."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM message_attachments WHERE message_id = ? ORDER BY created_at ASC",
            (message_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_attachment(self, attachment_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM message_attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
        return dict(row) if row else None

    def link_attachment_to_message(self, attachment_id: str, message_id: str) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE message_attachments SET message_id = ? WHERE id = ?",
                (message_id, attachment_id),
            )
            return cur.rowcount > 0

    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            existing = conn.execute(
                "SELECT id FROM message_reactions WHERE message_id = ? AND user_id = ? AND emoji = ?",
                (message_id, user_id, emoji),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM message_reactions WHERE id = ?", (existing[0],))
                added = False
            else:
                conn.execute(
                    "INSERT INTO message_reactions (id, message_id, user_id, emoji, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), message_id, user_id, emoji, now),
                )
                added = True
        return {"added": added, "reactions": self.list_message_reactions(message_id)}

    def list_message_reactions(self, message_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT emoji, user_id FROM message_reactions WHERE message_id = ? ORDER BY created_at ASC",
            (message_id,),
        ).fetchall()
        grouped: Dict[str, List[str]] = {}
        for r in rows:
            grouped.setdefault(r[0], []).append(r[1])
        return [{"emoji": e, "count": len(uids), "user_ids": uids} for e, uids in grouped.items()]

    def list_messages_after(
        self,
        channel_id: str,
        after_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        anchor = conn.execute("SELECT created_at FROM messages WHERE id = ?", (after_id,)).fetchone()
        if not anchor:
            return self.list_messages(channel_id, limit=limit)
        rows = conn.execute(
            """
            SELECT * FROM messages
            WHERE channel_id = ? AND deleted_at IS NULL AND created_at > ?
            ORDER BY created_at ASC LIMIT ?
            """,
            (channel_id, anchor[0], limit),
        ).fetchall()
        result = [dict(r) for r in rows]
        for r in result:
            r["is_pinned"] = bool(r["is_pinned"])
        return result

    def list_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista mensajes en orden cronológico con paginación basada en cursor before_id."""
        conn = self._get_connection()
        before_time = None
        if before_id:
            row_b = conn.execute("SELECT created_at FROM messages WHERE id = ?", (before_id,)).fetchone()
            if row_b:
                before_time = row_b[0]

        if before_time:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE channel_id = ? AND deleted_at IS NULL AND created_at < ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (channel_id, before_time, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE channel_id = ? AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT ?
                """,
                (channel_id, limit)
            ).fetchall()

        # Retornar en orden cronológico ascendente para renderizado de chat
        result = [dict(r) for r in reversed(rows)]
        for r in result:
            r["is_pinned"] = bool(r["is_pinned"])
        return result

    def update_message(self, message_id: str, new_content: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE messages SET content = ?, edited_at = ? WHERE id = ? AND deleted_at IS NULL",
                (new_content, now, message_id)
            )
            if cur.rowcount == 0:
                return None
        return self.get_message(message_id)

    def delete_message(self, message_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE messages SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (now, message_id)
            )
            return cur.rowcount > 0

    # =========================================================================
    # ESTADOS DE PRESENCIA (ONLINE, IDLE, DND, INVISIBLE)
    # =========================================================================

    def set_presence(
        self,
        user_id: str,
        status: str = "online",
        custom_status: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
        activity_type: Optional[str] = None,
        activity_title: Optional[str] = None,
        activity_game_id: Optional[str] = None,
        activity_started_at: Optional[float] = None,
        activity_visibility: Optional[str] = None,
        preserve_activity: bool = True,
    ) -> Dict[str, Any]:
        now = time.time()
        default_ttl = float(os.getenv("CCI_PRESENCE_TTL_SECONDS", "60"))
        effective_ttl = max(0.0, float(ttl_seconds if ttl_seconds is not None else default_ttl))
        expires_at = (now + effective_ttl) if status != "offline" else now

        conn = self._get_connection()
        with self._tx_lock, conn:
            prev = conn.execute("SELECT * FROM user_presence WHERE user_id = ?", (user_id,)).fetchone()
            prev_d = dict(prev) if prev else {}

            if status == "offline":
                a_type = None
                a_title = None
                a_gid = None
                a_started = None
            elif not preserve_activity or activity_type is not None or activity_title is not None:
                a_type = activity_type
                a_title = activity_title
                a_gid = activity_game_id
                a_started = activity_started_at if activity_started_at is not None else (now if a_title else None)
            else:
                a_type = prev_d.get("activity_type")
                a_title = prev_d.get("activity_title")
                a_gid = prev_d.get("activity_game_id")
                a_started = prev_d.get("activity_started_at")

            a_vis = activity_visibility or prev_d.get("activity_visibility") or "communities"
            conn.execute(
                """
                INSERT INTO user_presence (
                    user_id, status, custom_status, last_seen,
                    activity_type, activity_title, activity_game_id, activity_started_at, activity_visibility, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    status = excluded.status,
                    custom_status = excluded.custom_status,
                    last_seen = excluded.last_seen,
                    activity_type = excluded.activity_type,
                    activity_title = excluded.activity_title,
                    activity_game_id = excluded.activity_game_id,
                    activity_started_at = excluded.activity_started_at,
                    activity_visibility = excluded.activity_visibility,
                    expires_at = excluded.expires_at
                """,
                (user_id, status, custom_status, now, a_type, a_title, a_gid, a_started, a_vis, expires_at),
            )
        return self.get_presence(user_id)

    def heartbeat_presence(self, user_id: str, ttl_seconds: Optional[float] = None) -> Dict[str, Any]:
        now = time.time()
        default_ttl = float(os.getenv("CCI_PRESENCE_TTL_SECONDS", "60"))
        effective_ttl = max(0.0, float(ttl_seconds if ttl_seconds is not None else default_ttl))
        conn = self._get_connection()
        with self._tx_lock, conn:
            row = conn.execute("SELECT status, custom_status FROM user_presence WHERE user_id = ?", (user_id,)).fetchone()
            if not row or row[0] == "offline":
                return self.set_presence(user_id, status="online", ttl_seconds=effective_ttl)
            conn.execute(
                "UPDATE user_presence SET last_seen = ?, expires_at = ? WHERE user_id = ?",
                (now, now + effective_ttl, user_id),
            )
        return self.get_presence(user_id)

    @staticmethod
    def _default_offline_presence(user_id: str, last_seen: float = 0.0) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "status": "offline",
            "custom_status": None,
            "last_seen": last_seen,
            "activity_type": None,
            "activity_title": None,
            "activity_game_id": None,
            "activity_started_at": None,
            "activity_visibility": "communities",
            "expires_at": 0.0,
        }

    def _normalize_presence_row(self, row_dict: Dict[str, Any], now: float) -> Dict[str, Any]:
        exp = float(row_dict.get("expires_at") or 0.0)
        if row_dict.get("status") != "offline" and exp > 0 and now > exp:
            # TTL expirado: persistir caída a offline y limpiar actividad obsoleta
            uid = row_dict["user_id"]
            conn = self._get_connection()
            with self._tx_lock, conn:
                conn.execute(
                    """
                    UPDATE user_presence
                    SET status = 'offline',
                        activity_type = NULL,
                        activity_title = NULL,
                        activity_game_id = NULL,
                        activity_started_at = NULL
                    WHERE user_id = ? AND expires_at > 0 AND expires_at < ?
                    """,
                    (uid, now),
                )
            return self._default_offline_presence(uid, last_seen=float(row_dict.get("last_seen") or 0.0))
        return row_dict

    def get_presence(self, user_id: str, now: Optional[float] = None) -> Dict[str, Any]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM user_presence WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return self._default_offline_presence(user_id)
        return self._normalize_presence_row(dict(row), now if now is not None else time.time())

    def list_presences(self, user_ids: List[str], now: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        if not user_ids:
            return {}
        ts = now if now is not None else time.time()
        conn = self._get_connection()
        placeholders = ",".join("?" for _ in user_ids)
        rows = conn.execute(
            f"SELECT * FROM user_presence WHERE user_id IN ({placeholders})",
            user_ids
        ).fetchall()
        result = {}
        for r in rows:
            d = self._normalize_presence_row(dict(r), ts)
            result[d["user_id"]] = d
        for uid in user_ids:
            if uid not in result:
                result[uid] = self._default_offline_presence(uid)
        return result

    # =========================================================================
    # SESIONES DE VOZ (LIVEKIT SFU)
    # =========================================================================

    def create_voice_session(
        self,
        channel_id: str,
        user_id: str,
        room_name: str,
        participant_id: str,
    ) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            # Finalizar cualquier sesión previa activa del usuario en este canal
            conn.execute(
                "UPDATE voice_sessions SET left_at = ? WHERE channel_id = ? AND user_id = ? AND left_at IS NULL",
                (now, channel_id, user_id)
            )
            conn.execute(
                """
                INSERT INTO voice_sessions (id, channel_id, user_id, livekit_room_name, livekit_participant_id, joined_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, channel_id, user_id, room_name, participant_id, now)
            )
        return {
            "session_id": session_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "livekit_room_name": room_name,
            "livekit_participant_id": participant_id,
            "is_muted": False,
            "is_deafened": False,
            "is_screen_sharing": False,
            "joined_at": now,
            "left_at": None,
        }

    def end_voice_session(self, channel_id: str, user_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE voice_sessions SET left_at = ? WHERE channel_id = ? AND user_id = ? AND left_at IS NULL",
                (now, channel_id, user_id)
            )
            return cur.rowcount > 0

    def update_voice_session_mute(self, channel_id: str, user_id: str, is_muted: bool) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE voice_sessions SET is_muted = ? WHERE channel_id = ? AND user_id = ? AND left_at IS NULL",
                (int(is_muted), channel_id, user_id)
            )
            return cur.rowcount > 0

    def list_active_voice_sessions(self, channel_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT * FROM voice_sessions
            WHERE channel_id = ? AND left_at IS NULL
            ORDER BY joined_at ASC
            """,
            (channel_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_muted"] = bool(d["is_muted"])
            d["is_deafened"] = bool(d["is_deafened"])
            d["is_screen_sharing"] = bool(d["is_screen_sharing"])
            result.append(d)
        return result

    def count_active_voice_sessions(self, channel_id: str) -> int:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT COUNT(*) FROM voice_sessions WHERE channel_id = ? AND left_at IS NULL",
            (channel_id,)
        ).fetchone()
        return row[0] if row else 0

    # =========================================================================
    # SOUND DECK (CATEGORÍAS, SONIDOS, FAVORITOS, COOLDOWNS)
    # =========================================================================

    def create_sound_category(
        self,
        category_id: str,
        scope_type: str,
        scope_id: Optional[str],
        name: str,
        position: int = 0
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO sound_categories (id, scope_type, scope_id, name, position, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (category_id, scope_type, scope_id, name, position, now)
            )
        return {
            "id": category_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "name": name,
            "position": position,
            "created_at": now
        }

    def get_sound_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM sound_categories WHERE id = ?",
            (category_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_sound_categories(
        self,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        query = "SELECT * FROM sound_categories WHERE 1=1"
        params: List[Any] = []
        if scope_type is not None:
            query += " AND scope_type = ?"
            params.append(scope_type)
        if scope_id is not None:
            query += " AND scope_id = ?"
            params.append(scope_id)
        query += " ORDER BY position ASC, name ASC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def create_sound_asset(
        self,
        sound_id: str,
        category_id: Optional[str],
        owner_type: str,
        owner_id: Optional[str],
        uploader_id: str,
        storage_key: str,
        title: str,
        duration_seconds: float,
        file_size_bytes: int,
        format_str: str,
        volume_scale: float,
        cooldown_seconds: int,
        checksum_sha256: str
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO sound_assets (
                    id, category_id, owner_type, owner_id, uploader_id,
                    storage_key, title, duration_seconds, file_size_bytes,
                    format, volume_scale, cooldown_seconds, checksum_sha256,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sound_id, category_id, owner_type, owner_id, uploader_id,
                    storage_key, title, duration_seconds, file_size_bytes,
                    format_str, volume_scale, cooldown_seconds, checksum_sha256,
                    now
                )
            )
        return self.get_sound_asset(sound_id)

    def get_sound_asset(self, sound_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM sound_assets WHERE id = ? AND deleted_at IS NULL",
            (sound_id,)
        ).fetchone()
        return dict(row) if row else None

    def count_user_sounds(self, user_id: str) -> int:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT COUNT(*) FROM sound_assets WHERE owner_type = 'user' AND owner_id = ? AND deleted_at IS NULL",
            (user_id,)
        ).fetchone()
        return row[0] if row else 0

    def list_sound_assets(
        self,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        query = "SELECT * FROM sound_assets WHERE deleted_at IS NULL"
        params: List[Any] = []
        if owner_type is not None:
            query += " AND owner_type = ?"
            params.append(owner_type)
        if owner_id is not None:
            query += " AND owner_id = ?"
            params.append(owner_id)
        if category_id is not None:
            query += " AND category_id = ?"
            params.append(category_id)
        if search:
            query += " AND title LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def list_sounds_for_community(
        self,
        community_id: str,
        user_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        # Union: community sounds + global sounds + user's personal sounds
        query = """
            SELECT * FROM sound_assets
            WHERE deleted_at IS NULL
              AND (
                  (owner_type = 'community' AND owner_id = ?)
                  OR (owner_type = 'global')
                  OR (? IS NOT NULL AND owner_type = 'user' AND owner_id = ?)
              )
        """
        params: List[Any] = [community_id, user_id, user_id]
        if search:
            query += " AND title LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY owner_type ASC, title ASC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def update_sound_asset(
        self,
        sound_id: str,
        title: Optional[str] = None,
        category_id: Optional[str] = None,
        volume_scale: Optional[float] = None,
        cooldown_seconds: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)
        if volume_scale is not None:
            updates.append("volume_scale = ?")
            params.append(volume_scale)
        if cooldown_seconds is not None:
            updates.append("cooldown_seconds = ?")
            params.append(cooldown_seconds)
        if not updates:
            return self.get_sound_asset(sound_id)
        params.append(sound_id)
        with self._tx_lock, conn:
            conn.execute(
                f"UPDATE sound_assets SET {', '.join(updates)} WHERE id = ? AND deleted_at IS NULL",
                tuple(params)
            )
        return self.get_sound_asset(sound_id)

    def delete_sound_asset(self, sound_id: str) -> bool:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE sound_assets SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (now, sound_id)
            )
            return cur.rowcount > 0

    def set_sound_favorite(
        self,
        user_id: str,
        sound_id: str,
        is_favorite: bool = True,
        hotkey: Optional[str] = None
    ) -> bool:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            if is_favorite:
                conn.execute(
                    """
                    INSERT INTO user_sound_favorites (user_id, sound_id, hotkey, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, sound_id) DO UPDATE SET hotkey = excluded.hotkey
                    """,
                    (user_id, sound_id, hotkey, now)
                )
            else:
                conn.execute(
                    "DELETE FROM user_sound_favorites WHERE user_id = ? AND sound_id = ?",
                    (user_id, sound_id)
                )
        return True

    def get_sound_favorite(self, user_id: str, sound_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM user_sound_favorites WHERE user_id = ? AND sound_id = ?",
            (user_id, sound_id)
        ).fetchone()
        return dict(row) if row else None

    def list_sound_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT f.sound_id, f.hotkey, f.created_at, s.title, s.owner_type, s.owner_id, s.duration_seconds, s.volume_scale
            FROM user_sound_favorites f
            JOIN sound_assets s ON f.sound_id = s.id
            WHERE f.user_id = ? AND s.deleted_at IS NULL
            ORDER BY f.created_at DESC
            """,
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_sound_play(self, play_id: str, sound_id: str, user_id: str, channel_id: str) -> float:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO sound_play_events (id, sound_id, user_id, channel_id, played_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (play_id, sound_id, user_id, channel_id, now)
            )
        return now

    def get_last_sound_play(
        self,
        sound_id: str,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None
    ) -> Optional[float]:
        conn = self._get_connection()
        query = "SELECT MAX(played_at) FROM sound_play_events WHERE sound_id = ?"
        params: List[Any] = [sound_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if channel_id:
            query += " AND channel_id = ?"
            params.append(channel_id)
        row = conn.execute(query, tuple(params)).fetchone()
        return row[0] if (row and row[0] is not None) else None

    # =========================================================================
    # STREAMING (PANTALLA, VENTANA, JUEGO)
    # =========================================================================

    def create_stream_session(
        self,
        session_id: str,
        channel_id: str,
        user_id: str,
        stream_type: str,
        title: str,
        game_id: Optional[str] = None,
        resolution: str = "1080p",
        fps: int = 60,
        bitrate_kbps: int = 4500,
        has_audio: bool = True,
        livekit_track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO stream_sessions (
                    id, channel_id, user_id, stream_type, title, game_id,
                    resolution, fps, bitrate_kbps, has_audio, is_paused,
                    livekit_track_id, started_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    session_id, channel_id, user_id, stream_type, title, game_id,
                    resolution, fps, bitrate_kbps, int(has_audio),
                    livekit_track_id, now
                )
            )
            # Marcar is_screen_sharing en la sesión de voz si existe
            conn.execute(
                "UPDATE voice_sessions SET is_screen_sharing = 1 WHERE channel_id = ? AND user_id = ? AND left_at IS NULL",
                (channel_id, user_id)
            )
        return self.get_stream_session(session_id)

    def get_stream_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM stream_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["has_audio"] = bool(d["has_audio"])
        d["is_paused"] = bool(d["is_paused"])
        return d

    def get_active_stream_for_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM stream_sessions WHERE channel_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (channel_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["has_audio"] = bool(d["has_audio"])
        d["is_paused"] = bool(d["is_paused"])
        return d

    def count_active_streams(self, channel_id: str) -> int:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT COUNT(*) FROM stream_sessions WHERE channel_id = ? AND ended_at IS NULL",
            (channel_id,)
        ).fetchone()
        return row[0] if row else 0

    def list_active_streams(self, community_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        if community_id:
            rows = conn.execute(
                """
                SELECT s.* FROM stream_sessions s
                JOIN channels c ON s.channel_id = c.id
                WHERE c.community_id = ? AND s.ended_at IS NULL
                ORDER BY s.started_at DESC
                """,
                (community_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stream_sessions WHERE ended_at IS NULL ORDER BY started_at DESC"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["has_audio"] = bool(d["has_audio"])
            d["is_paused"] = bool(d["is_paused"])
            result.append(d)
        return result

    def pause_stream_session(self, session_id: str, is_paused: bool = True) -> bool:
        conn = self._get_connection()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE stream_sessions SET is_paused = ? WHERE id = ? AND ended_at IS NULL",
                (int(is_paused), session_id)
            )
            return cur.rowcount > 0

    def end_stream_session(self, session_id: str) -> bool:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            # Obtener channel_id y user_id antes de cerrar
            row = conn.execute("SELECT channel_id, user_id FROM stream_sessions WHERE id = ?", (session_id,)).fetchone()
            cur = conn.execute(
                "UPDATE stream_sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
                (now, session_id)
            )
            if row:
                conn.execute(
                    "UPDATE voice_sessions SET is_screen_sharing = 0 WHERE channel_id = ? AND user_id = ? AND left_at IS NULL",
                    (row["channel_id"], row["user_id"])
                )
            return cur.rowcount > 0

    def end_active_streams_for_user(self, channel_id: str, user_id: str) -> int:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            cur = conn.execute(
                "UPDATE stream_sessions SET ended_at = ? WHERE channel_id = ? AND user_id = ? AND ended_at IS NULL",
                (now, channel_id, user_id)
            )
            conn.execute(
                "UPDATE voice_sessions SET is_screen_sharing = 0 WHERE channel_id = ? AND user_id = ? AND left_at IS NULL",
                (channel_id, user_id)
            )
            return cur.rowcount

    # =========================================================================
    # MODERACIÓN, REPORTES Y AUDITORÍA
    # =========================================================================

    def create_moderation_action(
        self,
        action_id: str,
        community_id: str,
        actor_id: str,
        target_id: str,
        action: str,
        reason: Optional[str] = None,
        expires_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO moderation_actions (
                    id, community_id, actor_id, target_id, action, reason, expires_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (action_id, community_id, actor_id, target_id, action, reason, expires_at, now)
            )
        return {
            "id": action_id,
            "community_id": community_id,
            "actor_id": actor_id,
            "target_id": target_id,
            "action": action,
            "reason": reason,
            "expires_at": expires_at,
            "created_at": now,
        }

    def list_moderation_actions(
        self,
        community_id: str,
        target_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        query = "SELECT * FROM moderation_actions WHERE community_id = ?"
        params: List[Any] = [community_id]
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def is_user_banned(self, community_id: str, user_id: str) -> bool:
        """Verifica si el usuario tiene una sanción de ban activa no revocada y vigente."""
        conn = self._get_connection()
        now = time.time()
        # Buscar la acción más reciente entre 'ban' y 'unban'
        row = conn.execute(
            """
            SELECT action, expires_at FROM moderation_actions
            WHERE community_id = ? AND target_id = ? AND action IN ('ban', 'unban')
            ORDER BY created_at DESC LIMIT 1
            """,
            (community_id, user_id)
        ).fetchone()
        if not row:
            return False
        if row["action"] == "unban":
            return False
        # Si es 'ban', verificar si expiró
        exp = row["expires_at"]
        if exp is not None and exp < now:
            return False
        return True

    def is_user_muted(self, community_id: str, user_id: str) -> bool:
        """Verifica si el usuario tiene una sanción de mute activa no revocada y vigente."""
        conn = self._get_connection()
        now = time.time()
        row = conn.execute(
            """
            SELECT action, expires_at FROM moderation_actions
            WHERE community_id = ? AND target_id = ? AND action IN ('mute', 'unmute')
            ORDER BY created_at DESC LIMIT 1
            """,
            (community_id, user_id)
        ).fetchone()
        if not row:
            return False
        if row["action"] == "unmute":
            return False
        exp = row["expires_at"]
        if exp is not None and exp < now:
            return False
        return True

    def create_report(
        self,
        report_id: str,
        community_id: str,
        reporter_id: str,
        target_type: str,
        target_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO reports (
                    id, community_id, reporter_id, target_type, target_id,
                    reason, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (report_id, community_id, reporter_id, target_type, target_id, reason, now)
            )
        return self.get_report(report_id)

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ?",
            (report_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_reports(
        self,
        community_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        query = "SELECT * FROM reports WHERE community_id = ?"
        params: List[Any] = [community_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def resolve_report(
        self,
        report_id: str,
        resolver_id: str,
        status: str = "resolved",
        resolution_notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                UPDATE reports
                SET status = ?, resolved_by = ?, resolution_notes = ?, resolved_at = ?
                WHERE id = ?
                """,
                (status, resolver_id, resolution_notes, now, report_id)
            )
        return self.get_report(report_id)

    def create_audit_entry(
        self,
        entry_id: str,
        community_id: str,
        actor_id: str,
        action_type: str,
        target_id: Optional[str] = None,
        details_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = self._get_connection()
        now = time.time()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    id, community_id, actor_id, action_type, target_id, details_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_id, community_id, actor_id, action_type, target_id, details_json, now)
            )
        return {
            "id": entry_id,
            "community_id": community_id,
            "actor_id": actor_id,
            "action_type": action_type,
            "target_id": target_id,
            "details_json": details_json,
            "created_at": now,
        }

    def list_audit_entries(
        self,
        community_id: str,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        query = "SELECT * FROM audit_log WHERE community_id = ?"
        params: List[Any] = [community_id]
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    # =========================================================================
    # ADJUNTOS EN ESPERA, ACTIVIDAD DE JUEGOS Y NOTIFICACIONES
    # =========================================================================

    def stage_attachment(
        self,
        attachment_id: str,
        channel_id: str,
        uploader_id: str,
        storage_key: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        checksum_sha256: str,
    ) -> Dict[str, Any]:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO staged_attachments (
                    id, channel_id, uploader_id, storage_key, filename, content_type, size_bytes, checksum_sha256, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (attachment_id, channel_id, uploader_id, storage_key, filename, content_type, size_bytes, checksum_sha256, now),
            )
        return {
            "id": attachment_id,
            "channel_id": channel_id,
            "uploader_id": uploader_id,
            "storage_key": storage_key,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "checksum_sha256": checksum_sha256,
            "created_at": now,
        }

    def consume_staged_attachment(self, attachment_id: str, channel_id: str, uploader_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        with self._tx_lock, conn:
            row = conn.execute(
                "SELECT * FROM staged_attachments WHERE id = ? AND channel_id = ? AND uploader_id = ?",
                (attachment_id, channel_id, uploader_id),
            ).fetchone()
            if not row:
                return None
            conn.execute("DELETE FROM staged_attachments WHERE id = ?", (attachment_id,))
            return dict(row)

    def record_activity_event(
        self,
        user_id: str,
        event_type: str,
        game_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata_json: Optional[str] = None,
        visibility: str = "communities",
    ) -> Dict[str, Any]:
        ev_id = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO activity_events (id, user_id, event_type, game_id, title, metadata_json, visibility, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ev_id, user_id, event_type, game_id, title, metadata_json, visibility, now),
            )
        return {
            "id": ev_id,
            "user_id": user_id,
            "event_type": event_type,
            "game_id": game_id,
            "title": title,
            "metadata_json": metadata_json,
            "visibility": visibility,
            "created_at": now,
        }

    def list_activity_events(self, user_ids: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        if not user_ids:
            return []
        conn = self._get_connection()
        placeholders = ",".join("?" for _ in user_ids)
        rows = conn.execute(
            f"""
            SELECT * FROM activity_events
            WHERE user_id IN ({placeholders})
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*user_ids, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def create_notification(
        self,
        user_id: str,
        kind: str,
        title: str,
        body: Optional[str] = None,
        actor_id: Optional[str] = None,
        community_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        nid = str(uuid.uuid4())
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO user_notifications (
                    id, user_id, kind, actor_id, community_id, channel_id, message_id, title, body, is_read, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (nid, user_id, kind, actor_id, community_id, channel_id, message_id, title, body, now),
            )
        return {
            "id": nid,
            "user_id": user_id,
            "kind": kind,
            "actor_id": actor_id,
            "community_id": community_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "title": title,
            "body": body,
            "is_read": False,
            "created_at": now,
        }

    def list_notifications(self, user_id: str, unread_only: bool = False, limit: int = 40) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        sql = "SELECT * FROM user_notifications WHERE user_id = ?"
        if unread_only:
            sql += " AND is_read = 0"
        sql += " ORDER BY created_at DESC LIMIT ?"
        rows = conn.execute(sql, (user_id, limit)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["is_read"] = bool(d.get("is_read"))
            out.append(d)
        return out

    def mark_notifications_read(self, user_id: str, notification_ids: Optional[List[str]] = None) -> int:
        conn = self._get_connection()
        with self._tx_lock, conn:
            if notification_ids:
                placeholders = ",".join("?" for _ in notification_ids)
                cur = conn.execute(
                    f"UPDATE user_notifications SET is_read = 1 WHERE user_id = ? AND id IN ({placeholders})",
                    (user_id, *notification_ids),
                )
            else:
                cur = conn.execute("UPDATE user_notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
            return cur.rowcount

    # =========================================================================
    # INTEGRACIÓN SPOTIFY OAUTH OPT-IN / REVOCABLE (P2)
    # =========================================================================

    def create_spotify_oauth_state(
        self,
        state: str,
        user_id: str,
        redirect_uri: str,
        scopes: str,
        share_presence: bool = True,
        code_challenge: Optional[str] = None,
        ttl_seconds: float = 600.0,
    ) -> Dict[str, Any]:
        now = time.time()
        expires_at = now + max(30.0, float(ttl_seconds))
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute("DELETE FROM spotify_oauth_states WHERE expires_at < ? OR consumed = 1", (now - 3600.0,))
            conn.execute(
                """
                INSERT INTO spotify_oauth_states (
                    state, user_id, redirect_uri, scopes, share_presence, code_challenge, created_at, expires_at, consumed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (state, user_id, redirect_uri, scopes, 1 if share_presence else 0, code_challenge, now, expires_at),
            )
        return {
            "state": state,
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "share_presence": bool(share_presence),
            "code_challenge": code_challenge,
            "created_at": now,
            "expires_at": expires_at,
        }

    def consume_spotify_oauth_state(self, state: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            row = conn.execute("SELECT * FROM spotify_oauth_states WHERE state = ?", (state,)).fetchone()
            if not row:
                return None
            rec = dict(row)
            if rec.get("consumed"):
                return None
            if float(rec.get("expires_at") or 0) < now:
                return None
            if user_id is not None and str(rec.get("user_id")) != str(user_id):
                return None
            cur = conn.execute(
                "UPDATE spotify_oauth_states SET consumed = 1 WHERE state = ? AND consumed = 0",
                (state,),
            )
            if cur.rowcount != 1:
                return None
            rec["consumed"] = True
            rec["share_presence"] = bool(rec.get("share_presence"))
            return rec

    def upsert_spotify_connection(
        self,
        user_id: str,
        spotify_user_id: Optional[str],
        display_name: Optional[str],
        scopes: str,
        token_ciphertext: str,
        expires_at: Optional[float],
        opt_in_enabled: bool = True,
        share_presence: bool = True,
    ) -> Dict[str, Any]:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            conn.execute(
                """
                INSERT INTO spotify_connections (
                    user_id, spotify_user_id, display_name, scopes, token_ciphertext,
                    expires_at, opt_in_enabled, share_presence, current_track, current_artist,
                    connected_at, updated_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, NULL)
                ON CONFLICT(user_id) DO UPDATE SET
                    spotify_user_id = excluded.spotify_user_id,
                    display_name = excluded.display_name,
                    scopes = excluded.scopes,
                    token_ciphertext = excluded.token_ciphertext,
                    expires_at = excluded.expires_at,
                    opt_in_enabled = excluded.opt_in_enabled,
                    share_presence = excluded.share_presence,
                    connected_at = COALESCE(spotify_connections.connected_at, excluded.connected_at),
                    updated_at = excluded.updated_at,
                    revoked_at = NULL
                """,
                (
                    user_id,
                    spotify_user_id,
                    display_name,
                    scopes,
                    token_ciphertext,
                    expires_at,
                    1 if opt_in_enabled else 0,
                    1 if share_presence else 0,
                    now,
                    now,
                ),
            )
        return self.get_spotify_connection(user_id) or {}

    def get_spotify_connection(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM spotify_connections WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["opt_in_enabled"] = bool(d.get("opt_in_enabled"))
        d["share_presence"] = bool(d.get("share_presence"))
        return d

    def update_spotify_connection_state(
        self,
        user_id: str,
        opt_in_enabled: Optional[bool] = None,
        share_presence: Optional[bool] = None,
        token_ciphertext: Optional[str] = None,
        expires_at: Optional[float] = None,
        current_track: Any = ...,
        current_artist: Any = ...,
    ) -> Optional[Dict[str, Any]]:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            row = conn.execute("SELECT * FROM spotify_connections WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            cur = dict(row)
            new_opt = (1 if opt_in_enabled else 0) if opt_in_enabled is not None else cur["opt_in_enabled"]
            new_share = (1 if share_presence else 0) if share_presence is not None else cur["share_presence"]
            new_ct = token_ciphertext if token_ciphertext is not None else cur["token_ciphertext"]
            new_exp = expires_at if expires_at is not None else cur["expires_at"]
            new_track = cur["current_track"] if current_track is ... else current_track
            new_artist = cur["current_artist"] if current_artist is ... else current_artist
            conn.execute(
                """
                UPDATE spotify_connections
                SET opt_in_enabled = ?,
                    share_presence = ?,
                    token_ciphertext = ?,
                    expires_at = ?,
                    current_track = ?,
                    current_artist = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (new_opt, new_share, new_ct, new_exp, new_track, new_artist, now, user_id),
            )
        return self.get_spotify_connection(user_id)

    def revoke_spotify_connection(self, user_id: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        conn = self._get_connection()
        with self._tx_lock, conn:
            row = conn.execute("SELECT * FROM spotify_connections WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE spotify_connections
                SET token_ciphertext = NULL,
                    expires_at = NULL,
                    opt_in_enabled = 0,
                    share_presence = 0,
                    current_track = NULL,
                    current_artist = NULL,
                    revoked_at = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (now, now, user_id),
            )
            conn.execute("UPDATE spotify_oauth_states SET consumed = 1 WHERE user_id = ?", (user_id,))
        return self.get_spotify_connection(user_id)
