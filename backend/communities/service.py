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
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from backend.communities.repository import CommunitiesRepository
from backend.communities.sound_validator import (
    validate_mp3_payload,
    save_sound_file,
    SoundValidationError,
)
from backend.communities.stream_adapter import (
    validate_stream_profile,
    detect_available_capture_sources,
    StreamValidationError,
)


class SoundCooldownError(Exception):
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class StreamLimitError(Exception):
    def __init__(self, message: str = "Límite de streams concurrentes alcanzado"):
        super().__init__(message)
        self.message = message


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

            # Si el canal es privado, cualquier acción exige allow explícito o rol de gestión
            if chan.get("is_private"):
                has_channel_access = has_role_allow or any(
                    ov["allow"] for ov in overrides
                    if (ov["target_type"] == "user" and ov["target_id"] == user_id) or
                       (ov["target_type"] == "role" and ov["target_id"] in role_ids)
                )
                if not has_channel_access:
                    return False

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

        # Comprobar si el usuario está baneado
        if self.repo.is_user_banned(comm["id"], user_id):
            raise PermissionError("El usuario tiene una sanción de ban activa en esta comunidad")

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

    # =========================================================================
    # MENSAJERÍA EN TIEMPO REAL E HISTORIAL PAGINADO
    # =========================================================================

    def send_message(
        self,
        community_id: str,
        channel_id: str,
        author_id: str,
        content: str,
        reply_to_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publica un mensaje en un canal de texto validando permiso messages.send y límites."""
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("El contenido del mensaje no puede estar vacío")
        if len(clean_content) > 2000:
            raise ValueError("El mensaje excede el límite máximo de 2000 caracteres")

        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado en esta comunidad")
        if ch["type"] != "text":
            raise ValueError("Solo es posible enviar mensajes en canales de tipo texto")

        if not self.has_permission(community_id, author_id, "messages.send", channel_id=channel_id):
            raise PermissionError("Acceso denegado: se requiere permiso messages.send")

        if self.repo.is_user_muted(community_id, author_id):
            raise PermissionError("El usuario se encuentra silenciado en esta comunidad")

        if reply_to_id:
            parent = self.repo.get_message(reply_to_id)
            if not parent or parent["channel_id"] != channel_id:
                raise LookupError("Mensaje de respuesta no encontrado en este canal")

        msg = self.repo.create_message(
            channel_id=channel_id,
            author_id=author_id,
            content=clean_content,
            reply_to_id=reply_to_id,
        )
        return msg

    def list_channel_messages(
        self,
        community_id: str,
        channel_id: str,
        requester_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Recupera el historial paginado de mensajes validando permiso messages.read."""
        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado en esta comunidad")

        if not self.has_permission(community_id, requester_id, "messages.read", channel_id=channel_id):
            raise PermissionError("Acceso denegado: se requiere permiso messages.read")

        limit = max(1, min(100, limit))
        return self.repo.list_messages(channel_id, limit=limit, before_id=before_id)

    def edit_message(
        self,
        community_id: str,
        channel_id: str,
        message_id: str,
        requester_id: str,
        new_content: str,
    ) -> Dict[str, Any]:
        """Edita un mensaje existente: solo el autor original o moderador con messages.manage."""
        clean_content = new_content.strip()
        if not clean_content:
            raise ValueError("El contenido del mensaje no puede estar vacío")
        if len(clean_content) > 2000:
            raise ValueError("El mensaje excede el límite máximo de 2000 caracteres")

        msg = self.repo.get_message(message_id)
        if not msg or msg["channel_id"] != channel_id:
            raise LookupError("Mensaje no encontrado")

        is_author = (msg["author_id"] == requester_id)
        has_manage = self.has_permission(community_id, requester_id, "messages.manage", channel_id=channel_id)
        if not (is_author or has_manage):
            raise PermissionError("No tienes permiso para editar este mensaje")

        updated = self.repo.update_message(message_id, clean_content)
        if not updated:
            raise LookupError("Mensaje no encontrado")
        return updated

    def delete_message(
        self,
        community_id: str,
        channel_id: str,
        message_id: str,
        requester_id: str,
    ) -> bool:
        """Eliminación lógica de mensaje: autor original o moderador con messages.manage."""
        msg = self.repo.get_message(message_id)
        if not msg or msg["channel_id"] != channel_id:
            raise LookupError("Mensaje no encontrado")

        is_author = (msg["author_id"] == requester_id)
        has_manage = self.has_permission(community_id, requester_id, "messages.manage", channel_id=channel_id)
        if not (is_author or has_manage):
            raise PermissionError("No tienes permiso para eliminar este mensaje")

        return self.repo.delete_message(message_id)

    # =========================================================================
    # PRESENCIA DE USUARIOS (ONLINE, IDLE, DND, INVISIBLE)
    # =========================================================================

    def set_user_presence(
        self,
        user_id: str,
        status: str = "online",
        custom_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Actualiza el estado de presencia global del usuario."""
        valid_statuses = {"online", "idle", "dnd", "invisible", "offline"}
        if status not in valid_statuses:
            raise ValueError(f"Estado de presencia inválido: {status}")

        return self.repo.set_presence(user_id, status=status, custom_status=custom_status)

    def get_user_presence(self, user_id: str, viewer_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene la presencia de un usuario; si está en 'invisible', se enmascara como 'offline'."""
        p = self.repo.get_presence(user_id)
        res = dict(p)
        if res.get("status") == "invisible" and viewer_id != user_id:
            res["status"] = "offline"
        return res

    def list_user_presences(self, user_ids: List[str], viewer_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        raw = self.repo.list_presences(user_ids)
        result = {}
        for uid, p in raw.items():
            entry = dict(p)
            if entry.get("status") == "invisible" and viewer_id != uid:
                entry["status"] = "offline"
            result[uid] = entry
        return result

    # =========================================================================
    # CANALES DE VOZ Y EMISIÓN DE TOKENS LIVEKIT
    # =========================================================================

    def request_voice_token(
        self,
        community_id: str,
        channel_id: str,
        user_id: str,
        username: str = "User",
    ) -> Dict[str, Any]:
        """Verifica autorización de acceso a canal de voz y emite credencial token JWT LiveKit."""
        from backend.communities.livekit_token import LiveKitTokenGenerator

        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado en esta comunidad")
        if ch["type"] not in ("voice", "stream"):
            raise ValueError("El canal seleccionado no es de tipo voz ni streaming")

        if not self.has_permission(community_id, user_id, "voice.connect", channel_id=channel_id):
            raise PermissionError("Acceso denegado: se requiere permiso voice.connect")

        # Comprobar límite de participantes activos
        max_p = ch.get("max_participants", 0)
        if max_p > 0:
            current_count = self.repo.count_active_voice_sessions(channel_id)
            if current_count >= max_p:
                raise ValueError("La sala de voz ha alcanzado su límite de participantes")

        # Comprobar permiso de transmisión de micrófono
        can_speak = self.has_permission(community_id, user_id, "voice.speak", channel_id=channel_id)

        room_name = f"comm_{community_id[:8]}_chan_{channel_id[:8]}"
        generator = LiveKitTokenGenerator()
        cred = generator.create_access_token(
            identity=user_id,
            name=username,
            room_name=room_name,
            can_publish=can_speak,
            can_subscribe=True,
            can_publish_data=True,
            valid_for_seconds=600,
        )

        # Registrar sesión de voz activa en base de datos
        self.repo.create_voice_session(
            channel_id=channel_id,
            user_id=user_id,
            room_name=room_name,
            participant_id=user_id,
        )

        return cred

    def leave_voice_channel(self, community_id: str, channel_id: str, user_id: str) -> bool:
        """Registra la salida formal del canal de voz liberando el slot."""
        return self.repo.end_voice_session(channel_id, user_id)

    def list_voice_participants(
        self,
        community_id: str,
        channel_id: str,
        requester_id: str,
    ) -> List[Dict[str, Any]]:
        """Lista participantes activos en la sala de voz."""
        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado")

        if not self.has_permission(community_id, requester_id, "voice.connect", channel_id=channel_id):
            raise PermissionError("Se requiere permiso voice.connect")

        return self.repo.list_active_voice_sessions(channel_id)

    def moderate_voice_participant(
        self,
        community_id: str,
        channel_id: str,
        requester_id: str,
        target_user_id: str,
        action: str,
    ) -> bool:
        """Modera a un participante en la sala (silenciar o desconectar) respetando jerarquías."""
        comm = self.repo.get_community(community_id)
        if not comm:
            raise LookupError("Comunidad no encontrada")
        if target_user_id == comm["owner_id"]:
            raise PermissionError("No es posible moderar al propietario de la comunidad")

        if action == "mute":
            if not self.has_permission(community_id, requester_id, "voice.mute_members", channel_id=channel_id):
                raise PermissionError("Se requiere permiso voice.mute_members")
            req_pos = self.get_user_highest_role_position(community_id, requester_id)
            target_pos = self.get_user_highest_role_position(community_id, target_user_id)
            if req_pos >= target_pos and comm["owner_id"] != requester_id:
                raise PermissionError("Jerarquía insuficiente para moderar a este miembro")
            return self.repo.update_voice_session_mute(channel_id, target_user_id, True)

        elif action == "disconnect":
            if not self.has_permission(community_id, requester_id, "voice.move_members", channel_id=channel_id):
                raise PermissionError("Se requiere permiso voice.move_members")
            req_pos = self.get_user_highest_role_position(community_id, requester_id)
            target_pos = self.get_user_highest_role_position(community_id, target_user_id)
            if req_pos >= target_pos and comm["owner_id"] != requester_id:
                raise PermissionError("Jerarquía insuficiente para desconectar a este miembro")
            return self.repo.end_voice_session(channel_id, target_user_id)

        else:
            raise ValueError(f"Acción de moderación no reconocida: {action}")

    # =========================================================================
    # SOUND DECK (SOUNDBOARD)
    # =========================================================================

    def create_sound_category(
        self,
        actor_id: str,
        scope_type: str,
        name: str,
        scope_id: Optional[str] = None,
        position: int = 0,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """Crea una categoría para organizar sonidos en un scope determinado."""
        if scope_type not in ("global", "user", "community"):
            raise ValueError(f"Tipo de scope inválido: {scope_type}")

        if not name or not name.strip():
            raise ValueError("El nombre de categoría no puede estar vacío")

        if scope_type == "global":
            if not is_admin and actor_id not in ("admin", "system"):
                raise PermissionError("Solo administradores pueden crear categorías globales")
            scope_id = None
        elif scope_type == "user":
            scope_id = actor_id
        elif scope_type == "community":
            if not scope_id:
                raise ValueError("Se requiere scope_id (ID de comunidad)")
            comm = self.repo.get_community(scope_id)
            if not comm:
                raise LookupError("Comunidad no encontrada")
            if not self.has_permission(scope_id, actor_id, "soundboard.manage"):
                raise PermissionError("Se requiere permiso soundboard.manage")

        category_id = str(uuid.uuid4())
        return self.repo.create_sound_category(
            category_id=category_id,
            scope_type=scope_type,
            scope_id=scope_id,
            name=name.strip(),
            position=position,
        )

    def list_sound_categories(
        self,
        actor_id: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista categorías accesibles para el usuario."""
        return self.repo.list_sound_categories(scope_type=scope_type, scope_id=scope_id)

    def upload_sound(
        self,
        actor_id: str,
        owner_type: str,
        title: str,
        file_bytes: bytes,
        owner_id: Optional[str] = None,
        category_id: Optional[str] = None,
        volume_scale: float = 1.0,
        cooldown_seconds: int = 5,
        declared_duration: Optional[float] = None,
        is_admin: bool = False,
        storage_dir: str = "storage/sounds",
    ) -> Dict[str, Any]:
        """Sube y valida un archivo MP3 asociándolo al scope correspondiente."""
        if owner_type not in ("global", "user", "community"):
            raise ValueError(f"Tipo de propietario no reconocido: {owner_type}")

        if not title or not title.strip():
            raise ValueError("El título del sonido no puede estar vacío")

        # 1. Comprobar permisos según scope
        if owner_type == "global":
            if not is_admin and actor_id not in ("admin", "system"):
                raise PermissionError("Solo administradores pueden subir sonidos globales")
            owner_id = None

        elif owner_type == "user":
            owner_id = actor_id
            # Comprobar cuota de sonidos personales (máximo 50)
            user_count = self.repo.count_user_sounds(actor_id)
            if user_count >= 50:
                raise ValueError("Límite de sonidos personales alcanzado (máximo 50)")

        elif owner_type == "community":
            if not owner_id:
                raise ValueError("Se requiere owner_id (ID de comunidad)")
            comm = self.repo.get_community(owner_id)
            if not comm:
                raise LookupError("Comunidad no encontrada")
            if not self.has_permission(owner_id, actor_id, "soundboard.manage"):
                raise PermissionError("Se requiere permiso soundboard.manage para subir sonidos al grupo")

        # 2. Validar payload de audio MP3
        try:
            _, duration, checksum = validate_mp3_payload(
                file_bytes=file_bytes,
                declared_duration=declared_duration,
            )
        except SoundValidationError as e:
            raise ValueError(f"Validación de audio falló [{e.code}]: {e.message}")

        # 3. Guardar archivo en almacenamiento
        sound_id = str(uuid.uuid4())
        storage_key = save_sound_file(storage_dir, sound_id, file_bytes)

        # 4. Registrar en repositorio
        return self.repo.create_sound_asset(
            sound_id=sound_id,
            category_id=category_id,
            owner_type=owner_type,
            owner_id=owner_id,
            uploader_id=actor_id,
            storage_key=storage_key,
            title=title.strip(),
            duration_seconds=duration,
            file_size_bytes=len(file_bytes),
            format_str="mp3",
            volume_scale=max(0.0, min(2.0, float(volume_scale))),
            cooldown_seconds=max(1, int(cooldown_seconds)),
            checksum_sha256=checksum,
        )

    def list_sounds(
        self,
        actor_id: str,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        community_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista sonidos según filtros de biblioteca o para una comunidad en particular."""
        if community_id:
            comm = self.repo.get_community(community_id)
            if not comm:
                raise LookupError("Comunidad no encontrada")
            # Verificar permiso básico de lectura de comunidad
            if not self.has_permission(community_id, actor_id, "community.view"):
                raise PermissionError("No tienes permiso para ver los sonidos de esta comunidad")
            return self.repo.list_sounds_for_community(
                community_id=community_id,
                user_id=actor_id,
                search=search,
            )

        return self.repo.list_sound_assets(
            owner_type=owner_type,
            owner_id=owner_id,
            category_id=category_id,
            search=search,
        )

    def get_sound(self, actor_id: str, sound_id: str) -> Dict[str, Any]:
        """Obtiene un sonido validando acceso."""
        sound = self.repo.get_sound_asset(sound_id)
        if not sound:
            raise LookupError("Sonido no encontrado")

        if sound["owner_type"] == "community":
            if not self.has_permission(sound["owner_id"], actor_id, "community.view"):
                raise PermissionError("No tienes acceso al sonido de esta comunidad")

        return sound

    def update_sound(
        self,
        actor_id: str,
        sound_id: str,
        title: Optional[str] = None,
        category_id: Optional[str] = None,
        volume_scale: Optional[float] = None,
        cooldown_seconds: Optional[int] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """Edita metadatos de un sonido si el usuario tiene privilegios."""
        sound = self.repo.get_sound_asset(sound_id)
        if not sound:
            raise LookupError("Sonido no encontrado")

        if sound["owner_type"] == "global":
            if not is_admin and actor_id not in ("admin", "system"):
                raise PermissionError("Solo administradores pueden editar sonidos globales")
        elif sound["owner_type"] == "user":
            if sound["uploader_id"] != actor_id and not is_admin:
                raise PermissionError("No puedes editar el sonido de otro usuario")
        elif sound["owner_type"] == "community":
            can_manage = self.has_permission(sound["owner_id"], actor_id, "soundboard.manage")
            is_uploader = sound["uploader_id"] == actor_id
            if not can_manage and not is_uploader and not is_admin:
                raise PermissionError("Se requiere permiso soundboard.manage para editar este sonido")

        updated = self.repo.update_sound_asset(
            sound_id=sound_id,
            title=title.strip() if title else None,
            category_id=category_id,
            volume_scale=max(0.0, min(2.0, float(volume_scale))) if volume_scale is not None else None,
            cooldown_seconds=max(1, int(cooldown_seconds)) if cooldown_seconds is not None else None,
        )
        return updated or sound

    def delete_sound(self, actor_id: str, sound_id: str, is_admin: bool = False) -> bool:
        """Elimina un sonido mediante soft delete comprobando permisos."""
        sound = self.repo.get_sound_asset(sound_id)
        if not sound:
            raise LookupError("Sonido no encontrado")

        if sound["owner_type"] == "global":
            if not is_admin and actor_id not in ("admin", "system"):
                raise PermissionError("Solo administradores pueden eliminar sonidos globales")
        elif sound["owner_type"] == "user":
            if sound["uploader_id"] != actor_id and not is_admin:
                raise PermissionError("No puedes eliminar el sonido de otro usuario")
        elif sound["owner_type"] == "community":
            can_manage = self.has_permission(sound["owner_id"], actor_id, "soundboard.manage")
            is_uploader = sound["uploader_id"] == actor_id
            if not can_manage and not is_uploader and not is_admin:
                raise PermissionError("Se requiere permiso soundboard.manage para eliminar este sonido")

        return self.repo.delete_sound_asset(sound_id)

    def toggle_favorite_sound(
        self,
        actor_id: str,
        sound_id: str,
        is_favorite: bool = True,
        hotkey: Optional[str] = None,
    ) -> bool:
        """Marca o desmarca un sonido como favorito y asigna una tecla rápida opcional."""
        sound = self.repo.get_sound_asset(sound_id)
        if not sound:
            raise LookupError("Sonido no encontrado")
        return self.repo.set_sound_favorite(
            user_id=actor_id,
            sound_id=sound_id,
            is_favorite=is_favorite,
            hotkey=hotkey,
        )

    def list_favorite_sounds(self, actor_id: str) -> List[Dict[str, Any]]:
        """Lista los sonidos favoritos del usuario con sus teclas rápidas."""
        return self.repo.list_sound_favorites(actor_id)

    def authorize_sound_play(
        self,
        actor_id: str,
        sound_id: str,
        channel_id: str,
    ) -> Dict[str, Any]:
        """
        Autoriza la reproducción de un sonido en una sala de voz.
        Valida:
        1. Existencia del sonido y del canal.
        2. Canal debe ser de tipo 'voice'.
        3. Permiso 'soundboard.play' en la comunidad/canal.
        4. Acceso al sonido (global, personal propio o de la misma comunidad).
        5. Cooldown anti-spam (HTTP 429 si se repite antes de vencer).
        """
        sound = self.repo.get_sound_asset(sound_id)
        if not sound:
            raise LookupError("Sonido no encontrado")

        chan = self.repo.get_channel(channel_id)
        if not chan:
            raise LookupError("Canal de voz no encontrado")

        if chan.get("type") != "voice":
            raise ValueError("El canal especificado no es una sala de voz")

        community_id = chan["community_id"]

        # Comprobar pertenencia del sonido
        if sound["owner_type"] == "community":
            if sound["owner_id"] != community_id:
                raise PermissionError("Este sonido pertenece a otra comunidad y no puede reproducirse aquí")
        elif sound["owner_type"] == "user":
            if sound["owner_id"] != actor_id:
                raise PermissionError("No puedes reproducir sonidos personales de otro usuario")

        # Comprobar permiso soundboard.play en el canal
        if not self.has_permission(community_id, actor_id, "soundboard.play", channel_id=channel_id):
            raise PermissionError("Se requiere permiso soundboard.play para reproducir sonidos")

        # Comprobar cooldown anti-spam
        cooldown_sec = sound.get("cooldown_seconds", 5)
        last_played = self.repo.get_last_sound_play(sound_id, user_id=actor_id)
        now = time.time()
        if last_played is not None:
            elapsed = now - last_played
            if elapsed < cooldown_sec:
                retry_after = round(cooldown_sec - elapsed, 2)
                raise SoundCooldownError(
                    f"Sonido en enfriamiento. Espera {retry_after}s antes de volver a reproducirlo",
                    retry_after=retry_after,
                )

        # Registrar reproducción
        play_id = str(uuid.uuid4())
        self.repo.record_sound_play(play_id, sound_id, actor_id, channel_id)

        return {
            "authorized": True,
            "sound_id": sound_id,
            "title": sound["title"],
            "channel_id": channel_id,
            "community_id": community_id,
            "storage_key": sound["storage_key"],
            "duration_seconds": sound["duration_seconds"],
            "volume_scale": sound["volume_scale"],
            "cooldown_seconds": cooldown_sec,
        }

    # =========================================================================
    # STREAMING (COMPARTIR PANTALLA, VENTANA Y JUEGOS EN VIVO)
    # =========================================================================

    def get_capture_sources(self, actor_id: str) -> Dict[str, Any]:
        """Obtiene las fuentes detectables (pantallas, ventanas, juegos instalados) y perfiles."""
        return detect_available_capture_sources()

    def start_stream(
        self,
        actor_id: str,
        username: str,
        community_id: str,
        channel_id: str,
        stream_type: str,
        title: str,
        game_id: Optional[str] = None,
        resolution: str = "1080p",
        fps: int = 60,
        bitrate_kbps: int = 4500,
        has_audio: bool = True,
    ) -> Dict[str, Any]:
        """
        Inicia una sesión de transmisión de pantalla o juego en un canal.
        Valida:
        1. Existencia del canal y tipo compatible ('voice' o 'stream').
        2. Permiso 'voice.stream'.
        3. Límites de concurrencia de stream por canal (max_streams_per_channel).
        4. Parámetros técnicos del perfil de video.
        5. Emisión de token LiveKit con video grant can_publish=True.
        """
        ch = self.repo.get_channel(channel_id)
        if not ch or ch["community_id"] != community_id:
            raise LookupError("Canal no encontrado")

        if ch.get("type") not in ("voice", "stream"):
            raise ValueError("El canal debe ser de tipo 'voice' o 'stream' para transmitir pantalla")

        # Comprobar permiso fail-closed
        if not self.has_permission(community_id, actor_id, "voice.stream", channel_id=channel_id):
            raise PermissionError("Se requiere permiso voice.stream para transmitir pantalla o juegos")

        # Validar perfil técnico
        res_clean, fps_clean, bitrate_clean = validate_stream_profile(resolution, fps, bitrate_kbps)

        # Comprobar límite de transmisiones simultáneas por canal
        active_stream = self.repo.get_active_stream_for_channel(channel_id)
        if active_stream:
            if active_stream["user_id"] != actor_id:
                raise StreamLimitError("El canal ha alcanzado el límite de transmisiones simultáneas")
            else:
                # El usuario ya tenía una sesión activa; cerrarla limpiamente antes de reiniciar
                self.repo.end_stream_session(active_stream["id"])

        # Generar credencial LiveKit autoritativa para el stream
        from backend.communities.livekit_token import LiveKitTokenGenerator
        room_name = f"comm_{community_id[:8]}_chan_{channel_id[:8]}"
        generator = LiveKitTokenGenerator()
        livekit_cred = generator.create_access_token(
            identity=actor_id,
            name=username,
            room_name=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
            valid_for_seconds=1800,
        )

        session_id = str(uuid.uuid4())
        session = self.repo.create_stream_session(
            session_id=session_id,
            channel_id=channel_id,
            user_id=actor_id,
            stream_type=stream_type,
            title=title.strip() if title else "Live Stream",
            game_id=game_id,
            resolution=res_clean,
            fps=fps_clean,
            bitrate_kbps=bitrate_clean,
            has_audio=has_audio,
            livekit_track_id=f"track_v_{session_id[:8]}",
        )

        return {
            "session": session,
            "livekit": livekit_cred,
        }

    def pause_stream(
        self,
        actor_id: str,
        community_id: str,
        channel_id: str,
        session_id: str,
        is_paused: bool = True,
    ) -> Dict[str, Any]:
        """Pausa o reanuda la transmisión activa."""
        session = self.repo.get_stream_session(session_id)
        if not session or session["channel_id"] != channel_id:
            raise LookupError("Sesión de stream no encontrada")

        if session["ended_at"] is not None:
            raise ValueError("La sesión de stream ya ha finalizado")

        # Solo el emisor o moderadores pueden pausar
        if session["user_id"] != actor_id:
            can_mod = self.has_permission(community_id, actor_id, "voice.move_members", channel_id=channel_id)
            if not can_mod:
                raise PermissionError("No tienes permiso para pausar el stream de otro usuario")

        self.repo.pause_stream_session(session_id, is_paused)
        session["is_paused"] = is_paused
        return session

    def stop_stream(
        self,
        actor_id: str,
        community_id: str,
        channel_id: str,
        session_id: str,
    ) -> bool:
        """Detiene la transmisión activa liberando el slot del canal."""
        session = self.repo.get_stream_session(session_id)
        if not session or session["channel_id"] != channel_id:
            raise LookupError("Sesión de stream no encontrada")

        if session["ended_at"] is not None:
            return True

        if session["user_id"] != actor_id:
            can_mod = self.has_permission(community_id, actor_id, "voice.move_members", channel_id=channel_id)
            if not can_mod:
                raise PermissionError("No tienes permiso para detener el stream de otro usuario")

        return self.repo.end_stream_session(session_id)

    def get_active_channel_stream(
        self,
        actor_id: str,
        community_id: str,
        channel_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Obtiene la información del stream activo en el canal."""
        if not self.has_permission(community_id, actor_id, "community.view", channel_id=channel_id):
            raise PermissionError("No tienes permiso para ver este canal")

        return self.repo.get_active_stream_for_channel(channel_id)

    def list_active_streams(
        self,
        actor_id: str,
        community_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista streams activos visibles para el usuario."""
        if community_id and not self.has_permission(community_id, actor_id, "community.view"):
            raise PermissionError("No tienes permiso para ver esta comunidad")

        return self.repo.list_active_streams(community_id=community_id)

    # =========================================================================
    # MODERACIÓN, SANCIONES JERÁRQUICAS, REPORTES Y AUDITORÍA
    # =========================================================================

    def _check_moderation_hierarchy(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
    ) -> None:
        """Verifica que el actor tenga jerarquía superior a la del usuario objetivo."""
        comm = self.repo.get_community(community_id)
        if not comm:
            raise LookupError("Comunidad no encontrada")

        if target_user_id == comm["owner_id"]:
            raise PermissionError("No es posible moderar al propietario de la comunidad")

        if actor_id != comm["owner_id"]:
            req_pos = self.get_user_highest_role_position(community_id, actor_id)
            target_pos = self.get_user_highest_role_position(community_id, target_user_id)
            if req_pos >= target_pos:
                raise PermissionError("Jerarquía insuficiente para sancionar a este miembro")

    def warn_member(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Emite una advertencia formal con motivo a un miembro de la comunidad."""
        can_mod = (
            self.has_permission(community_id, actor_id, "community.manage")
            or self.has_permission(community_id, actor_id, "community.members.kick")
        )
        if not can_mod:
            raise PermissionError("Se requiere permiso de moderación para advertir miembros")

        self._check_moderation_hierarchy(community_id, actor_id, target_user_id)
        action_id = str(uuid.uuid4())
        action = self.repo.create_moderation_action(
            action_id=action_id,
            community_id=community_id,
            actor_id=actor_id,
            target_id=target_user_id,
            action="warn",
            reason=reason.strip() if reason else "Advertencia de moderación",
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="member.warn",
            target_id=target_user_id,
            details_json=f'{{"reason": "{reason}"}}',
        )
        return action

    def mute_member(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
        duration_minutes: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Silencia temporal o permanentemente a un miembro en chat y voz."""
        can_mod = (
            self.has_permission(community_id, actor_id, "voice.mute_members")
            or self.has_permission(community_id, actor_id, "community.manage")
        )
        if not can_mod:
            raise PermissionError("Se requiere permiso voice.mute_members para silenciar miembros")

        self._check_moderation_hierarchy(community_id, actor_id, target_user_id)
        expires_at = time.time() + (duration_minutes * 60) if duration_minutes else None

        action_id = str(uuid.uuid4())
        action = self.repo.create_moderation_action(
            action_id=action_id,
            community_id=community_id,
            actor_id=actor_id,
            target_id=target_user_id,
            action="mute",
            reason=reason,
            expires_at=expires_at,
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="member.mute",
            target_id=target_user_id,
            details_json=f'{{"duration_minutes": {duration_minutes}, "reason": "{reason}"}}',
        )
        return action

    def unmute_member(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revoca el silenciamiento de un miembro."""
        can_mod = (
            self.has_permission(community_id, actor_id, "voice.mute_members")
            or self.has_permission(community_id, actor_id, "community.manage")
        )
        if not can_mod:
            raise PermissionError("Se requiere permiso voice.mute_members para reactivar miembros")

        self._check_moderation_hierarchy(community_id, actor_id, target_user_id)
        action_id = str(uuid.uuid4())
        action = self.repo.create_moderation_action(
            action_id=action_id,
            community_id=community_id,
            actor_id=actor_id,
            target_id=target_user_id,
            action="unmute",
            reason=reason,
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="member.unmute",
            target_id=target_user_id,
            details_json=f'{{"reason": "{reason}"}}',
        )
        return action

    def kick_member_with_audit(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Expulsa a un miembro registrando la acción en moderación y log de auditoría."""
        if not self.has_permission(community_id, actor_id, "community.members.kick"):
            raise PermissionError("Se requiere permiso community.members.kick")

        self._check_moderation_hierarchy(community_id, actor_id, target_user_id)
        self.repo.remove_member(community_id, target_user_id)

        action_id = str(uuid.uuid4())
        self.repo.create_moderation_action(
            action_id=action_id,
            community_id=community_id,
            actor_id=actor_id,
            target_id=target_user_id,
            action="kick",
            reason=reason,
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="member.kick",
            target_id=target_user_id,
            details_json=f'{{"reason": "{reason}"}}',
        )
        return True

    def ban_member(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
        duration_hours: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Banea permanente o temporalmente a un usuario impidiendo su reingreso."""
        if not self.has_permission(community_id, actor_id, "community.members.ban"):
            raise PermissionError("Se requiere permiso community.members.ban")

        self._check_moderation_hierarchy(community_id, actor_id, target_user_id)
        expires_at = time.time() + (duration_hours * 3600) if duration_hours else None

        # Remover membresía si aún es miembro
        self.repo.remove_member(community_id, target_user_id)

        action_id = str(uuid.uuid4())
        action = self.repo.create_moderation_action(
            action_id=action_id,
            community_id=community_id,
            actor_id=actor_id,
            target_id=target_user_id,
            action="ban",
            reason=reason,
            expires_at=expires_at,
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="member.ban",
            target_id=target_user_id,
            details_json=f'{{"duration_hours": {duration_hours}, "reason": "{reason}"}}',
        )
        return action

    def unban_member(
        self,
        community_id: str,
        actor_id: str,
        target_user_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revoca la sanción de ban de un usuario."""
        if not self.has_permission(community_id, actor_id, "community.members.ban"):
            raise PermissionError("Se requiere permiso community.members.ban")

        action_id = str(uuid.uuid4())
        action = self.repo.create_moderation_action(
            action_id=action_id,
            community_id=community_id,
            actor_id=actor_id,
            target_id=target_user_id,
            action="unban",
            reason=reason,
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="member.unban",
            target_id=target_user_id,
            details_json=f'{{"reason": "{reason}"}}',
        )
        return action

    def list_moderation_actions(
        self,
        community_id: str,
        actor_id: str,
        target_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista el historial de sanciones aplicadas en la comunidad."""
        can_view = (
            self.has_permission(community_id, actor_id, "community.manage")
            or self.has_permission(community_id, actor_id, "community.members.kick")
            or self.has_permission(community_id, actor_id, "community.members.ban")
        )
        if not can_view:
            raise PermissionError("Se requieren permisos de moderación para ver el historial de sanciones")

        return self.repo.list_moderation_actions(
            community_id=community_id,
            target_id=target_id,
            action=action,
        )

    def create_report(
        self,
        community_id: str,
        reporter_id: str,
        target_type: str,
        target_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Crea un reporte de usuario o mensaje abusivo."""
        if not self.has_permission(community_id, reporter_id, "community.view"):
            raise PermissionError("Se requiere acceso a la comunidad para emitir reportes")

        if target_type not in ("user", "message"):
            raise ValueError("target_type debe ser 'user' o 'message'")

        if not reason or not reason.strip():
            raise ValueError("El motivo del reporte no puede estar vacío")

        report_id = str(uuid.uuid4())
        return self.repo.create_report(
            report_id=report_id,
            community_id=community_id,
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason.strip(),
        )

    def list_reports(
        self,
        community_id: str,
        actor_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista los reportes de la comunidad (solo moderadores)."""
        can_view = (
            self.has_permission(community_id, actor_id, "community.manage")
            or self.has_permission(community_id, actor_id, "community.members.kick")
        )
        if not can_view:
            raise PermissionError("Se requieren permisos de moderación para consultar reportes")

        return self.repo.list_reports(community_id=community_id, status=status)

    def resolve_report(
        self,
        community_id: str,
        actor_id: str,
        report_id: str,
        status: str = "resolved",
        resolution_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Marca un reporte como resuelto o descartado."""
        can_mod = (
            self.has_permission(community_id, actor_id, "community.manage")
            or self.has_permission(community_id, actor_id, "community.members.kick")
        )
        if not can_mod:
            raise PermissionError("Se requieren permisos de moderación para resolver reportes")

        report = self.repo.get_report(report_id)
        if not report or report["community_id"] != community_id:
            raise LookupError("Reporte no encontrado")

        updated = self.repo.resolve_report(
            report_id=report_id,
            resolver_id=actor_id,
            status=status,
            resolution_notes=resolution_notes,
        )
        self.repo.create_audit_entry(
            entry_id=str(uuid.uuid4()),
            community_id=community_id,
            actor_id=actor_id,
            action_type="report.resolve",
            target_id=report_id,
            details_json=f'{{"status": "{status}", "notes": "{resolution_notes}"}}',
        )
        return updated or report

    def list_audit_log(
        self,
        community_id: str,
        actor_id: str,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Consulta el log inmutable de auditoría de la comunidad."""
        if not self.has_permission(community_id, actor_id, "community.manage"):
            raise PermissionError("Se requiere permiso community.manage para consultar el log de auditoría")

        return self.repo.list_audit_entries(
            community_id=community_id,
            action_type=action_type,
            limit=limit,
        )
