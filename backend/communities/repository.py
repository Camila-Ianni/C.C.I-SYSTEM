"""
backend/communities/repository.py - Capa de persistencia relacional para CCI Communities.

Implementa el almacenamiento y operaciones sobre el esquema relacional definido en Fase 0:
comunidades, miembros, roles, permisos, canales, sobrescrituras e invitaciones.
Compatible con entornos de prueba herméticos (SQLite/Memoria) y despliegues PostgreSQL.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional
import uuid


class CommunitiesRepository:
    """Repositorio de base de datos relacional para comunidades, canales, roles e invitaciones."""

    _instance: Optional[CommunitiesRepository] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or ":memory:"
        self._local = threading.local()
        self._init_schema()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> CommunitiesRepository:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    def close(self) -> None:
        """Cierra de forma limpia la conexión de base de datos del hilo actual."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    @classmethod
    def reset_instance(cls, db_path: Optional[str] = None) -> CommunitiesRepository:
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = cls(db_path)
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self) -> None:
        conn = self._get_connection()
        with conn:
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
            """)

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
        with conn:
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
        with conn:
            conn.execute(f"UPDATE communities SET {clause} WHERE id = ? AND deleted_at IS NULL", values)
        return self.get_community(community_id)

    def delete_community(self, community_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with conn:
            cur = conn.execute(
                "UPDATE communities SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (now, community_id)
            )
            return cur.rowcount > 0

    def transfer_ownership(self, community_id: str, new_owner_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with conn:
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
        with conn:
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
        with conn:
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
        with conn:
            cur = conn.execute("DELETE FROM roles WHERE id = ? AND is_default = 0", (role_id,))
            return cur.rowcount > 0

    # =========================================================================
    # MIEMBROS Y ASIGNACIÓN DE ROLES
    # =========================================================================

    def add_member(self, community_id: str, user_id: str, nickname: Optional[str] = None) -> bool:
        now = time.time()
        conn = self._get_connection()
        with conn:
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
        with conn:
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
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO member_roles (community_id, user_id, role_id) VALUES (?, ?, ?)",
                (community_id, user_id, role_id)
            )
        return True

    def remove_role_from_member(self, community_id: str, user_id: str, role_id: str) -> bool:
        conn = self._get_connection()
        with conn:
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
        with conn:
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
        with conn:
            conn.execute(f"UPDATE channels SET {clause} WHERE id = ? AND deleted_at IS NULL", list(updates.values()) + [channel_id])
        return self.get_channel(channel_id)

    def delete_channel(self, channel_id: str) -> bool:
        now = time.time()
        conn = self._get_connection()
        with conn:
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
        with conn:
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
        with conn:
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
        with conn:
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
