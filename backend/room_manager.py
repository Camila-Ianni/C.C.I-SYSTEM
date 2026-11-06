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

    def join_room(
        self,
        room_id: str,
        user_id: str,
        username: str,
        socket_id: Optional[str] = None
    ) -> Optional[LiveGameRoom]:
        room = self._rooms.get(room_id)
        if not room or room.is_full or room.status != RoomStatus.WAITING:
            return None

        # Si ya es miembro (reconexión)
        if user_id in room.members:
            m = room.members[user_id]
            m.connection_state = ConnectionState.CONNECTED
            m.socket_id = socket_id
            m.last_ping = time.monotonic()
            return room

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
