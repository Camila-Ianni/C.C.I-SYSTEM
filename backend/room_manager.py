"""
backend/room_manager.py - Gestor de salas de juego multijugador en memoria y persistencia.
Maneja creación de salas, emparejamiento, asignación de slots, estados y reconexión.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import cci_database
from backend.contracts import ConnectionState, PlayerSlot, RoomStatus


@dataclass
class MemberSession:
    user_id: str
    username: str
    slot: PlayerSlot
    ready: bool = False
    connection_state: ConnectionState = ConnectionState.CONNECTED
    socket_id: Optional[str] = None
    last_ping: float = field(default_factory=time.monotonic)


@dataclass
class LiveGameRoom:
    room_id: str
    game_id: str
    host_id: str
    visibility: str = "public"
    invite_code: str = field(default_factory=lambda: secrets.token_hex(3).upper())
    status: RoomStatus = RoomStatus.WAITING
    created_at: float = field(default_factory=time.monotonic)
    members: Dict[str, MemberSession] = field(default_factory=dict)
    pause_until: Optional[float] = None

    @property
    def is_full(self) -> bool:
        return len(self.members) >= 2

    @property
    def both_ready(self) -> bool:
        return len(self.members) == 2 and all(m.ready for m in self.members.values())

    def get_slot(self, slot: PlayerSlot) -> Optional[MemberSession]:
        for m in self.members.values():
            if m.slot == slot:
                return m
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "game_id": self.game_id,
            "host_id": self.host_id,
            "visibility": self.visibility,
            "invite_code": self.invite_code,
            "status": self.status.value,
            "members": [
                {
                    "user_id": m.user_id,
                    "username": m.username,
                    "slot": m.slot.value,
                    "ready": m.ready,
                    "connection_state": m.connection_state.value,
                }
                for m in self.members.values()
            ],
            "both_ready": self.both_ready,
        }


class RoomManager:
    """Singleton para administración de salas activas en tiempo real."""
    _instance: Optional[RoomManager] = None

    @classmethod
    def get_instance(cls) -> RoomManager:
        if cls._instance is None:
            cls._instance = RoomManager()
        return cls._instance

    def __init__(self):
        self._rooms: Dict[str, LiveGameRoom] = {}

    def create_room(
        self,
        game_id: str,
        host_id: str,
        host_name: str,
        socket_id: Optional[str] = None,
        visibility: str = "public"
    ) -> LiveGameRoom:
        room_id = f"room_{secrets.token_hex(4)}"
        room = LiveGameRoom(
            room_id=room_id,
            game_id=game_id,
            host_id=host_id,
            visibility=visibility,
        )
        host_session = MemberSession(
            user_id=host_id,
            username=host_name,
            slot=PlayerSlot.P1,
            ready=True,
            socket_id=socket_id,
        )
        room.members[host_id] = host_session
        self._rooms[room_id] = room

        # Persistir en SQLite
        try:
            cci_database.create_game_room(
                room_id=room_id,
                game_id=game_id,
                host_id=host_id,
                visibility=visibility,
                invite_code=room.invite_code,
            )
        except Exception as exc:
            print(f"[RoomManager] Error persistiendo sala en SQLite: {exc}")

        return room

    def find_by_invite_code(self, invite_code: str) -> Optional[LiveGameRoom]:
        code = invite_code.strip().upper()
        for r in self._rooms.values():
            if r.invite_code == code and r.status == RoomStatus.WAITING:
                return r
        # Buscar en base de datos si no está en memoria
        db_room = cci_database.get_room_by_invite_code_entry(code)
        if db_room and db_room["status"] == "waiting":
            # Restaurar en memoria
            room = LiveGameRoom(
                room_id=db_room["id"],
                game_id=db_room["game_id"],
                host_id=db_room["host_id"],
                visibility=db_room["visibility"],
                invite_code=db_room["invite_code"],
            )
            for m in db_room["members"]:
                room.members[m["user_id"]] = MemberSession(
                    user_id=m["user_id"],
                    username=m["user_id"],
                    slot=PlayerSlot.P1 if m["player_slot"] == 1 else PlayerSlot.P2,
                    ready=bool(m["ready_state"]),
                )
            self._rooms[room.room_id] = room
            return room
        return None

    def join_room(
        self,
        room_id: str,
        user_id: str,
        username: str,
        socket_id: Optional[str] = None,
        invite_code: Optional[str] = None
    ) -> Optional[LiveGameRoom]:
        room = self._rooms.get(room_id)
        if not room:
            # Si se pasó código de invitación, buscar por él
            if invite_code:
                room = self.find_by_invite_code(invite_code)
                if room:
                    room_id = room.room_id

        if not room or room.status not in (RoomStatus.WAITING, RoomStatus.PAUSED):
            return None

        # Si ya es miembro (reconexión)
        if user_id in room.members:
            m = room.members[user_id]
            m.connection_state = ConnectionState.CONNECTED
            m.socket_id = socket_id
            m.last_ping = time.monotonic()
            if room.status == RoomStatus.PAUSED:
                room.status = RoomStatus.PLAYING
                room.pause_until = None
            return room

        # Validación de sala llena para miembros nuevos
        if room.is_full or room.status != RoomStatus.WAITING:
            return None

        # Validación de sala privada: si es privada, DEBE coincidir el invite_code
        if room.visibility == "private":
            if not invite_code or invite_code.strip().upper() != room.invite_code:
                return None

        p2_session = MemberSession(
            user_id=user_id,
            username=username,
            slot=PlayerSlot.P2,
            ready=False,
            socket_id=socket_id,
        )
        room.members[user_id] = p2_session

        try:
            cci_database.join_game_room(room_id, user_id, target_slot=2)
        except Exception as exc:
            print(f"[RoomManager] Error registrando miembro en SQLite: {exc}")

        return room

    def get_room(self, room_id: str) -> Optional[LiveGameRoom]:
        return self._rooms.get(room_id)

    def set_ready(self, room_id: str, user_id: str, ready: bool) -> Optional[LiveGameRoom]:
        room = self._rooms.get(room_id)
        if not room or user_id not in room.members:
            return None
        room.members[user_id].ready = ready
        if room.both_ready:
            room.status = RoomStatus.READY
        return room

    def kick_member(self, room_id: str, actor_id: str, target_user_id: str) -> Optional[LiveGameRoom]:
        """Expulsa a un jugador de la sala (solo permitido para el anfitrión)."""
        room = self._rooms.get(room_id)
        if not room or room.host_id != actor_id or target_user_id not in room.members:
            return None
        if actor_id == target_user_id:
            return None

        del room.members[target_user_id]
        try:
            cci_database.leave_game_room(room_id, target_user_id)
        except Exception:
            pass
        room.status = RoomStatus.WAITING
        return room

    def transfer_host(self, room_id: str, actor_id: str, new_host_id: str) -> Optional[LiveGameRoom]:
        """Transfiere el rol de anfitrión a otro jugador de la sala."""
        room = self._rooms.get(room_id)
        if not room or room.host_id != actor_id or new_host_id not in room.members:
            return None
        room.host_id = new_host_id
        # Swap slots
        m_new = room.members[new_host_id]
        m_old = room.members[actor_id]
        m_new.slot = PlayerSlot.P1
        m_old.slot = PlayerSlot.P2
        return room

    def handle_disconnect(self, socket_id: str, grace_seconds: float = 5.0) -> Optional[LiveGameRoom]:
        """Maneja desconexión de un socket activando ventana de gracia de 5s."""
        for room in self._rooms.values():
            for m in room.members.values():
                if m.socket_id == socket_id:
                    m.connection_state = ConnectionState.DISCONNECTED
                    if room.status == RoomStatus.PLAYING:
                        room.status = RoomStatus.PAUSED
                        room.pause_until = time.monotonic() + grace_seconds
                    return room
        return None

    def leave_room(self, room_id: str, user_id: str) -> Optional[LiveGameRoom]:
        room = self._rooms.get(room_id)
        if not room or user_id not in room.members:
            return None

        del room.members[user_id]
        try:
            cci_database.leave_game_room(room_id, user_id)
        except Exception:
            pass

        # Si el host se va o queda vacía, cerramos la sala
        if room.host_id == user_id or len(room.members) == 0:
            room.status = RoomStatus.FINISHED
            self._rooms.pop(room_id, None)

        return room

