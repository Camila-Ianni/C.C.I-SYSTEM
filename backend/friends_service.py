"""
backend/friends_service.py - Servicio de gestión de Amigos, Grupos, Roles y Presencia.
Implementa las reglas de negocio de la Fase 2 (Módulo B) para C.C.I. SYSTEM.
"""
from __future__ import annotations

import secrets
import time
from enum import Enum
from typing import Any, Dict, List, Optional
import cci_database


class PresenceStatus(str, Enum):
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


class GroupRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class FriendsService:
    """Servicio desacoplado para amistades, presencia en tiempo real y grupos de amigos."""

    _instance: Optional[FriendsService] = None

    @classmethod
    def get_instance(cls) -> FriendsService:
        if cls._instance is None:
            cls._instance = FriendsService()
        return cls._instance

    def __init__(self):
        # Cache de presencia en memoria: user_id -> {"status": PresenceStatus, "game": Optional[str], "last_seen": float}
        self._presence: Dict[str, Dict[str, Any]] = {}

    # ==============================================================================
    # 1. GESTIÓN DE PRESENCIA
    # ==============================================================================

    def update_presence(self, user_id: str, status: str = "online", current_game: Optional[str] = None) -> Dict[str, Any]:
        """Actualiza la presencia persistida (unificada con CommunitiesRepository SQLite WAL)."""
        valid_status = status.lower() if status.lower() in ("online", "away", "busy", "idle", "dnd", "invisible", "offline") else "online"
        repo_status = {"away": "idle", "busy": "dnd"}.get(valid_status, valid_status)
        try:
            from backend.communities.repository import CommunitiesRepository
            repo = CommunitiesRepository.get_instance()
            repo.set_presence(
                user_id=user_id,
                status=repo_status,
                custom_status=current_game,
                activity_type="playing" if current_game else None,
                activity_title=current_game,
                preserve_activity=False,
            )
        except Exception:
            pass
        data = {
            "user_id": user_id,
            "status": valid_status,
            "current_game": current_game,
            "last_seen": time.time(),
        }
        self._presence[user_id] = data
        return data

    def get_presence(self, user_id: str) -> Dict[str, Any]:
        """Retorna la presencia persistida con expiración TTL o 'offline' por defecto."""
        try:
            from backend.communities.repository import CommunitiesRepository
            p = CommunitiesRepository.get_instance().get_presence(user_id)
            st = str(p.get("status") or "offline")
            legacy_st = {"idle": "away", "dnd": "busy"}.get(st, st)
            if legacy_st == "invisible":
                legacy_st = "offline"
            hide_activity = (legacy_st == "offline") or (p.get("activity_visibility") == "private")
            game = None if hide_activity else (p.get("activity_title") or p.get("custom_status"))
            return {
                "user_id": user_id,
                "status": legacy_st,
                "current_game": game,
                "activity_type": None if hide_activity else p.get("activity_type"),
                "activity_game_id": None if hide_activity else p.get("activity_game_id"),
                "last_seen": float(p.get("last_seen") or 0.0),
            }
        except Exception:
            return self._presence.get(user_id, {
                "user_id": user_id,
                "status": PresenceStatus.OFFLINE.value,
                "current_game": None,
                "last_seen": 0.0,
            })

    # ==============================================================================
    # 2. GESTIÓN DE AMISTADES Y SOLICITUDES
    # ==============================================================================

    def send_friend_request(self, requester_id: str, addressee_id: str) -> Dict[str, Any]:
        """Envía una solicitud de amistad validando que no sean la misma persona ni estén bloqueados."""
        if requester_id == addressee_id:
            return {"success": False, "error": "No puedes enviarte una solicitud a ti mismo."}

        # Comprobar si existe relación previa
        friends = cci_database.get_user_friends(requester_id)
        if any(f["requester_id"] == addressee_id or f["addressee_id"] == addressee_id for f in friends):
            return {"success": False, "error": "Ya son amigos."}

        # Comprobar bloqueos
        with cci_database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM friendships
                WHERE (requester_id = ? AND addressee_id = ?)
                   OR (requester_id = ? AND addressee_id = ?)
            """, (requester_id, addressee_id, addressee_id, requester_id))
            row = cursor.fetchone()
            if row and row["status"] == "blocked":
                return {"success": False, "error": "No es posible enviar la solicitud de amistad."}

        ok = cci_database.record_friendship_request(requester_id, addressee_id)
        return {"success": ok, "message": "Solicitud de amistad enviada con éxito."}

    def accept_friend_request(self, user_id: str, requester_id: str) -> Dict[str, Any]:
        """Acepta una solicitud de amistad pendiente recibida."""
        ok = cci_database.update_friendship_status(requester_id, user_id, "accepted")
        if ok:
            return {"success": True, "message": "Solicitud de amistad aceptada."}
        return {"success": False, "error": "No se encontró la solicitud de amistad pendiente."}

    def reject_friend_request(self, user_id: str, requester_id: str) -> Dict[str, Any]:
        """Rechaza una solicitud de amistad pendiente."""
        ok = cci_database.update_friendship_status(requester_id, user_id, "rejected")
        if ok:
            return {"success": True, "message": "Solicitud de amistad rechazada."}
        return {"success": False, "error": "No se encontró la solicitud de amistad."}

    def cancel_friend_request(self, user_id: str, addressee_id: str) -> Dict[str, Any]:
        """Cancela una solicitud saliente que aún no fue aceptada."""
        ok = cci_database.cancel_friendship_request(user_id, addressee_id)
        if ok:
            return {"success": True, "message": "Solicitud cancelada correctamente."}
        return {"success": False, "error": "No se encontró la solicitud saliente."}

    def block_user(self, user_id: str, target_id: str) -> Dict[str, Any]:
        """Bloquea a un usuario impidiendo interacciones futuras."""
        ok = cci_database.update_friendship_status(user_id, target_id, "blocked")
        if not ok:
            with cci_database.get_db() as conn:
                cursor = conn.cursor()
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
                cursor.execute("""
                    INSERT INTO friendships (requester_id, addressee_id, status, created_at, updated_at)
                    VALUES (?, ?, 'blocked', ?, ?)
                """, (user_id, target_id, now_iso, now_iso))
        return {"success": True, "message": f"Usuario {target_id} bloqueado."}

    def get_friends_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtiene la lista de amigos con su estado de presencia en tiempo real y nombre real."""
        raw_friends = cci_database.get_user_friends(user_id)
        fids = [
            f["addressee_id"] if f["requester_id"] == user_id else f["requester_id"]
            for f in raw_friends
        ]
        names: Dict[str, str] = {}
        numeric = [int(x) for x in fids if str(x).isdigit()]
        if numeric:
            try:
                with cci_database.get_db() as conn:
                    ph = ",".join("?" for _ in numeric)
                    for r in conn.execute(f"SELECT id, username FROM accounts WHERE id IN ({ph})", numeric).fetchall():
                        names[str(r["id"])] = str(r["username"])
            except Exception:
                pass
        result = []
        for f in raw_friends:
            friend_id = f["addressee_id"] if f["requester_id"] == user_id else f["requester_id"]
            presence = self.get_presence(friend_id)
            result.append({
                "friend_id": friend_id,
                "username": names.get(str(friend_id), str(friend_id)),
                "status": f["status"],
                "since": f["updated_at"],
                "presence": presence["status"],
                "current_game": presence["current_game"],
                "activity_type": presence.get("activity_type"),
                "activity_game_id": presence.get("activity_game_id"),
            })
        return result

    # ==============================================================================
    # 3. GESTIÓN DE GRUPOS Y CONTROL DE ACCESO BASADO EN ROLES (RBAC)
    # ==============================================================================

    def create_group(self, name: str, owner_id: str, avatar: Optional[str] = None, visibility: str = "private") -> Dict[str, Any]:
        """Crea un nuevo grupo y asigna al creador como 'owner'."""
        if not name or len(name.strip()) < 3:
            return {"success": False, "error": "El nombre del grupo debe tener al menos 3 caracteres."}

        group_id = f"grp_{secrets.token_hex(4)}"
        grp = cci_database.create_group_entry(group_id, name.strip(), owner_id, avatar, visibility)
        return {"success": True, "group": grp}

    def get_group_info(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el detalle completo del grupo y miembros."""
        return cci_database.get_group_detail(group_id)

    def invite_member(self, group_id: str, actor_id: str, target_user_id: str) -> Dict[str, Any]:
        """Invita o añade a un miembro al grupo. Solo owner y admin pueden invitar."""
        grp = cci_database.get_group_detail(group_id)
        if not grp:
            return {"success": False, "error": "El grupo no existe."}

        # Comprobar permisos del actor
        actor_member = next((m for m in grp["members"] if m["user_id"] == actor_id), None)
        if not actor_member or actor_member["role"] not in (GroupRole.OWNER.value, GroupRole.ADMIN.value):
            return {"success": False, "error": "No tienes permisos de administrador para invitar miembros."}

        # Comprobar si ya es miembro
        if any(m["user_id"] == target_user_id for m in grp["members"]):
            return {"success": False, "error": "El usuario ya es miembro de este grupo."}

        ok = cci_database.add_group_member_entry(group_id, target_user_id, role=GroupRole.MEMBER.value)
        return {"success": ok, "message": f"Usuario {target_user_id} añadido al grupo."}

    def kick_member(self, group_id: str, actor_id: str, target_user_id: str) -> Dict[str, Any]:
        """Expulsa a un miembro del grupo con validación estricta de jerarquía."""
        grp = cci_database.get_group_detail(group_id)
        if not grp:
            return {"success": False, "error": "El grupo no existe."}

        actor_member = next((m for m in grp["members"] if m["user_id"] == actor_id), None)
        target_member = next((m for m in grp["members"] if m["user_id"] == target_user_id), None)

        if not actor_member or not target_member:
            return {"success": False, "error": "Miembro no encontrado en el grupo."}

        # Reglas de expulsión:
        # 1. No se puede auto-expulsar (debe usar leave_group)
        if actor_id == target_user_id:
            return {"success": False, "error": "Para salir del grupo utiliza la opción de abandonar."}
        # 2. El owner puede expulsar a cualquiera
        # 3. El admin solo puede expulsar a members (no al owner ni a otros admins)
        if actor_member["role"] == GroupRole.ADMIN.value:
            if target_member["role"] in (GroupRole.OWNER.value, GroupRole.ADMIN.value):
                return {"success": False, "error": "Los administradores no pueden expulsar al dueño ni a otros administradores."}
        elif actor_member["role"] != GroupRole.OWNER.value:
            return {"success": False, "error": "No tienes permisos para expulsar miembros."}

        ok = cci_database.remove_group_member_entry(group_id, target_user_id)
        return {"success": ok, "message": f"Miembro {target_user_id} expulsado del grupo."}

    def leave_group(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """Abandona el grupo. Si el dueño sale y quedan miembros, se transfiere automáticamente la propiedad."""
        grp = cci_database.get_group_detail(group_id)
        if not grp:
            return {"success": False, "error": "El grupo no existe."}

        member = next((m for m in grp["members"] if m["user_id"] == user_id), None)
        if not member:
            return {"success": False, "error": "No eres miembro de este grupo."}

        # Si el dueño se va:
        if member["role"] == GroupRole.OWNER.value:
            other_members = [m for m in grp["members"] if m["user_id"] != user_id]
            if other_members:
                # Priorizar admin, o el miembro más antiguo
                next_owner = next((m for m in other_members if m["role"] == GroupRole.ADMIN.value), other_members[0])
                cci_database.transfer_group_ownership_entry(group_id, next_owner["user_id"])
            else:
                # Si no queda nadie, borrar el grupo
                with cci_database.get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))

        cci_database.remove_group_member_entry(group_id, user_id)
        return {"success": True, "message": "Has abandonado el grupo con éxito."}

    def transfer_ownership(self, group_id: str, actor_id: str, new_owner_id: str) -> Dict[str, Any]:
        """Transfiere la titularidad del grupo. Solo el owner actual puede realizarlo."""
        grp = cci_database.get_group_detail(group_id)
        if not grp:
            return {"success": False, "error": "El grupo no existe."}

        if grp["owner_id"] != actor_id:
            return {"success": False, "error": "Solo el propietario actual puede transferir el grupo."}

        if actor_id == new_owner_id:
            return {"success": False, "error": "Ya eres el propietario del grupo."}

        ok = cci_database.transfer_group_ownership_entry(group_id, new_owner_id)
        if ok:
            # Degradar al actor anterior a admin
            cci_database.update_group_member_role_entry(group_id, actor_id, GroupRole.ADMIN.value)
            return {"success": True, "message": f"Propiedad transferida con éxito a {new_owner_id}."}
        return {"success": False, "error": "El nuevo propietario debe ser miembro del grupo."}

    def update_role(self, group_id: str, actor_id: str, target_user_id: str, new_role: str) -> Dict[str, Any]:
        """Promociona o degrada el rol de un miembro ('admin', 'member'). Solo el owner puede modificar roles."""
        grp = cci_database.get_group_detail(group_id)
        if not grp or grp["owner_id"] != actor_id:
            return {"success": False, "error": "Solo el propietario del grupo puede modificar los roles de miembros."}

        if new_role not in (GroupRole.ADMIN.value, GroupRole.MEMBER.value):
            return {"success": False, "error": "Rol inválido (debe ser admin o member)."}

        ok = cci_database.update_group_member_role_entry(group_id, target_user_id, new_role)
        return {"success": ok, "message": f"Rol de {target_user_id} actualizado a {new_role}."}
