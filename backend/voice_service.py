"""
backend/voice_service.py - Servicio de Llamadas de Voz Grupales y Señalización WebRTC.
Implementa las especificaciones funcionales de la Fase 5 (Módulo B.3) para C.C.I. SYSTEM.
100% Python, gestiona sesiones en vivo, participantes, estados de micrófono y enrutamiento P2P Mesh.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional
import cci_database
from backend.config import config
from backend.contracts import SocketEvents


@dataclass
class CallParticipant:
    user_id: str
    username: str
    socket_id: Optional[str] = None
    muted: bool = False
    speaking: bool = False
    joined_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LiveCallSession:
    session_id: str
    group_id: str
    started_by: str
    status: str = "active"  # active, ended
    started_at: float = field(default_factory=time.time)
    participants: Dict[str, CallParticipant] = field(default_factory=dict)
    recording_enabled: bool = False  # Garantía de privacidad: False por defecto

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "group_id": self.group_id,
            "started_by": self.started_by,
            "status": self.status,
            "started_at": self.started_at,
            "participants": [p.to_dict() for p in self.participants.values()],
            "recording_enabled": self.recording_enabled,
        }


class VoiceService:
    """Servicio desacoplado para administración de llamadas grupales y audio WebRTC."""

    _instance: Optional[VoiceService] = None

    @classmethod
    def get_instance(cls) -> VoiceService:
        if cls._instance is None:
            cls._instance = VoiceService()
        return cls._instance

    def __init__(self, broadcast_fn: Optional[Callable[[str, Dict[str, Any], Optional[str]], None]] = None):
        self._broadcast = broadcast_fn
        # Sesiones activas en memoria: session_id -> LiveCallSession
        self._active_calls: Dict[str, LiveCallSession] = {}

    def set_broadcast_fn(self, broadcast_fn: Callable[[str, Dict[str, Any], Optional[str]], None]) -> None:
        self._broadcast = broadcast_fn

    # ==============================================================================
    # 1. GESTIÓN DEL CICLO DE VIDA DE LLAMADAS
    # ==============================================================================

    def start_call(self, group_id: str, started_by: str, username: str, socket_id: Optional[str] = None) -> Dict[str, Any]:
        """Inicia una llamada grupal en vivo."""
        # Comprobar si ya existe una llamada activa en el grupo
        existing = self.get_active_call_for_group(group_id)
        if existing:
            # Si ya existe, unirse a ella
            return self.join_call(existing.session_id, started_by, username, socket_id)

        session_id = f"call_{secrets.token_hex(4)}"
        call = LiveCallSession(
            session_id=session_id,
            group_id=group_id,
            started_by=started_by,
        )
        initiator = CallParticipant(
            user_id=started_by,
            username=username,
            socket_id=socket_id,
            muted=False,
        )
        call.participants[started_by] = initiator
        self._active_calls[session_id] = call

        # Persistir en SQLite
        try:
            cci_database.create_call_session_entry(session_id, group_id, started_by)
        except Exception as exc:
            print(f"[VoiceService] Error persistiendo sesión en SQLite: {exc}")

        # Notificar al grupo sobre la llamada entrante
        if self._broadcast:
            self._broadcast("call:incoming", call.to_dict(), group_id)

        return {"success": True, "call": call.to_dict()}

    def join_call(self, session_id: str, user_id: str, username: str, socket_id: Optional[str] = None) -> Dict[str, Any]:
        """Añade a un miembro a la llamada activa previa validación de membresía de grupo."""
        call = self._active_calls.get(session_id)
        if not call or call.status != "active":
            return {"success": False, "error": "La llamada no está activa o ya finalizó."}

        # Validar pertenencia del usuario al grupo de la llamada (Fail-Closed)
        if call.group_id:
            from backend.auth import check_group_membership
            if not check_group_membership(str(user_id), str(call.group_id)):
                return {"success": False, "error": "Acceso denegado: no perteneces al grupo de esta llamada."}

        participant = CallParticipant(
            user_id=user_id,
            username=username,
            socket_id=socket_id,
            muted=False,
        )
        call.participants[user_id] = participant

        # Notificar a los participantes existentes para disparar el handshake WebRTC P2P
        if self._broadcast:
            self._broadcast(SocketEvents.WEBRTC_PEER_JOINED, {
                "session_id": session_id,
                "user_id": user_id,
                "username": username,
            }, session_id)
            self._broadcast("call:state", call.to_dict(), session_id)

        return {"success": True, "call": call.to_dict()}

    def leave_call(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Remueve a un usuario de la llamada."""
        call = self._active_calls.get(session_id)
        if not call or user_id not in call.participants:
            return {"success": False, "error": "Participante o llamada no encontrada."}

        del call.participants[user_id]

        if self._broadcast:
            self._broadcast(SocketEvents.WEBRTC_PEER_LEFT, {
                "session_id": session_id,
                "user_id": user_id,
            }, session_id)

        # Si no quedan participantes, finalizar la sesión mediante limpieza interna
        if len(call.participants) == 0:
            self._cleanup_empty_call(session_id)

        return {"success": True, "message": "Has salido de la llamada."}

    def _cleanup_empty_call(self, session_id: str) -> None:
        """Operación interna del sistema: remueve y finaliza llamadas que quedaron sin participantes."""
        call = self._active_calls.pop(session_id, None)
        if not call:
            return
        call.status = "ended"
        try:
            cci_database.end_call_session_entry(session_id)
        except Exception as exc:
            print(f"[VoiceService] Error finalizando llamada vacía en SQLite: {exc}")
        if self._broadcast:
            self._broadcast("call:ended", {"session_id": session_id, "ended_by": "system_auto_cleanup"}, session_id)

    def toggle_mute(self, session_id: str, user_id: str, muted: bool) -> Dict[str, Any]:
        """Silencia o activa el micrófono del participante."""
        call = self._active_calls.get(session_id)
        if not call or user_id not in call.participants:
            return {"success": False, "error": "Participante no encontrado en la llamada."}

        call.participants[user_id].muted = muted
        if self._broadcast:
            self._broadcast("call:mute_changed", {
                "session_id": session_id,
                "user_id": user_id,
                "muted": muted,
            }, session_id)

        return {"success": True, "muted": muted}

    def end_call(self, session_id: str, actor_id: str) -> Dict[str, Any]:
        """
        Finaliza voluntariamente la llamada grupal para todos los participantes.
        Política de autorización estricta: Solo el iniciador (started_by) o un administrador/propietario del grupo.
        Participantes regulares y terceros NO tienen permiso de cerrar la llamada para el resto.
        """
        call = self._active_calls.get(session_id)
        if not call:
            return {"success": False, "error": "Llamada no encontrada."}

        # Validar política de autorización estricta: iniciador o admin/owner del grupo
        is_initiator = (str(call.started_by) == str(actor_id))
        is_group_admin = False
        if call.group_id:
            grp = cci_database.get_group_detail(call.group_id)
            if grp:
                for m in grp.get("members", []):
                    if str(m.get("user_id")) == str(actor_id) and m.get("role") in ("owner", "admin"):
                        is_group_admin = True
                        break

        if not (is_initiator or is_group_admin):
            return {
                "success": False,
                "error": "Acceso denegado: solo el iniciador o un administrador del grupo pueden finalizar la llamada para todos."
            }

        self._active_calls.pop(session_id, None)
        call.status = "ended"
        try:
            cci_database.end_call_session_entry(session_id)
        except Exception as exc:
            print(f"[VoiceService] Error finalizando llamada en SQLite: {exc}")

        if self._broadcast:
            self._broadcast("call:ended", {"session_id": session_id, "ended_by": actor_id}, session_id)

        return {"success": True, "message": "Llamada finalizada."}

    def get_call_session(self, session_id: str) -> Optional[LiveCallSession]:
        """Obtiene la sesión de llamada activa por su ID."""
        return self._active_calls.get(session_id)

    def get_active_call_for_group(self, group_id: str) -> Optional[LiveCallSession]:
        """Busca llamada en curso para un grupo."""
        for call in self._active_calls.values():
            if call.group_id == group_id and call.status == "active":
                return call
        return None

    def get_ice_servers(self) -> List[Dict[str, Any]]:
        """
        Retorna la lista de servidores STUN y TURN configurados.
        STUN: Resuelve IP pública en redes abiertas (Google STUN).
        TURN: Relay de audio Opus obligatorio en redes móviles 4G/5G con CGNAT.
        """
        servers = [
            {"urls": [config.stun_server or "stun:stun.l.google.com:19302"]}
        ]
        if config.turn_server:
            turn_entry: Dict[str, Any] = {"urls": [config.turn_server]}
            if config.turn_username:
                turn_entry["username"] = config.turn_username
            if config.turn_credential:
                turn_entry["credential"] = config.turn_credential
            servers.append(turn_entry)
        return servers
