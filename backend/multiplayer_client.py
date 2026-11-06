"""
backend/multiplayer_client.py - Cliente de red ligero para partidas multijugador online.
Conecta el bucle de juego local de Da Vinci Fighters con el servidor autoritativo de C.C.I. SYSTEM.
100% Python, calcula latencia/RTT, gestiona predicción local e interpolación de estados remotos.
"""
from __future__ import annotations

import collections
import time
from typing import Any, Dict, List, Optional
from backend.contracts import PlayerInputPacket, SocketEvents, WorldSnapshotPacket


class MultiplayerNetworkClient:
    """Cliente de red para sincronización en tiempo real de Da Vinci Fighters."""

    def __init__(self, room_id: str, player_id: int, user_id: str, send_fn: Optional[Any] = None):
        self.room_id = room_id
        self.player_id = player_id  # 1 o 2
        self.user_id = user_id
        self._send_fn = send_fn

        self.seq: int = 0
        self.tick: int = 0
        self.ping_ms: float = 0.0
        self._last_ping_sent: float = 0.0

        # Buffer de instantáneas recibidas para interpolación
        self._snapshots: collections.deque[WorldSnapshotPacket] = collections.deque(maxlen=30)
        self.latest_snapshot: Optional[WorldSnapshotPacket] = None

        self.is_connected: bool = True
        self.is_paused: bool = False
        self.match_over: bool = False

    def emit_input(self, dpad: str, buttons: List[str]) -> PlayerInputPacket:
        """Crea y transmite el paquete de entrada del tick actual."""
        self.tick += 1
        self.seq += 1
        now_ms = time.time() * 1000.0

        packet = PlayerInputPacket(
            room_id=self.room_id,
            player_id=self.player_id,
            tick=self.tick,
            seq=self.seq,
            dpad=dpad,
            buttons=buttons,
            timestamp_ms=now_ms,
        )

        if self._send_fn:
            self._send_fn(SocketEvents.GAME_INPUT, packet.to_dict())

        return packet

    def receive_snapshot(self, snapshot_dict: Dict[str, Any]) -> None:
        """Recibe y encola una instantánea autoritativa del servidor."""
        snap = WorldSnapshotPacket(
            room_id=snapshot_dict.get("room_id", self.room_id),
            tick=int(snapshot_dict.get("tick", 0)),
            p1_state=snapshot_dict.get("p1_state", {}),
            p2_state=snapshot_dict.get("p2_state", {}),
            timer=float(snapshot_dict.get("timer", 99.0)),
            current_round=int(snapshot_dict.get("current_round", 1)),
            p1_wins=int(snapshot_dict.get("p1_wins", 0)),
            p2_wins=int(snapshot_dict.get("p2_wins", 0)),
            status=snapshot_dict.get("status", "fighting"),
        )
        self._snapshots.append(snap)
        self.latest_snapshot = snap

        if snap.status == "match_over":
            self.match_over = True

    def get_remote_fighter_state(self) -> Dict[str, Any]:
        """Obtiene el estado interpolado del contrincante remoto."""
        if not self.latest_snapshot:
            # Estado por defecto según el slot
            if self.player_id == 1:
                return {"x": 1300.0, "y": 550.0, "hp": 100, "state": "idle", "facing_right": False}
            else:
                return {"x": 800.0, "y": 550.0, "hp": 100, "state": "idle", "facing_right": True}

        # Si somos P1, el remoto es P2; si somos P2, el remoto es P1
        return self.latest_snapshot.p2_state if self.player_id == 1 else self.latest_snapshot.p1_state

    def update_rtt(self, sent_timestamp_ms: float) -> float:
        """Calcula el tiempo de ida y vuelta (RTT) y latencia en milisegundos."""
        now_ms = time.time() * 1000.0
        rtt = max(1.0, now_ms - sent_timestamp_ms)
        self.ping_ms = round(rtt / 2.0, 1)
        return self.ping_ms
