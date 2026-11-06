"""
backend/communities/service.py - Servicio de lógica de negocio y autorización para CCI Communities.

Implementa las reglas de producto de la Fase 1:
- Ciclo de vida de comunidades (creación con @everyone y #general, edición, borrado, transferencia de propiedad).
- Jerarquía de roles y motor de resolución de permisos fail-closed (Sección 5.2).
- Gestión de miembros (invitaciones, incorporación, expulsión jerárquica, abandono seguro).
- Canales públicos y privados con sobrescrituras de permisos.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from backend.communities.repository import CommunitiesRepository


class CommunitiesService:
    """Servicio soberano para la administración de comunidades, roles y canales."""

    _instance: Optional[CommunitiesService] = None

    def __init__(self, repo: Optional[CommunitiesRepository] = None):
        self._repo = repo

    @property
    def repo(self) -> CommunitiesRepository:
        if self._repo is not None:
            return self._repo
        return CommunitiesRepository.get_instance()

    @classmethod
    def get_instance(cls, repo: Optional[CommunitiesRepository] = None) -> CommunitiesService:
        if cls._instance is None or repo is not None:
            cls._instance = cls(repo)
        return cls._instance

    # =========================================================================
    # MOTOR DE RESOLUCIÓN DE PERMISOS (SECCIÓN 5.2)
    # =========================================================================

    def get_user_highest_role_position(self, community_id: str, user_id: str) -> int:
        """Retorna la posición más alta (menor valor numérico) de los roles asignados al usuario."""
        comm = self.repo.get_community(community_id)
        if not comm:
            return 999999
        if comm["owner_id"] == user_id:
            return -1  # Propietario tiene rango supremo

        member = self.repo.get_member(community_id, user_id)
        if not member or not member.get("roles"):
            return 999999

        return min(r["position"] for r in member["roles"])

    def has_permission(
        self,
        community_id: str,
        user_id: str,
        permission_id: str,
        channel_id: Optional[str] = None
    ) -> bool:
        """
        Evalúa jerárquicamente si un usuario tiene un permiso específico.
        Reglas:
        1. Propietario (owner_id) -> ALLOW total.
        2. Rol con is_admin=True -> ALLOW total.
        3. Conjunto de permisos base acumulado de todos sus roles.
        4. Sobrescrituras a nivel de canal (para usuario y para roles).
        5. Denegación estricta por defecto (Fail-closed).
        """
        comm = self.repo.get_community(community_id)
        if not comm:
            return False

        # 1. Propietario absoluto
        if comm["owner_id"] == user_id:
            return True

        member = self.repo.get_member(community_id, user_id)
        if not member or member.get("status") != "active":
            return False

        user_roles = member.get("roles", [])

        # 2. Administrador total
        if any(r.get("is_admin") for r in user_roles):
            return True

        # 3. Permisos base de los roles
        base_allowed = False
        for r in user_roles:
            role_obj = self.repo.get_role(r["id"])
            if role_obj and permission_id in role_obj.get("permissions", []):
                base_allowed = True
                break

        # 4. Sobrescrituras por canal (si aplica)
        if channel_id:
            chan = self.repo.get_channel(channel_id)
            if not chan:
                return False

            overrides = self.repo.get_channel_overrides(channel_id)

            # 4a. Sobrescritura específica para el usuario
            for ov in overrides:
                if ov["target_type"] == "user" and ov["target_id"] == user_id and ov["permission_id"] == permission_id:
                    if ov["deny"]:
                        return False
                    if ov["allow"]:
                        return True

            # 4b. Sobrescritura para los roles del usuario
            role_ids = {r["id"] for r in user_roles}
            has_role_allow = False
            has_role_deny = False
            for ov in overrides:
                if ov["target_type"] == "role" and ov["target_id"] in role_ids and ov["permission_id"] == permission_id:
                    if ov["deny"]:
                        has_role_deny = True
                    if ov["allow"]:
                        has_role_allow = True

            if has_role_deny and not has_role_allow:
                return False
            if has_role_allow:
                return True

            # Si el canal es privado y se busca leer/conectar sin allow explícito
            if chan.get("is_private") and permission_id in ("messages.read", "voice.connect"):
                return base_allowed and has_role_allow

        return base_allowed

    # =========================================================================
    # COMUNIDADES
    # =========================================================================

    def create_community(
        self,
        owner_id: str,
        name: str,
        description: Optional[str] = None,
        visibility: str = "private",
        slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Crea una nueva comunidad inicializando rol @everyone y canales base."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El nombre de la comunidad no puede estar vacío")

        if not slug:
            base_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", clean_name.lower())[:32].strip("-")
            slug = base_slug or "community"

        # Asegurar unicidad de slug
        counter = 1
        orig_slug = slug
        while self.repo.get_community_by_slug(slug):
            slug = f"{orig_slug}-{counter}"
            counter += 1

        comm = self.repo.create_community(
            owner_id=owner_id,
            name=clean_name,
            slug=slug,
            description=description,
            visibility=visibility,
        )
        comm_id = comm["id"]

        # 1. Rol por defecto @everyone (posición más baja = 1000)
        default_perms = [
            "community.view",
            "messages.read",
            "messages.send",
            "voice.connect",
            "voice.speak",
            "soundboard.play",
        ]
        self.repo.create_role(
            community_id=comm_id,
            name="@everyone",
            color="#99AAB5",
            position=1000,
            is_default=True,
            is_admin=False,
            permissions=default_perms,
        )

        # 2. Canales iniciales por defecto
        self.repo.create_channel(
            community_id=comm_id,
            name="general",
            channel_type="text",
            topic="Canal de conversación general",
            position=0,
        )
        self.repo.create_channel(
            community_id=comm_id,
            name="General Voice",
            channel_type="voice",
            topic="Sala de voz general",
            position=1,
        )

        return comm

    def get_community(self, community_id: str, requester_id: str) -> Optional[Dict[str, Any]]:
        """Consulta información de una comunidad respetando privacidad pública/privada."""
        comm = self.repo.get_community(community_id)
        if not comm:
            return None

        # Si es privada, exige ser miembro o propietario
        if comm["visibility"] == "private":
            member = self.repo.get_member(community_id, requester_id)
            if not member and comm["owner_id"] != requester_id:
                return None  # No autorizado a ver comunidad privada

        res = dict(comm)
        res["channels"] = self.list_channels(community_id, requester_id)
        res["roles"] = self.repo.list_roles(community_id)
        res["member_count"] = len(self.repo.list_members(community_id))
        return res

    def list_communities(self, requester_id: str, discover_public: bool = False) -> List[Dict[str, Any]]:
        """Lista comunidades del usuario o comunidades públicas descubribles."""
        if discover_public:
            return self.repo.list_public_communities()
        return self.repo.list_communities_for_user(requester_id)

    def update_community(self, community_id: str, requester_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Modifica ajustes de la comunidad verificando permiso community.manage."""
        if not self.has_permission(community_id, requester_id, "community.manage"):
            raise PermissionError("Acceso denegado: se requiere permiso community.manage")
        updated = self.repo.update_community(community_id, fields)
        if not updated:
            raise LookupError("Comunidad no encontrada")
        return updated

    def delete_community(self, community_id: str, requester_id: str) -> bool:
        """Eliminación lógica de comunidad (restringido estrictamente al propietario)."""
        comm = self.repo.get_community(community_id)
        if not comm:
            raise LookupError("Comunidad no encontrada")
        if comm["owner_id"] != requester_id:
            raise PermissionError("Solo el propietario puede eliminar la comunidad")
        return self.repo.delete_community(community_id)

    def transfer_ownership(self, community_id: str, requester_id: str, new_owner_id: str) -> bool:
        """Transfiere la propiedad soberana de la comunidad a otro miembro activo."""
        comm = self.repo.get_community(community_id)
        if not comm:
            raise LookupError("Comunidad no encontrada")
        if comm["owner_id"] != requester_id:
            raise PermissionError("Solo el propietario actual puede transferir la comunidad")

        target_member = self.repo.get_member(community_id, new_owner_id)
        if not target_member or target_member.get("status") != "active":
            raise ValueError("El nuevo propietario debe ser un miembro activo de la comunidad")

        return self.repo.transfer_ownership(community_id, new_owner_id)

    # =========================================================================
    # INVITACIONES Y MIEMBROS
    # =========================================================================

    def create_invitation(
        self,
        community_id: str,
        requester_id: str,
        max_uses: int = 0,
        expires_in_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Genera un código de invitación único validando permiso community.invites.create."""
        if not self.has_permission(community_id, requester_id, "community.invites.create"):
            raise PermissionError("Se requiere permiso community.invites.create")
        return self.repo.create_invitation(community_id, requester_id, max_uses, expires_in_hours)

    def join_via_invitation(self, code: str, user_id: str) -> Dict[str, Any]:
        """Procesa el ingreso de un usuario a la comunidad consumiendo la invitación."""
        inv = self.repo.get_invitation_by_code(code)
        if not inv:
            raise LookupError("Invitación no válida o expirada")

        comm = self.repo.get_community(inv["community_id"])
        if not comm:
            raise LookupError("Comunidad asociada no existe")

        # Comprobar límite de miembros
        current_members = len(self.repo.list_members(comm["id"]))
        if current_members >= comm["max_members"]:
            raise ValueError("La comunidad ha alcanzado su límite máximo de miembros")

        consumed = self.repo.consume_invitation(code)
        if not consumed:
            raise LookupError("Invitación no válida o expirada")

        self.repo.add_member(comm["id"], user_id)
        return {"community": comm, "member": self.repo.get_member(comm["id"], user_id)}

    def kick_member(self, community_id: str, requester_id: str, target_user_id: str) -> bool:
        """Expulsa a un miembro respetando la jerarquía de roles."""
        if not self.has_permission(community_id, requester_id, "community.members.kick"):
            raise PermissionError("Se requiere permiso community.members.kick")

        comm = self.repo.get_community(community_id)
        if not comm:
            raise LookupError("Comunidad no encontrada")
        if target_user_id == comm["owner_id"]:
            raise PermissionError("No es posible expulsar al propietario de la comunidad")

        # Comprobación de jerarquía: requester no puede expulsar a alguien con rol superior o igual
        req_pos = self.get_user_highest_role_position(community_id, requester_id)
        target_pos = self.get_user_highest_role_position(community_id, target_user_id)
        if req_pos >= target_pos and comm["owner_id"] != requester_id:
            raise PermissionError("Jerarquía insuficiente para expulsar a este miembro")

        return self.repo.remove_member(community_id, target_user_id)

    def leave_community(self, community_id: str, user_id: str) -> bool:
        """Permite abandonar una comunidad; el propietario debe transferirla antes."""
        comm = self.repo.get_community(community_id)
        if not comm:
            raise LookupError("Comunidad no encontrada")
        if comm["owner_id"] == user_id:
            raise ValueError("El propietario no puede abandonar la comunidad sin transferir la propiedad")

        return self.repo.remove_member(community_id, user_id)

    # =========================================================================
    # ROLES
    # =========================================================================

    def create_role(
        self,
        community_id: str,
        requester_id: str,
        name: str,
        color: str = "#99AAB5",
        position: int = 100,
        is_admin: bool = False,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Crea un nuevo rol validando community.roles.manage y jerarquía de posición."""
        if not self.has_permission(community_id, requester_id, "community.roles.manage"):
            raise PermissionError("Se requiere permiso community.roles.manage")

        req_pos = self.get_user_highest_role_position(community_id, requester_id)
        comm = self.repo.get_community(community_id)
        if comm and comm["owner_id"] != requester_id and position <= req_pos:
            raise PermissionError("No puedes crear un rol con posición superior o igual a tu rol más alto")

        return self.repo.create_role(
            community_id=community_id,
            name=name,
            color=color,
            position=position,
            is_admin=is_admin,
            permissions=permissions,
        )

    def assign_role(self, community_id: str, requester_id: str, target_user_id: str, role_id: str) -> bool:
        """Asigna un rol a un miembro respetando la jerarquía."""
        if not self.has_permission(community_id, requester_id, "community.roles.manage"):
            raise PermissionError("Se requiere permiso community.roles.manage")

        role = self.repo.get_role(role_id)
        if not role or role["community_id"] != community_id:
            raise LookupError("Rol no encontrado")

        req_pos = self.get_user_highest_role_position(community_id, requester_id)
        comm = self.repo.get_community(community_id)
        if comm and comm["owner_id"] != requester_id and role["position"] <= req_pos:
            raise PermissionError("No puedes asignar un rol superior o igual a tu posición")

        return self.repo.assign_role_to_member(community_id, target_user_id, role_id)

    # =========================================================================
    # CANALES
    # =========================================================================

    def create_channel(
        self,
        community_id: str,
        requester_id: str,
        name: str,
        channel_type: str = "text",
        category_id: Optional[str] = None,
        topic: Optional[str] = None,
        is_private: bool = False,
        max_participants: int = 0,
        bitrate_kbps: int = 64,
        position: int = 0,
    ) -> Dict[str, Any]:
        """Crea un canal validando permiso channels.manage."""
        if not self.has_permission(community_id, requester_id, "channels.manage"):
            raise PermissionError("Se requiere permiso channels.manage")

        return self.repo.create_channel(
            community_id=community_id,
            name=name,
            channel_type=channel_type,
            category_id=category_id,
            topic=topic,
            is_private=is_private,
            max_participants=max_participants,
            bitrate_kbps=bitrate_kbps,
            position=position,
        )

    def list_channels(self, community_id: str, requester_id: str) -> List[Dict[str, Any]]:
        """Lista canales visibles para el solicitante (filtra canales privados sin acceso)."""
        all_channels = self.repo.list_channels(community_id)
        visible = []
        for ch in all_channels:
            if not ch.get("is_private"):
                visible.append(ch)
            else:
                # Si es privado, comprobar si puede leer (texto) o conectar (voz)
                perm_needed = "messages.read" if ch["type"] == "text" else "voice.connect"
                if self.has_permission(community_id, requester_id, perm_needed, channel_id=ch["id"]):
                    visible.append(ch)
        return visible

    def delete_channel(self, community_id: str, channel_id: str, requester_id: str) -> bool:
        """Elimina un canal de la comunidad verificando channels.manage."""
        if not self.has_permission(community_id, requester_id, "channels.manage"):
            raise PermissionError("Se requiere permiso channels.manage")
        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado en esta comunidad")
        return self.repo.delete_channel(channel_id)

    def set_channel_override(
        self,
        community_id: str,
        channel_id: str,
        requester_id: str,
        target_type: str,
        target_id: str,
        permission_id: str,
        allow: bool = False,
        deny: bool = False,
    ) -> bool:
        """Aplica una sobrescritura de permiso para un rol o usuario en un canal."""
        if not self.has_permission(community_id, requester_id, "channels.manage"):
            raise PermissionError("Se requiere permiso channels.manage")
        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado")
        return self.repo.set_channel_override(channel_id, target_type, target_id, permission_id, allow, deny)
