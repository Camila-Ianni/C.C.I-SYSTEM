"""
backend/contracts.py - Definición de contratos de eventos, tipos y payloads
para la comunicación en tiempo real (WebSocket / Socket.IO / WebRTC) en C.C.I. SYSTEM.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RoomStatus(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


class PlayerSlot(int, Enum):
    P1 = 1
    P2 = 2


class ConnectionState(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


# ==============================================================================
# EVENTOS DEL PROTOCOLO DE TIEMPO REAL
# ==============================================================================

class SocketEvents:
    # Gestión de Salas
    ROOM_CREATE = "room:create"
    ROOM_JOIN = "room:join"
    ROOM_LEAVE = "room:leave"
    ROOM_READY = "room:ready"
    ROOM_STATE = "room:state"
    ROOM_ERROR = "room:error"

    # Multijugador y Sincronización
    GAME_INPUT = "game:input"
    GAME_SNAPSHOT = "game:snapshot"
    GAME_PAUSE = "game:pause"
    GAME_RESUME = "game:resume"
    GAME_ROUND_END = "game:round_end"
    GAME_MATCH_END = "game:match_end"

    # Chat y Presencia
    CHAT_SEND = "chat:send"
    CHAT_MESSAGE = "chat:message"
    CHAT_HISTORY = "chat:history"
    USER_PRESENCE = "user:presence"

    # Señalización WebRTC para Voz
    WEBRTC_OFFER = "webrtc:offer"
    WEBRTC_ANSWER = "webrtc:answer"
    WEBRTC_ICE_CANDIDATE = "webrtc:ice_candidate"
    WEBRTC_PEER_JOINED = "webrtc:peer_joined"
    WEBRTC_PEER_LEFT = "webrtc:peer_left"


# ==============================================================================
# PAYLOADS Y CONTRATOS FUERTEMENTE TIPADOS
# ==============================================================================

@dataclass
class PlayerInputPacket:
    """Paquete de entrada de un jugador enviado a 60 Hz."""
    room_id: str
    player_id: int
    tick: int
    seq: int
    dpad: str = "idle"  # idle, left, right, up, down
    buttons: List[str] = field(default_factory=list)  # punch_light, kick_heavy, etc.
    timestamp_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorldSnapshotPacket:
    """Instantánea autoritativa del servidor enviada a 30 Hz."""
    room_id: str
    tick: int
    p1_state: Dict[str, Any]  # x, y, vx, state, hp, facing_right
    p2_state: Dict[str, Any]  # x, y, vx, state, hp, facing_right
    timer: float
    current_round: int
    p1_wins: int
    p2_wins: int
    status: str = "fighting"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChatMessagePayload:
    """Mensaje de chat privado o grupal."""
    message_id: str
    group_id: str
    sender_id: str
    sender_name: str
    body: str
    timestamp_iso: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebRTCSignalingPayload:
    """Mensaje de señalización SDP o ICE candidate."""
    room_id: str
    sender_id: str
    target_id: Optional[str]
    type: str  # offer, answer, ice-candidate
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
